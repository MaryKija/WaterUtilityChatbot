"""backend/context_engine.py

Autonomous context engine for continuous, context-aware, non-repetitive conversations.

Hard requirements implemented here:
- Persisted session context schema (JSON) compatible with `session_context` DB table.
- Pending-question resolver with never-reprompt behavior + attempts counter.
- Flow expiry (FLOW_TIMEOUT_HOURS, default 24h).
- Regex-first entity extraction with LLM fallback (Groq) when needed.
- Conversation summarization when long.
- Human agent override hook: `clear_workflow_for_ticket(ticket_id)`.

Integration note:
- `backend/main.py` should call `update_context()` on every incoming turn,
  and may short-circuit with an override reply when `action_hint["reply_override"]` is present.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Tuple

import requests

from .config import config
from .logger import logger
from .validators import is_valid_account, is_valid_name, is_valid_phone, normalize_phone


Role = Literal["user", "bot"]


FLOW_TIMEOUT_HOURS = int(os.getenv("FLOW_TIMEOUT_HOURS", "24"))
CONTEXT_HISTORY_HEAD_N = int(os.getenv("CONTEXT_HISTORY_HEAD_N", "12"))
SUMMARY_TRIGGER_TURNS = int(os.getenv("SUMMARY_TRIGGER_TURNS", "24"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # Accept both with/without timezone.
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _safe_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _safe_list(v: Any) -> list:
    return v if isinstance(v, list) else []


def redact_pii(text: str) -> str:
    """Redact PII for storage in analytics/training tables.

    - phones: keep last 3 digits
    - long digit runs: partially mask
    """

    t = text or ""

    def _mask_digits(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) <= 4:
            return "X" * len(digits)
        return ("X" * (len(digits) - 3)) + digits[-3:]

    # Phone-ish patterns.
    t = re.sub(r"(\+?\d[\d\s\-]{7,14}\d)", _mask_digits, t)
    # Account-ish patterns.
    t = re.sub(r"\b\d{6,20}\b", _mask_digits, t)
    return t


def initialize_context(user_id: str) -> dict:
    """Initialize default context for a user."""

    uid = (user_id or "").strip() or "unknown"
    return {
        "user_id": uid,
        "flow": None,
        "step": None,
        "entities": {},
        "pending_question": None,
        "pending_attempts": {},
        "conversation_summary": "",
        "conversation_history_head": [],
        "last_updated": _utc_now_iso(),
        "escalated": False,
        # Optional hint that lets `/chat` skip classification safely.
        "intent_hint": None,
        # When true, caller can optionally notify the user once.
        "flow_expired_notice": None,
    }


def extract_entities(message: str) -> dict:
    """Extract entities from message (regex first, with validation).

    Returns a dict with any of:
    - account_number
    - phone
    - name
    - ticket_id
    - date
    - amount
    """

    msg = (message or "").strip()
    out: dict[str, str] = {}

    # Account number: 6+ digits.
    m_acct = re.search(r"\b(\d{6,20})\b", msg)
    if m_acct and is_valid_account(m_acct.group(1)):
        out["account_number"] = m_acct.group(1)

    # Ticket id: WC-XXXXXX
    m_tid = re.search(r"\b(WC-[A-Z0-9]{6})\b", msg.upper())
    if m_tid:
        out["ticket_id"] = m_tid.group(1)

    # Phone: accept +260..., 260..., 0..., or digit runs.
    m_phone = re.search(r"(\+?\d[\d\s\-]{7,14}\d)", msg)
    if m_phone:
        candidate = m_phone.group(1)
        if is_valid_phone(candidate):
            out["phone"] = normalize_phone(candidate)

    # Amount: local heuristic.
    m_amt = re.search(r"\b(?:k\s*)?(\d+(?:\.\d{1,2})?)\b", msg, flags=re.IGNORECASE)
    if m_amt:
        out["amount"] = m_amt.group(1)

    # Date: common forms.
    m_date = re.search(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|today|yesterday|last\s+week|last\s+month)\b",
        msg,
        flags=re.IGNORECASE,
    )
    if m_date:
        out["date"] = m_date.group(1)

    # Name: best-effort when explicitly stated.
    m_name = re.search(r"\b(?:my\s+name\s+is|i\s+am)\s+([A-Za-z][A-Za-z\s'\-\.]{1,58})\b", msg, flags=re.IGNORECASE)
    if m_name:
        name = m_name.group(1).strip()
        if is_valid_name(name):
            out["name"] = name

    return out


def _groq_extract_entities(message: str, session: dict) -> dict:
    """Groq fallback entity extraction. Returns entities with optional confidences.

    Output shape tolerated:
    {
      "fields": {"name": {"value": "...", "confidence": 0.9}, ...}
    }
    OR direct flat: {"name": "...", ...}
    """

    # Keep prompt tight and auditable.
    system = (
        "Given this user message and session context, extract: "
        "name, account_number, phone, date, amount. "
        "Return JSON only. Include confidence scores if possible."
    )
    user = {
        "message": (message or ""),
        "session_context": {
            "flow": session.get("flow"),
            "step": session.get("step"),
            "pending_question": session.get("pending_question"),
            "entities": session.get("entities", {}),
            "conversation_summary": session.get("conversation_summary", ""),
        },
    }

    payload: Dict[str, Any] = {
        "model": config.groq_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        "temperature": 0,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.groq_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    raw = json.loads(content)

    # Normalize output.
    if isinstance(raw, dict) and "fields" in raw and isinstance(raw.get("fields"), dict):
        fields = raw.get("fields")
        flat: dict[str, str] = {}
        for k, v in fields.items():
            if isinstance(v, dict):
                val = v.get("value")
            else:
                val = v
            if val is None:
                continue
            flat[str(k)] = str(val)
        raw = flat

    if not isinstance(raw, dict):
        return {}

    out: dict[str, str] = {}
    if raw.get("account_number") and is_valid_account(str(raw["account_number"])):
        out["account_number"] = re.sub(r"\D", "", str(raw["account_number"]))
    if raw.get("phone") and is_valid_phone(str(raw["phone"])):
        out["phone"] = normalize_phone(str(raw["phone"]))
    if raw.get("name") and is_valid_name(str(raw["name"])):
        out["name"] = str(raw["name"]).strip()
    if raw.get("date"):
        out["date"] = str(raw["date"]).strip()
    if raw.get("amount"):
        out["amount"] = str(raw["amount"]).strip()
    return out


def resolve_pending_question(session: dict, message: str) -> Tuple[dict, bool]:
    """Resolve `pending_question` (if any) using message.

    Returns (updated_session, resolved_bool).
    """

    sess = _safe_dict(session)
    pending = sess.get("pending_question")
    if not pending:
        return sess, False

    extracted = extract_entities(message)
    # If regex didn't help, try Groq once.
    if pending not in extracted:
        try:
            llm_ex = _groq_extract_entities(message, sess)
            extracted.update(llm_ex)
        except Exception as e:
            logger.warning(f"context_engine.groq_extract_failed err={e}")

    entities = _safe_dict(sess.get("entities"))

    def _set(field: str, value: str) -> bool:
        v = (value or "").strip()
        if not v:
            return False
        entities[field] = v
        # Mirror some fields for backward-compat with agent flows.
        if field == "account_number":
            sess["account_number"] = v
        if field == "phone":
            sess["phone_number"] = v
        if field == "name":
            sess["name"] = v
        return True

    resolved = False
    if pending == "account_number" and extracted.get("account_number"):
        resolved = _set("account_number", extracted["account_number"])
    elif pending == "phone" and extracted.get("phone"):
        resolved = _set("phone", extracted["phone"])
    elif pending == "name" and extracted.get("name"):
        resolved = _set("name", extracted["name"])

    sess["entities"] = entities
    if resolved:
        sess["pending_question"] = None
        attempts = _safe_dict(sess.get("pending_attempts"))
        attempts.pop(str(pending), None)
        sess["pending_attempts"] = attempts
        return sess, True

    # Not resolved -> increment attempts.
    attempts = _safe_dict(sess.get("pending_attempts"))
    attempts[str(pending)] = int(attempts.get(str(pending), 0)) + 1
    sess["pending_attempts"] = attempts
    return sess, False


def summarize_if_needed(user_id: str, session: dict) -> str:
    """Summarize conversation when long.

    Strategy:
    - If head grows beyond SUMMARY_TRIGGER_TURNS, summarize and truncate head.
    - If Groq unavailable, fallback to a deterministic summary.
    """

    sess = _safe_dict(session)
    head = _safe_list(sess.get("conversation_history_head"))
    if len(head) < SUMMARY_TRIGGER_TURNS:
        return str(sess.get("conversation_summary") or "")

    redacted_lines = []
    for m in head[-20:]:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        text = redact_pii(str(m.get("text") or ""))
        redacted_lines.append(f"{role}: {text}")

    system = (
        "You are an assistant that summarizes a support conversation for a water utility. "
        "Return JSON only: {\"summary\": \"...\"}. Keep it under 60 words."
    )
    user = "\n".join(redacted_lines)

    try:
        payload: Dict[str, Any] = {
            "model": config.groq_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": 120,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.groq_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        raw = json.loads(content)
        summary = str(raw.get("summary") or "").strip()
        if not summary:
            raise ValueError("empty summary")
    except Exception as e:
        logger.warning(f"context_engine.summarize_fallback err={e}")
        # Deterministic fallback.
        user_msgs = [m for m in head if isinstance(m, dict) and m.get("role") == "user"]
        tail = [str(m.get("text") or "") for m in user_msgs[-3:]]
        summary = "Recent issues: " + "; ".join(redact_pii(t)[:80] for t in tail if t)

    sess["conversation_summary"] = summary
    # Keep only a small tail after summarization.
    sess["conversation_history_head"] = head[-CONTEXT_HISTORY_HEAD_N:]
    return summary


def expire_flow_if_needed(session: dict) -> dict:
    """Expire active flow if last_updated is beyond timeout."""

    sess = _safe_dict(session)
    active_flow = sess.get("flow")
    last_updated = _parse_ts(str(sess.get("last_updated") or ""))
    if not active_flow or not last_updated:
        return sess

    timeout = timedelta(hours=max(1, FLOW_TIMEOUT_HOURS))
    if datetime.now(timezone.utc) - last_updated <= timeout:
        return sess

    # Expire.
    prev_flow = sess.get("flow")
    sess["flow"] = None
    sess["step"] = None
    sess["pending_question"] = None
    sess["pending_attempts"] = {}
    sess["intent_hint"] = None
    sess["flow_expired_notice"] = (
        f"Your previous session about '{prev_flow}' expired after inactivity."
    )
    logger.info(
        "context_engine.flow_expired",
        extra={
            "extra_data": {
                "user_id": sess.get("user_id"),
                "flow": prev_flow,
                "timeout_hours": FLOW_TIMEOUT_HOURS,
            }
        },
    )
    return sess


def update_context(user_id: str, role: Role, message: str, session: dict) -> dict:
    """Update context with a new message.

    Returns updated session. May include an `action_hint` dict:
    - reply_override: str (if the context engine should respond directly)
    - needs_clarification: bool
    - escalated: bool
    """

    sess = _safe_dict(session)
    if not sess:
        sess = initialize_context(user_id)

    sess["user_id"] = (user_id or sess.get("user_id") or "unknown")

    # Expire flow if needed (before processing the new message).
    sess = expire_flow_if_needed(sess)

    # Append to in-session history head.
    head = _safe_list(sess.get("conversation_history_head"))
    head.append({"role": role, "text": message, "ts": _utc_now_iso()})
    sess["conversation_history_head"] = head[-CONTEXT_HISTORY_HEAD_N:]
    sess["last_updated"] = _utc_now_iso()

    # Summarize if needed (only on user turns).
    if role == "user":
        try:
            summarize_if_needed(user_id, sess)
        except Exception:
            pass

    action_hint: dict[str, Any] = {}

    # Resolve pending question on user turn.
    if role == "user" and sess.get("pending_question"):
        sess, resolved = resolve_pending_question(sess, message)
        if resolved:
            action_hint["pending_resolved"] = True
        else:
            pending = str(sess.get("pending_question"))
            attempts = _safe_dict(sess.get("pending_attempts")).get(pending, 0)
            # Single clarifying question, specific to the missing field.
            if attempts <= 3:
                prompts = {
                    "account_number": "Please reply with your account number (6+ digits).",
                    "phone": "Please reply with your phone number (e.g., +26097XXXXXXX).",
                    "name": "Please reply with your full name.",
                }
                action_hint["reply_override"] = prompts.get(pending, "Please provide the requested detail.")
                action_hint["needs_clarification"] = True
            else:
                # After 3 failed attempts, suggest escalation.
                action_hint["reply_override"] = (
                    "I'm having trouble capturing that detail. "
                    "I can connect you to a customer service agent to help."
                )
                action_hint["escalate_suggested"] = True

    # Merge entities (best-effort) on user turn.
    if role == "user":
        entities = _safe_dict(sess.get("entities"))
        extracted = extract_entities(message)
        # If a pending field exists and regex didn't fill it, try Groq once.
        pending = sess.get("pending_question")
        if pending and pending not in extracted:
            try:
                extracted.update(_groq_extract_entities(message, sess))
            except Exception as e:
                logger.warning(f"context_engine.groq_extract_failed err={e}")

        entities.update({k: v for k, v in extracted.items() if v})
        sess["entities"] = entities

        # Back-compat mirroring.
        if entities.get("account_number"):
            sess.setdefault("account_number", entities["account_number"])
        if entities.get("phone"):
            sess.setdefault("phone_number", entities["phone"])
        if entities.get("name"):
            sess.setdefault("name", entities["name"])

    # Provide an intent hint derived from flow (so `/chat` can skip reclassification).
    flow = sess.get("flow")
    if flow and not sess.get("intent_hint"):
        if flow in {"complaint"}:
            sess["intent_hint"] = "report_fault"
        elif flow in {"billing", "payment_reflection"}:
            sess["intent_hint"] = "billing_inquiry"
        elif flow in {"escalation_form"}:
            sess["intent_hint"] = "escalation"
        elif flow in {"followup"}:
            sess["intent_hint"] = "complaint_followup"

    sess["action_hint"] = action_hint
    return sess


def clear_workflow_for_ticket(ticket_id: str) -> int:
    """Clear or mark flow completed for any sessions referencing this ticket.

    This is called when a ticket is RESOLVED/CLOSED by a human agent.

    Returns the number of affected sessions.
    """

    tid = (ticket_id or "").upper().strip()
    if not tid:
        return 0

    # Import here to avoid circular imports.
    from .storage import DB_PATH

    affected = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT user_id, context_json FROM session_context").fetchall()
        for user_id, ctx_json in rows:
            try:
                ctx = json.loads(ctx_json or "{}")
            except Exception:
                continue

            if not isinstance(ctx, dict):
                continue

            # Look for references.
            referenced = False
            for key in [
                "ticket_id",
                "payment_ticket",
                "escalation_ticket_id",
            ]:
                if str(ctx.get(key) or "").upper().strip() == tid:
                    referenced = True
                    break

            if not referenced:
                # Also scan nested entities.
                ents = ctx.get("entities")
                if isinstance(ents, dict) and str(ents.get("ticket_id") or "").upper().strip() == tid:
                    referenced = True

            if not referenced:
                continue

            # Clear workflow fields.
            ctx["flow"] = None
            ctx["step"] = None
            ctx["pending_question"] = None
            ctx["pending_attempts"] = {}
            ctx["intent_hint"] = None
            ctx["escalated"] = False
            ctx["last_updated"] = _utc_now_iso()

            conn.execute(
                "UPDATE session_context SET context_json = ?, updated_at = ? WHERE user_id = ?",
                (json.dumps(ctx), _utc_now_iso(), user_id),
            )
            affected += 1

        conn.commit()
    except Exception as e:
        logger.error(f"context_engine.clear_workflow_for_ticket_failed ticket_id={tid} err={e}")
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass

    logger.info(
        "context_engine.clear_workflow_for_ticket",
        extra={"extra_data": {"ticket_id": tid, "affected": affected}},
    )
    return affected

