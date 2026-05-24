"""backend/intent_discovery.py

Self-learning intent discovery pipeline (human-in-the-loop).

Hard requirements:
- Reads conversation logs from SQLite (redacted view only).
- Generates *suggestions* only; never auto-deploys into production.
- Groq is the primary reasoning/summarization engine, with local-first embeddings.
- Fallback behavior when embeddings/LLM unavailable (TF-IDF + clustering + deterministic summary).
- Clear, auditable structured logging for: detection, clustering, suggestion, label, deploy/rollback.

CLI:
  python -m backend.intent_discovery --run-once
  python -m backend.intent_discovery --run-once --since "2026-02-01T00:00:00Z"
  python -m backend.intent_discovery --daemon --interval-minutes 60
  python -m backend.intent_discovery --purge-old --retention-days 90

Note: Admin API endpoints that label/deploy suggestions live in `backend/main.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import string
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import sqlite3

import requests

from .config import config
from .logger import logger
from .storage import (
    DB_PATH,
    init_db,
    CONVERSATION_HISTORY_TABLE,
    INTENT_SUGGESTIONS_TABLE,
    INTENT_LABELS_TABLE,
    INTENT_CANDIDATES_TABLE,
    INTENT_METRICS_TABLE,
)


MAX_UTTERANCES_PER_RUN = int(os.getenv("INTENT_DISCOVERY_MAX_UTTERANCES", "10000"))
MIN_CLUSTER_SIZE = int(os.getenv("INTENT_DISCOVERY_MIN_CLUSTER_SIZE", "6"))
DISCOVERY_SAMPLE_SEED = int(os.getenv("INTENT_DISCOVERY_SEED", "42"))

RETENTION_DAYS_DEFAULT = int(os.getenv("CONVERSATION_RETENTION_DAYS", "90"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_suggestion_id() -> str:
    chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SUG-{chars}"


def _safe_json_loads(s: str, default: Any) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return default


def extract_unlabeled_utterances(since_timestamp: str | None = None) -> List[str]:
    """Extract user utterances from redacted conversation history.

    "Unlabeled" here means "not already an intent suggestion". We do not store per-message
    intent labels in the DB yet, so we instead:
    - pull recent user turns
    - filter out very short / greeting-like turns
    - sample up to a configured limit
    """

    init_db()
    where = "WHERE role = 'user'"
    params: list[Any] = []
    if since_timestamp:
        where += " AND ts >= ?"
        params.append(since_timestamp)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT text_redacted
            FROM {CONVERSATION_HISTORY_TABLE}
            {where}
            ORDER BY ts DESC
            LIMIT ?
            """,
            (*params, MAX_UTTERANCES_PER_RUN),
        ).fetchall()

    texts = [str(r[0] or "").strip() for r in rows]
    # Basic filters.
    cleaned: list[str] = []
    for t in texts:
        if len(t) < 4:
            continue
        low = t.lower().strip()
        if low in {"hi", "hello", "hey", "thanks", "thank you"}:
            continue
        cleaned.append(t)

    # Stable shuffle to avoid always clustering the same tail.
    rnd = random.Random(DISCOVERY_SAMPLE_SEED)
    rnd.shuffle(cleaned)
    return cleaned[:MAX_UTTERANCES_PER_RUN]


def embed_texts(texts: List[str]):
    """Embed texts.

    Preferred: sentence-transformers (offline embeddings).
    Fallback: TF-IDF + TruncatedSVD dense vectors.
    """

    if not texts:
        return []

    # Try sentence-transformers.
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model_name = os.getenv("INTENT_DISCOVERY_EMBED_MODEL", "all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)
        emb = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return emb
    except Exception as e:
        logger.warning(
            "intent_discovery.embed_fallback",
            extra={"extra_data": {"reason": str(e)[:200]}},
        )

    # TF-IDF fallback.
    from sklearn.decomposition import TruncatedSVD  # type: ignore
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.preprocessing import Normalizer  # type: ignore

    vectorizer = TfidfVectorizer(
        max_features=int(os.getenv("INTENT_DISCOVERY_TFIDF_MAX_FEATURES", "5000")),
        ngram_range=(1, 2),
        min_df=2,
    )
    X = vectorizer.fit_transform(texts)
    n_components = min(128, max(2, X.shape[1] - 1))
    svd = TruncatedSVD(n_components=n_components, random_state=DISCOVERY_SAMPLE_SEED)
    dense = svd.fit_transform(X)
    dense = Normalizer(copy=False).fit_transform(dense)
    return dense


def cluster_embeddings(embeddings) -> List[int]:
    """Cluster embeddings.

    Preferred: HDBSCAN (variable cluster count).
    Fallback: DBSCAN.
    Fallback2: KMeans (fixed-ish cluster count based on sqrt(n)).
    """

    if embeddings is None or len(embeddings) == 0:
        return []

    # Try HDBSCAN.
    try:
        import hdbscan  # type: ignore

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=MIN_CLUSTER_SIZE,
            metric="euclidean",
        )
        labels = clusterer.fit_predict(embeddings)
        return [int(x) for x in labels]
    except Exception as e:
        logger.warning(
            "intent_discovery.cluster_fallback",
            extra={"extra_data": {"reason": str(e)[:200], "algo": "hdbscan"}},
        )

    # DBSCAN fallback.
    try:
        from sklearn.cluster import DBSCAN  # type: ignore

        labels = DBSCAN(eps=0.6, min_samples=MIN_CLUSTER_SIZE, metric="euclidean").fit_predict(
            embeddings
        )
        return [int(x) for x in labels]
    except Exception as e:
        logger.warning(
            "intent_discovery.cluster_fallback",
            extra={"extra_data": {"reason": str(e)[:200], "algo": "dbscan"}},
        )

    # KMeans fallback.
    from sklearn.cluster import KMeans  # type: ignore

    k = int(max(2, min(20, (len(embeddings) ** 0.5))))
    labels = KMeans(n_clusters=k, random_state=DISCOVERY_SAMPLE_SEED, n_init="auto").fit_predict(
        embeddings
    )
    return [int(x) for x in labels]


@dataclass(frozen=True)
class ClusterSuggestion:
    suggestion_id: str
    label_suggestion: str
    confidence_score: float
    sample_utts: list[str]
    summary: str
    example_action: str
    created_at: str


def _cosine_sim_matrix(vectors):
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

    return cosine_similarity(vectors)


def _existing_candidate_labels() -> list[str]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"SELECT label FROM {INTENT_CANDIDATES_TABLE} WHERE active = 1"
        ).fetchall()
    return [str(r[0]) for r in rows if r and r[0]]


def score_and_prune_clusters(clusters, texts) -> List[ClusterSuggestion]:
    """Create cluster suggestions with confidence scoring.

    Score uses:
    - cluster size
    - intra-cluster similarity (avg cosine)
    - novelty factor (penalize if label overlaps an active candidate label)
    """

    if not clusters or not texts or len(clusters) != len(texts):
        return []

    # Group by cluster id; -1 is noise.
    buckets: dict[int, list[int]] = {}
    for i, c in enumerate(clusters):
        if int(c) < 0:
            continue
        buckets.setdefault(int(c), []).append(i)

    if not buckets:
        return []

    # Lightweight embeddings for scoring similarity (TF-IDF always available through sklearn dependency).
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.preprocessing import Normalizer  # type: ignore

    vec = TfidfVectorizer(max_features=4000, ngram_range=(1, 2), min_df=2)
    X = vec.fit_transform(texts)
    X = Normalizer(copy=False).fit_transform(X)

    sim = _cosine_sim_matrix(X)
    active_labels = set(_existing_candidate_labels())

    suggestions: list[ClusterSuggestion] = []
    now = _utc_now_iso()
    for cluster_id, idxs in buckets.items():
        if len(idxs) < MIN_CLUSTER_SIZE:
            continue

        # Intra-cluster similarity.
        intra_vals = []
        for a in idxs:
            for b in idxs:
                if a >= b:
                    continue
                intra_vals.append(float(sim[a, b]))
        intra = sum(intra_vals) / max(1, len(intra_vals))

        # Size factor with saturation.
        size_factor = min(1.0, len(idxs) / 30.0)
        cohesion_factor = max(0.0, min(1.0, intra))

        # Provisional label via heuristic keywords (will be overridden by Groq if available).
        cluster_texts = [texts[i] for i in idxs]
        joined = " ".join(cluster_texts).lower()
        if "pay" in joined or "payment" in joined:
            label_guess = "payment_issue_candidate"
        elif "connect" in joined or "new connection" in joined:
            label_guess = "new_connection_candidate"
        elif "meter" in joined:
            label_guess = "meter_issue_candidate"
        else:
            label_guess = "new_intent_candidate"

        novelty_penalty = 0.15 if label_guess in active_labels else 0.0
        confidence = max(0.0, min(1.0, 0.2 + 0.5 * cohesion_factor + 0.3 * size_factor - novelty_penalty))

        # Sample utterances.
        sample = cluster_texts[:]
        random.Random(DISCOVERY_SAMPLE_SEED + cluster_id).shuffle(sample)
        sample = sample[: min(10, len(sample))]

        suggestions.append(
            ClusterSuggestion(
                suggestion_id=_new_suggestion_id(),
                label_suggestion=label_guess,
                confidence_score=confidence,
                sample_utts=sample[:3],
                summary="",
                example_action="",
                created_at=now,
            )
        )

    # Highest confidence first; keep top N.
    suggestions.sort(key=lambda s: s.confidence_score, reverse=True)
    max_out = int(os.getenv("INTENT_DISCOVERY_MAX_SUGGESTIONS", "25"))
    return suggestions[:max_out]


def _groq_cluster_summary(cluster_texts: list[str]) -> dict:
    """Use Groq once to summarize a cluster into a candidate intent JSON."""

    system = (
        "You are an assistant that summarizes a set of customer support utterances from a water utility into: "
        "label, 3 example phrases, short summary (1–2 sentences) and suggested handler (tool or escalation). "
        "Output JSON only."
    )
    # Provide up to 10 sample utterances.
    payload_user = {"utterances": cluster_texts[:10]}
    payload: Dict[str, Any] = {
        "model": config.groq_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload_user)},
        ],
        "temperature": 0,
        "max_tokens": 280,
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.groq_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    return json.loads(content)


def generate_candidate_intent_description(cluster_texts) -> str:
    """Return Groq JSON string (or deterministic fallback JSON string)."""

    # Must use redacted text only.
    cluster_texts = [str(x) for x in (cluster_texts or []) if str(x).strip()]
    if not cluster_texts:
        return json.dumps({"label": "", "examples": [], "summary": "", "suggested_action": ""})

    try:
        raw = _groq_cluster_summary(cluster_texts)
        # Normalize keys.
        out = {
            "label": str(raw.get("label") or "").strip(),
            "examples": raw.get("examples") if isinstance(raw.get("examples"), list) else [],
            "summary": str(raw.get("summary") or "").strip(),
            "suggested_action": str(raw.get("suggested_action") or raw.get("suggested_handler") or "").strip(),
        }
        return json.dumps(out)
    except Exception as e:
        logger.warning(
            "intent_discovery.groq_unavailable",
            extra={"extra_data": {"reason": str(e)[:200]}},
        )
        # Deterministic fallback.
        joined = " ".join(cluster_texts[:10]).lower()
        if "pay" in joined or "payment" in joined:
            label = "payment_issue_candidate"
            action = "escalate_to_billing_team"
        elif "connect" in joined:
            label = "new_connection_candidate"
            action = "provide_connection_guidance"
        else:
            label = "new_intent_candidate"
            action = "review_and_route"
        examples = cluster_texts[:3]
        summary = "Recurring scenario discovered from recent conversations."
        return json.dumps({"label": label, "examples": examples, "summary": summary, "suggested_action": action})


def create_suggestions_db(entries: List[ClusterSuggestion]) -> None:
    init_db()
    now = _utc_now_iso()

    with sqlite3.connect(DB_PATH) as conn:
        for e in entries:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {INTENT_SUGGESTIONS_TABLE}(
                    suggestion_id, label_suggestion, confidence_score, sample_utts_json,
                    summary, example_action, status, groq_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    e.suggestion_id,
                    e.label_suggestion,
                    float(e.confidence_score),
                    json.dumps(e.sample_utts),
                    e.summary,
                    e.example_action,
                    "PENDING",
                    None,
                    e.created_at or now,
                    now,
                ),
            )
        conn.commit()


def _enrich_suggestions_with_groq(suggestions: list[ClusterSuggestion], cluster_map: dict[str, list[str]]) -> None:
    """Update suggestion rows with Groq-derived JSON summary."""

    if not suggestions:
        return
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        for s in suggestions:
            cluster_texts = cluster_map.get(s.suggestion_id, [])
            groq_json = generate_candidate_intent_description(cluster_texts)
            parsed = _safe_json_loads(groq_json, {})
            summary = str(parsed.get("summary") or "").strip()
            label = str(parsed.get("label") or s.label_suggestion).strip() or s.label_suggestion
            action = str(parsed.get("suggested_action") or "").strip()
            examples = parsed.get("examples") if isinstance(parsed.get("examples"), list) else []
            sample_utts_json = json.dumps((examples[:3] if examples else s.sample_utts))

            conn.execute(
                f"""
                UPDATE {INTENT_SUGGESTIONS_TABLE}
                SET label_suggestion = ?, summary = ?, example_action = ?, sample_utts_json = ?, groq_json = ?, updated_at = ?
                WHERE suggestion_id = ?
                """,
                (label, summary, action, sample_utts_json, groq_json, _utc_now_iso(), s.suggestion_id),
            )
        conn.commit()


def run_discovery_once(since: str | None = None) -> dict:
    """Run one discovery pass and write suggestions to DB."""

    start = time.time()
    logger.info(
        "intent_discovery.start",
        extra={"extra_data": {"since": since, "max_utterances": MAX_UTTERANCES_PER_RUN}},
    )

    texts = extract_unlabeled_utterances(since)
    logger.info(
        "intent_discovery.detect",
        extra={"extra_data": {"utterances": len(texts)}},
    )

    embeddings = embed_texts(texts)
    labels = cluster_embeddings(embeddings)

    logger.info(
        "intent_discovery.cluster",
        extra={"extra_data": {"utterances": len(texts), "labels": len(labels)}},
    )

    suggestions = score_and_prune_clusters(labels, texts)
    logger.info(
        "intent_discovery.score",
        extra={"extra_data": {"suggestions": len(suggestions)}},
    )

    # Map suggestion -> full cluster sample (for Groq summary).
    cluster_map: dict[str, list[str]] = {}
    if suggestions:
        # Build buckets again.
        buckets: dict[int, list[int]] = {}
        for i, c in enumerate(labels):
            if int(c) < 0:
                continue
            buckets.setdefault(int(c), []).append(i)
        # Assign in score order.
        for s in suggestions:
            # Best-effort: match cluster by scanning for sample utterances.
            sid_texts = []
            for idxs in buckets.values():
                cluster_texts = [texts[i] for i in idxs]
                if any(u in cluster_texts for u in s.sample_utts):
                    sid_texts = cluster_texts
                    break
            cluster_map[s.suggestion_id] = sid_texts[:10]

    create_suggestions_db(suggestions)
    _enrich_suggestions_with_groq(suggestions, cluster_map)

    dur_ms = int((time.time() - start) * 1000)
    logger.info(
        "intent_discovery.done",
        extra={"extra_data": {"duration_ms": dur_ms, "suggestions": len(suggestions)}},
    )

    return {
        "status": "ok",
        "duration_ms": dur_ms,
        "utterances": len(texts),
        "suggestions_created": len(suggestions),
        "first_suggestion_id": suggestions[0].suggestion_id if suggestions else None,
    }


def run_discovery_daemon(interval_minutes: int = 60) -> None:
    """Run discovery periodically (dev convenience)."""

    interval = max(5, int(interval_minutes))
    logger.info(
        "intent_discovery.daemon_start",
        extra={"extra_data": {"interval_minutes": interval}},
    )
    while True:
        try:
            run_discovery_once()
        except Exception as e:
            logger.error(
                "intent_discovery.daemon_error",
                extra={"extra_data": {"error": str(e)[:300]}},
            )
        time.sleep(interval * 60)


def purge_old_conversation_logs(retention_days: int | None = None) -> dict:
    """Purge conversation logs older than `retention_days`.

    Hard requirement: provide retention/consent control. This is a local utility
    (no API endpoint is exposed by default).
    """

    init_db()
    days = int(retention_days or RETENTION_DAYS_DEFAULT)
    days = max(1, days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        # Keep PII table aligned by timestamp.
        cur1 = conn.execute(
            f"DELETE FROM conversation_history WHERE ts < ?",
            (cutoff_iso,),
        )
        cur2 = conn.execute(
            f"DELETE FROM conversation_history_pii WHERE ts < ?",
            (cutoff_iso,),
        )
        conn.commit()

    logger.info(
        "intent_discovery.purge",
        extra={
            "extra_data": {
                "retention_days": days,
                "cutoff": cutoff_iso,
                "deleted_redacted": cur1.rowcount,
                "deleted_pii": cur2.rowcount,
            }
        },
    )
    return {
        "status": "ok",
        "retention_days": days,
        "cutoff": cutoff_iso,
        "deleted_redacted": cur1.rowcount,
        "deleted_pii": cur2.rowcount,
    }


def _get_suggestion(suggestion_id: str) -> dict | None:
    init_db()
    sid = (suggestion_id or "").strip().upper()
    if not sid:
        return None
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"""SELECT suggestion_id, label_suggestion, confidence_score, sample_utts_json, summary, status, created_at, updated_at
            FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?""",
            (sid,),
        ).fetchone()
    if not row:
        return None
    return {
        "suggestion_id": row[0],
        "label_suggestion": row[1],
        "confidence_score": row[2],
        "sample_utts": _safe_json_loads(row[3] or "[]", []),
        "summary": row[4],
        "status": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def test_candidate_intent(suggestion_id: str) -> dict:
    """Lightweight staging test harness.

    This does NOT activate an intent. It records metrics for admin review.

    Current heuristic evaluation (since we do not have gold labels in DB):
    - Measures how well the candidate label matches a set of historical utterances using TF-IDF similarity.
    - Reports proxy precision/recall based on a similarity threshold.
    """

    sug = _get_suggestion(suggestion_id)
    if not sug:
        return {"status": "error", "detail": "suggestion not found"}

    texts = extract_unlabeled_utterances()
    if not texts:
        return {"status": "ok", "detail": "no data", "precision": 0.0, "recall": 0.0, "f1": 0.0}

    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

    vec = TfidfVectorizer(max_features=6000, ngram_range=(1, 2), min_df=2)
    X = vec.fit_transform(texts)

    # Represent candidate by its label + summary + examples.
    rep = " ".join(
        [
            str(sug.get("label_suggestion") or ""),
            str(sug.get("summary") or ""),
            " ".join([str(x) for x in (sug.get("sample_utts") or [])]),
        ]
    ).strip()
    q = vec.transform([rep])
    sims = cosine_similarity(X, q).reshape(-1)

    thresh = float(os.getenv("INTENT_DISCOVERY_TEST_SIM_THRESHOLD", "0.28"))
    pred_pos = [i for i, s in enumerate(sims) if float(s) >= thresh]

    # Proxy ground-truth: nearest neighbors to the candidate representation.
    # Take top M as "true positives" to estimate recall.
    M = max(20, min(200, int(len(texts) * 0.05)))
    top = sorted(range(len(texts)), key=lambda i: float(sims[i]), reverse=True)[:M]
    true_pos = set(top)
    pred_pos_set = set(pred_pos)

    tp = len(true_pos & pred_pos_set)
    fp = len(pred_pos_set - true_pos)
    fn = len(true_pos - pred_pos_set)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = (2 * precision * recall) / max(1e-9, (precision + recall))

    details = {
        "threshold": thresh,
        "evaluated": len(texts),
        "proxy_true_set": len(true_pos),
        "predicted_positive": len(pred_pos_set),
        "examples_predicted": [texts[i] for i in pred_pos[:5]],
    }

    # Store metric snapshot for audit.
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT INTO {INTENT_METRICS_TABLE}(candidate_id, precision, recall, f1, evaluated_at, details_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(sug["suggestion_id"]),
                float(precision),
                float(recall),
                float(f1),
                _utc_now_iso(),
                json.dumps(details),
            ),
        )
        conn.commit()

    logger.info(
        "intent_discovery.test_candidate",
        extra={
            "extra_data": {
                "suggestion_id": sug["suggestion_id"],
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        },
    )

    return {
        "status": "ok",
        "suggestion_id": sug["suggestion_id"],
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "details": details,
    }


def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Intent discovery pipeline")
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--since", type=str, default=None)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval-minutes", type=int, default=60)
    parser.add_argument("--test-candidate", type=str, default=None)
    parser.add_argument("--purge-old", action="store_true")
    parser.add_argument("--retention-days", type=int, default=None)
    args = parser.parse_args(argv)

    if args.purge_old:
        res = purge_old_conversation_logs(args.retention_days)
        print(json.dumps(res, indent=2))
        return 0

    if args.test_candidate:
        res = test_candidate_intent(args.test_candidate)
        print(json.dumps(res, indent=2))
        return 0

    if args.run_once:
        res = run_discovery_once(args.since)
        print(json.dumps(res, indent=2))
        return 0

    if args.daemon:
        run_discovery_daemon(args.interval_minutes)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
