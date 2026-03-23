from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, Optional


# HARD REQUIREMENT: Persist in SQLite `water_utility.db`.
# Back-compat: if an older `database.db` exists and the new DB doesn't,
# copy it over on first run so existing local data isn't lost.
DB_PATH = Path(__file__).resolve().parents[1] / "water_utility.db"
_LEGACY_DB_PATH = Path(__file__).resolve().parents[1] / "database.db"

COMPLAINTS_TABLE = "water_complaints"
ESCALATIONS_TABLE = "escalations"
SESSION_CONTEXT_TABLE = "session_context"

# New tables for context + self-learning intent discovery
CONVERSATION_HISTORY_TABLE = "conversation_history"
CONVERSATION_HISTORY_PII_TABLE = "conversation_history_pii"
INTENT_SUGGESTIONS_TABLE = "intent_suggestions"
INTENT_LABELS_TABLE = "intent_labels"
INTENT_CANDIDATES_TABLE = "intent_candidates"
INTENT_METRICS_TABLE = "intent_metrics"
NEW_CONNECTIONS_TABLE = "new_connections"


ALLOWED_COMPLAINT_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "ESCALATED"}
ALLOWED_ESCALATION_STATUSES = {"WAITING", "ACTIVE", "CLOSED"}


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Legacy DB migration (best-effort copy). SQLite doesn't support cross-file migration
    # without attach; for local dev we do a simple copy when safe.
    if (not DB_PATH.exists()) and _LEGACY_DB_PATH.exists():
        try:
            shutil.copy2(_LEGACY_DB_PATH, DB_PATH)
        except Exception:
            # If copy fails, proceed to create a new DB.
            pass
    return sqlite3.connect(DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(value: Any, *, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


@dataclass(frozen=True)
class Complaint:
    ticket_id: str
    name: str
    area: str
    issue: str
    status: str
    created_at: str
    updated_at: str
    assigned_to: Optional[str]
    notes: list[dict[str, Any]]


@dataclass(frozen=True)
class Escalation:
    escalation_id: str
    ticket_id: str
    user_id: str
    reason: str
    status: str
    messages: list[dict[str, Any]]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Connection:
    id: int
    ticket_id: str
    name: str
    address: str
    phone: str
    email: str
    status: str
    created_at: str


def init_db() -> None:
    """Initialize / upgrade local SQLite schema."""

    with _connect() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {COMPLAINTS_TABLE} (
                ticket_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                area TEXT NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                assigned_to TEXT,
                notes_json TEXT
            )
            """
        )

        # Schema upgrade (for existing DBs).
        for ddl in [
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN updated_at TEXT",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN assigned_to TEXT",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN notes_json TEXT",
        ]:
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                # Duplicate column, etc.
                pass

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ESCALATIONS_TABLE} (
                escalation_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Persistent per-user session context ("progress")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SESSION_CONTEXT_TABLE} (
                user_id TEXT PRIMARY KEY,
                context_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Backward-compatible schema upgrade: add last_updated if missing.
        # (Hard requirement mentions `last_updated`; we keep `updated_at` for existing code.)
        try:
            conn.execute(f"ALTER TABLE {SESSION_CONTEXT_TABLE} ADD COLUMN last_updated TEXT")
        except sqlite3.OperationalError:
            pass

        # ------------------------------
        # Conversation logs (privacy-aware)
        # ------------------------------
        # `conversation_history` stores *redacted* text used for discovery/analytics.
        # `conversation_history_pii` stores the original text for restricted/admin-only access.
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CONVERSATION_HISTORY_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                text_redacted TEXT NOT NULL,
                flow TEXT,
                intent TEXT,
                confidence REAL,
                ts TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CONVERSATION_HISTORY_PII_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                text_original TEXT NOT NULL,
                ts TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_conv_hist_ts ON {CONVERSATION_HISTORY_TABLE}(ts)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_conv_hist_user_ts ON {CONVERSATION_HISTORY_TABLE}(user_id, ts)"
        )

        # ------------------------------
        # Self-learning intent discovery tables
        # ------------------------------
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_SUGGESTIONS_TABLE} (
                suggestion_id TEXT PRIMARY KEY,
                label_suggestion TEXT,
                confidence_score REAL,
                sample_utts_json TEXT NOT NULL,
                summary TEXT,
                example_action TEXT,
                status TEXT NOT NULL,
                groq_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_LABELS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id TEXT NOT NULL,
                label TEXT NOT NULL,
                approved_by TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_CANDIDATES_TABLE} (
                candidate_id TEXT PRIMARY KEY,
                source_suggestion_id TEXT,
                label TEXT NOT NULL,
                handler TEXT,
                active INTEGER NOT NULL DEFAULT 0,
                approvals_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_intent_candidates_active ON {INTENT_CANDIDATES_TABLE}(active)"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_METRICS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                precision REAL,
                recall REAL,
                f1 REAL,
                evaluated_at TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
            """
        )

        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_escalations_status ON {ESCALATIONS_TABLE}(status)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_escalations_user ON {ESCALATIONS_TABLE}(user_id)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_session_context_updated ON {SESSION_CONTEXT_TABLE}(updated_at)"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {NEW_CONNECTIONS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_new_connections_status ON {NEW_CONNECTIONS_TABLE}(status)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_new_connections_ticket ON {NEW_CONNECTIONS_TABLE}(ticket_id)")


def log_conversation_turn(
    *,
    user_id: str,
    role: str,
    text_redacted: str,
    text_original: str,
    ts: str | None = None,
    session_id: str | None = None,
    flow: str | None = None,
    intent: str | None = None,
    confidence: float | None = None,
) -> None:
    """Persist a single conversation turn.

    Privacy:
    - `conversation_history` receives redacted text only (safe for discovery/analytics).
    - `conversation_history_pii` receives the original text (restricted use only; no API endpoints expose it).
    """

    init_db()
    uid = (user_id or "").strip() or "unknown"
    role = (role or "").strip().lower() or "user"
    when = ts or _now()
    sid = (session_id or "").strip() or None
    tr = (text_redacted or "").strip()
    to = (text_original or "").strip()
    fl = (flow or "").strip() or None
    it = (intent or "").strip() or None
    conf = float(confidence) if confidence is not None else None

    if not tr:
        tr = "[EMPTY]"
    if not to:
        to = "[EMPTY]"

    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {CONVERSATION_HISTORY_TABLE}(
                user_id, session_id, role, text_redacted, flow, intent, confidence, ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, sid, role, tr, fl, it, conf, when),
        )
        conn.execute(
            f"""
            INSERT INTO {CONVERSATION_HISTORY_PII_TABLE}(
                user_id, session_id, role, text_original, ts
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (uid, sid, role, to, when),
        )


def get_session_context(user_id: str) -> dict[str, Any]:
    """Load persisted session context for a user_id (or {} if none)."""

    init_db()
    uid = (user_id or "").strip() or "unknown"
    with _connect() as conn:
        row = conn.execute(
            f"SELECT context_json FROM {SESSION_CONTEXT_TABLE} WHERE user_id = ?",
            (uid,),
        ).fetchone()

    if not row:
        return {}

    ctx = _safe_json_loads(row[0], default={})
    return ctx if isinstance(ctx, dict) else {}


def upsert_session_context(user_id: str, context: dict[str, Any]) -> None:
    """Persist (insert/update) the session context for a user_id."""

    init_db()
    uid = (user_id or "").strip() or "unknown"
    payload = context if isinstance(context, dict) else {}
    now = _now()

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {SESSION_CONTEXT_TABLE} SET context_json = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(payload), now, uid),
        )
        if cur.rowcount <= 0:
            conn.execute(
                f"""
                INSERT INTO {SESSION_CONTEXT_TABLE}(user_id, context_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (uid, json.dumps(payload), now, now),
            )


def create_complaint(*, name: str, area: str, issue: str, ticket_id: str | None = None) -> str:
    """Create a complaint ticket and return ticket_id."""

    init_db()
    created_at = _now()

    def _generate_ticket_id() -> str:
        import random
        import string

        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"WC-{chars}"

    for _ in range(3):
        tid = (ticket_id or _generate_ticket_id()).upper().strip()
        try:
            with _connect() as conn:
                conn.execute(
                    f"""
                    INSERT INTO {COMPLAINTS_TABLE}(
                        ticket_id, name, area, issue, status, created_at, updated_at, assigned_to, notes_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tid, name, area, issue, "OPEN", created_at, created_at, None, "[]"),
                )
            return tid
        except sqlite3.IntegrityError:
            ticket_id = None

    raise RuntimeError("Failed to allocate a unique ticket_id")


def list_complaints() -> list[Complaint]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                ticket_id,
                name,
                area,
                issue,
                status,
                created_at,
                COALESCE(updated_at, created_at) as updated_at,
                assigned_to,
                COALESCE(notes_json, '[]') as notes_json
            FROM {COMPLAINTS_TABLE}
            ORDER BY created_at DESC
            """
        ).fetchall()

    items: list[Complaint] = []
    for row in rows:
        notes = _safe_json_loads(row[8], default=[])
        if not isinstance(notes, list):
            notes = []
        items.append(
            Complaint(
                ticket_id=row[0],
                name=row[1],
                area=row[2],
                issue=row[3],
                status=row[4],
                created_at=row[5],
                updated_at=row[6],
                assigned_to=row[7],
                notes=notes,
            )
        )
    return items


def get_complaint(ticket_id: str) -> Complaint | None:
    init_db()
    tid = (ticket_id or "").upper().strip()
    if not tid:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                ticket_id,
                name,
                area,
                issue,
                status,
                created_at,
                COALESCE(updated_at, created_at) as updated_at,
                assigned_to,
                COALESCE(notes_json, '[]') as notes_json
            FROM {COMPLAINTS_TABLE}
            WHERE ticket_id = ?
            """,
            (tid,),
        ).fetchone()

    if not row:
        return None

    notes = _safe_json_loads(row[8], default=[])
    if not isinstance(notes, list):
        notes = []

    return Complaint(
        ticket_id=row[0],
        name=row[1],
        area=row[2],
        issue=row[3],
        status=row[4],
        created_at=row[5],
        updated_at=row[6],
        assigned_to=row[7],
        notes=notes,
    )


def set_complaint_status(ticket_id: str, status: str) -> bool:
    init_db()

    tid = (ticket_id or "").upper().strip()
    st = (status or "").upper().strip()
    if not tid:
        return False
    if st not in ALLOWED_COMPLAINT_STATUSES:
        raise ValueError(f"Invalid complaint status: {st!r}")

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET status = ?, updated_at = ? WHERE ticket_id = ?",
            (st, _now(), tid),
        )
    return cur.rowcount > 0


def add_complaint_note(ticket_id: str, note: str, *, author: str = "agent") -> bool:
    init_db()

    tid = (ticket_id or "").upper().strip()
    note = (note or "").strip()
    if not tid:
        return False
    if not note:
        raise ValueError("note cannot be empty")

    complaint = get_complaint(tid)
    if not complaint:
        return False

    notes = list(complaint.notes or [])
    notes.append({"note": note, "author": author, "created_at": _now()})

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET notes_json = ?, updated_at = ? WHERE ticket_id = ?",
            (json.dumps(notes), _now(), tid),
        )
    return cur.rowcount > 0


def create_escalation(
    *,
    ticket_id: str,
    user_id: str,
    reason: str,
    messages: Optional[list[dict[str, Any]]] = None,
) -> str:
    init_db()

    created_at = _now()
    reason = (reason or "").strip() or "complex_case"
    uid = (user_id or "").strip() or "unknown"
    tid = (ticket_id or "").upper().strip() or "WC-UNKNOWN"
    msgs = messages if isinstance(messages, list) else []

    def _generate_escalation_id() -> str:
        import random
        import string

        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ESC-{chars}"

    for _ in range(3):
        esc_id = _generate_escalation_id()
        try:
            with _connect() as conn:
                conn.execute(
                    f"""
                    INSERT INTO {ESCALATIONS_TABLE}(
                        escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        esc_id,
                        tid,
                        uid,
                        reason,
                        "WAITING",
                        json.dumps(msgs),
                        created_at,
                        created_at,
                    ),
                )
            return esc_id
        except sqlite3.IntegrityError:
            continue

    raise RuntimeError("Failed to allocate a unique escalation_id")


def list_escalations(*, status: str | None = None) -> list[Escalation]:
    init_db()
    st = (status or "").upper().strip() if status else None

    with _connect() as conn:
        if st:
            rows = conn.execute(
                f"""
                SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
                FROM {ESCALATIONS_TABLE}
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (st,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
                FROM {ESCALATIONS_TABLE}
                ORDER BY created_at DESC
                """
            ).fetchall()

    items: list[Escalation] = []
    for row in rows:
        msgs = _safe_json_loads(row[5], default=[])
        if not isinstance(msgs, list):
            msgs = []
        items.append(
            Escalation(
                escalation_id=row[0],
                ticket_id=row[1],
                user_id=row[2],
                reason=row[3],
                status=row[4],
                messages=msgs,
                created_at=row[6],
                updated_at=row[7],
            )
        )
    return items


def get_escalation(escalation_id: str) -> Escalation | None:
    init_db()
    eid = (escalation_id or "").upper().strip()
    if not eid:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
            FROM {ESCALATIONS_TABLE}
            WHERE escalation_id = ?
            """,
            (eid,),
        ).fetchone()

    if not row:
        return None

    msgs = _safe_json_loads(row[5], default=[])
    if not isinstance(msgs, list):
        msgs = []

    return Escalation(
        escalation_id=row[0],
        ticket_id=row[1],
        user_id=row[2],
        reason=row[3],
        status=row[4],
        messages=msgs,
        created_at=row[6],
        updated_at=row[7],
    )


def append_escalation_message(*, escalation_id: str, sender: str, text: str) -> bool:
    init_db()

    eid = (escalation_id or "").upper().strip()
    sender = (sender or "").strip().lower() or "user"
    text = (text or "").strip()
    if not eid or not text:
        return False

    esc = get_escalation(eid)
    if not esc:
        return False

    msgs = list(esc.messages or [])
    msgs.append({"sender": sender, "text": text, "created_at": _now()})

    new_status = esc.status
    if esc.status == "WAITING" and sender == "agent":
        new_status = "ACTIVE"

    with _connect() as conn:
        cur = conn.execute(
            f"""
            UPDATE {ESCALATIONS_TABLE}
            SET messages_json = ?, status = ?, updated_at = ?
            WHERE escalation_id = ?
            """,
            (json.dumps(msgs), new_status, _now(), eid),
        )
    return cur.rowcount > 0


def set_escalation_status(escalation_id: str, status: str) -> bool:
    init_db()

    eid = (escalation_id or "").upper().strip()
    st = (status or "").upper().strip()
    if not eid:
        return False
    if st not in ALLOWED_ESCALATION_STATUSES:
        raise ValueError(f"Invalid escalation status: {st!r}")

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {ESCALATIONS_TABLE} SET status = ?, updated_at = ? WHERE escalation_id = ?",
            (st, _now(), eid),
        )
    return cur.rowcount > 0


def close_escalation(escalation_id: str) -> bool:
    return set_escalation_status(escalation_id, "CLOSED")


def find_open_escalation_for_user(user_id: str) -> Escalation | None:
    """Find the most recent non-closed escalation for a user."""

    init_db()
    uid = (user_id or "").strip() or "unknown"
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
            FROM {ESCALATIONS_TABLE}
            WHERE user_id = ? AND status != 'CLOSED'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (uid,),
        ).fetchone()

    if not row:
        return None

    msgs = _safe_json_loads(row[5], default=[])
    if not isinstance(msgs, list):
        msgs = []

    return Escalation(
        escalation_id=row[0],
        ticket_id=row[1],
        user_id=row[2],
        reason=row[3],
        status=row[4],
        messages=msgs,
        created_at=row[6],
        updated_at=row[7],
    )


def list_connections() -> list[Connection]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, ticket_id, name, address, phone, email, status, created_at
            FROM {NEW_CONNECTIONS_TABLE}
            ORDER BY created_at DESC
            """
        ).fetchall()
    items: list[Connection] = []
    for row in rows:
        items.append(
            Connection(
                id=row[0],
                ticket_id=row[1],
                name=row[2],
                address=row[3],
                phone=row[4] or "",
                email=row[5] or "",
                status=row[6],
                created_at=row[7],
            )
        )
    return items


def get_connection(ticket_id: str) -> Connection | None:
    init_db()
    tid = (ticket_id or "").upper().strip()
    if not tid:
        return None
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT id, ticket_id, name, address, phone, email, status, created_at
            FROM {NEW_CONNECTIONS_TABLE}
            WHERE ticket_id = ?
            """,
            (tid,),
        ).fetchone()
        if not row:
            return None
        return Connection(
            id=row[0],
            ticket_id=row[1],
            name=row[2],
            address=row[3],
            phone=row[4] or "",
            email=row[5] or "",
            status=row[6],
            created_at=row[7],
        )


def create_connection_request(data: dict) -> str:
    """Create a new connection request and return ticket_id."""

    init_db()
    created_at = _now()

    def _generate_ticket_id() -> str:
        import random
        import string
        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"NC-{chars}"

    name = data.get("name", "").strip()
    address = data.get("address", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()

    if not name or not address:
        raise ValueError("name and address required")

    tid = _generate_ticket_id()
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {NEW_CONNECTIONS_TABLE}(
                ticket_id, name, address, phone, email, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tid, name, address, phone, email, "pending", created_at),
        )
    from .logger import logger
    logger.info(f"Created connection request ticket={tid} name={name} address={address}")
    return f"Connection request #{tid} created successfully for {name}."


