from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import os
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import asdict
from pathlib import Path

from .config import config
from .logger import logger
from .storage import (
    list_complaints as storage_list_complaints,
    get_complaint as storage_get_complaint,
    set_complaint_status as storage_set_complaint_status,
    add_complaint_note as storage_add_complaint_note,
    list_escalations as storage_list_escalations,
    get_escalation as storage_get_escalation,
    append_escalation_message as storage_append_escalation_message,
    close_escalation as storage_close_escalation,
    find_open_escalation_for_user as storage_find_open_escalation_for_user,
    get_session_context as storage_get_session_context,
    upsert_session_context as storage_upsert_session_context,
    log_conversation_turn as storage_log_conversation_turn,
)

from .context_engine import context_redact_pii, context_manager


def _require_admin(authorization: str | None) -> None:
    """Simple admin token auth (API-only hooks; UI already exists)."""

    admin_token = os.getenv("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing admin bearer token")
    provided = authorization.split(" ", 1)[1].strip()
    if provided != admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")


class IntentLabelRequest(BaseModel):
    label: str
    notes: Optional[str] = None
    approved_by: Optional[str] = None


class IntentDeployRequest(BaseModel):
    handler: Optional[str] = None


class IntentActivateRequest(BaseModel):
    approved_by: Optional[str] = None
    role: Optional[str] = None  # "admin" bypasses 2-approval rule


# Log startup
logger.info(f"Starting Water Utility Chatbot with config: {config}")

# Groq-only: configuration validation happens in config.py
logger.info(f"Groq LLM configured with model: {config.groq_model}")

# ---------------------------
# FastAPI App Setup
# ---------------------------
app = FastAPI(title="Water Utility Chatbot", version="1.0.0")

# Production CORS: allow all origins for demo purposes
# In production, you should restrict this to your domain
_cors_allow_origins = [
    "*",  # Allow all origins for demo
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for production
frontend_path = Path(__file__).parent.parent / "frontend" / "aqua-chat-modern-main" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Catch-all route to serve the frontend (SPA fallback)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    #Only block API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    #Admin SPA
    # Check if it's an admin route
    if full_path == "admin" or full_path == "admin/":
        admin_path = Path(__file__).parent.parent / "frontend" / "admin" / "dist"
        index_file = admin_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

    # Default to customer chat frontend
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    raise HTTPException(status_code=404, detail="Frontend not built")

# Session memory (per phone number)
sessions = {}  # Keep for backward compatibility, but not used in new implementation

# ---------------------------
# Request body model
# ---------------------------
class ChatRequest(BaseModel):
    # "phone" is the original field used by the WhatsApp-style flows.
    # The web UI may send "user_id" instead; accept either for compatibility.
    phone: Optional[str] = None
    user_id: Optional[str] = None
    message: str


class ClearChatRequest(BaseModel):
    phone: Optional[str] = None
    user_id: Optional[str] = None


# ---------------------------
# Admin API models
# ---------------------------
class ComplaintStatusUpdate(BaseModel):
    status: str


class ComplaintNoteCreate(BaseModel):
    note: str


class EscalationReplyCreate(BaseModel):
    message: str



# ---------------------------
# CHAT ENDPOINT
# ---------------------------
@app.post("/chat")
def chat(data: ChatRequest):
    phone = data.phone or data.user_id or "demo-user"
    message = data.message

    # Use the new orchestrator
    from .orchestrator import orchestrator
    from .context_engine import context_redact_pii

    result = orchestrator.handle_request(phone, message)

    # Log conversation turn
    try:
        storage_log_conversation_turn(
            user_id=phone,
            role="user",
            text_redacted=context_redact_pii(message),
            text_original=message,
            flow=None,  # Will be updated by context manager
            intent=str(result.get("intent") or ""),
            confidence=float(result.get("confidence") or 0.0),
        )
        storage_log_conversation_turn(
            user_id=phone,
            role="bot",
            text_redacted=context_redact_pii(result["reply"]),
            text_original=result["reply"],
            flow=None,  # Will be updated by context manager
            intent=str(result.get("intent") or ""),
            confidence=float(result.get("confidence") or 0.0),
        )
    except Exception as e:
        logger.warning(f"conversation_history.log_failed err={e}")

    return {
        "reply": result["reply"],
        "intent": result.get("intent"),
        "confidence": result.get("confidence", 0.0),
        "entities": result.get("entities", {}),
        "tier": "high",  # Simplified for now
        "auto_escalated": result.get("escalated", False),
        "escalation_reason": None,  # Will be added to context later
        "active_agent": result.get("active_agent"),
    }


@app.post("/chat/clear")
def clear_chat(data: ClearChatRequest):
    """Clear a user's session context for a fresh conversation."""
    user_id = data.phone or data.user_id or "demo-user"
    context = context_manager.reset_context({"user_id": user_id})
    context_manager.save_context(user_id, context)

    # Backward compatibility: clear legacy in-memory session cache as well.
    try:
        sessions.pop(user_id, None)
    except Exception:
        pass

    return {"status": "cleared"}


@app.get("/chat/updates")
def chat_updates(user_id: str, after: int = 0):
    """Polling endpoint for the customer UI to receive agent replies.

    Returns any new escalation messages after the given index.
    """

    if after < 0:
        after = 0

    esc = storage_find_open_escalation_for_user(user_id)
    if not esc:
        return {"status": "none", "messages": [], "next_after": 0}

    msgs = esc.messages or []
    if after > len(msgs):
        after = len(msgs)

    return {
        "status": esc.status,
        "escalation_id": esc.escalation_id,
        "ticket_id": esc.ticket_id,
        "messages": msgs[after:],
        "next_after": len(msgs),
    }


# ---------------------------
# Admin: Complaints
# ---------------------------
@app.get("/admin/complaints")
def admin_list_complaints():
    """List complaints (summary)."""

    complaints = storage_list_complaints()
    return [
        {
            "ticket_id": c.ticket_id,
            "issue": c.issue,
            "status": c.status,
            "area": c.area,
        }
        for c in complaints
    ]


@app.get("/admin/complaints/{ticket_id}")
def admin_get_complaint(ticket_id: str):
    c = storage_get_complaint(ticket_id)
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return asdict(c)


@app.post("/admin/complaints/{ticket_id}/status")
def admin_update_complaint_status(ticket_id: str, body: ComplaintStatusUpdate):
    try:
        ok = storage_set_complaint_status(ticket_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c = storage_get_complaint(ticket_id)
    return {"success": True, "complaint": asdict(c) if c else None}


@app.post("/admin/complaints/{ticket_id}/note")
def admin_add_complaint_note(ticket_id: str, body: ComplaintNoteCreate):
    try:
        ok = storage_add_complaint_note(ticket_id, body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c = storage_get_complaint(ticket_id)
    return {"success": True, "complaint": asdict(c) if c else None}


# ---------------------------
# Admin: Escalations
# ---------------------------
@app.get("/admin/escalations")
def admin_list_escalations():
    escs = storage_list_escalations()
    return [
        {
            "escalation_id": e.escalation_id,
            "ticket_id": e.ticket_id,
            "user_id": e.user_id,
            "reason": e.reason,
            "status": e.status,
            "updated_at": e.updated_at,
        }
        for e in escs
    ]


@app.get("/admin/escalations/{escalation_id}")
def admin_get_escalation(escalation_id: str):
    e = storage_get_escalation(escalation_id)
    if not e:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return asdict(e)


@app.post("/admin/escalations/{escalation_id}/reply")
def admin_reply_escalation(escalation_id: str, body: EscalationReplyCreate):
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message cannot be empty")

    ok = storage_append_escalation_message(
        escalation_id=escalation_id, sender="agent", text=msg
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Escalation not found")

    e = storage_get_escalation(escalation_id)
    return {"success": True, "escalation": asdict(e) if e else None}


@app.post("/admin/escalations/{escalation_id}/close")
def admin_close_escalation(escalation_id: str):
    ok = storage_close_escalation(escalation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Escalation not found")
    e = storage_get_escalation(escalation_id)
    return {"success": True, "escalation": asdict(e) if e else None}


# ---------------------------
# Admin: Intent discovery suggestions
# ---------------------------
@app.get("/admin/intent_suggestions")
def admin_list_intent_suggestions(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_SUGGESTIONS_TABLE
    import sqlite3

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT suggestion_id, label_suggestion, confidence_score, sample_utts_json, summary, status, created_at, updated_at
            FROM {INTENT_SUGGESTIONS_TABLE}
            ORDER BY created_at DESC
            LIMIT 200
            """
        ).fetchall()

    items = []
    for r in rows:
        try:
            sample = json.loads(r[3] or "[]")
        except Exception:
            sample = []
        items.append(
            {
                "suggestion_id": r[0],
                "label_suggestion": r[1],
                "confidence_score": r[2],
                "sample_utts": sample,
                "summary": r[4],
                "status": r[5],
                "created_at": r[6],
                "updated_at": r[7],
            }
        )
    return items


@app.get("/admin/intent_suggestions/{suggestion_id}")
def admin_get_intent_suggestion(
    suggestion_id: str, authorization: str | None = Header(default=None)
):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_SUGGESTIONS_TABLE
    import sqlite3

    sid = (suggestion_id or "").strip().upper()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"""SELECT suggestion_id, label_suggestion, confidence_score, sample_utts_json, summary, example_action, status, groq_json, created_at, updated_at
            FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?""",
            (sid,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    try:
        sample = json.loads(row[3] or "[]")
    except Exception:
        sample = []
    groq_json = None
    if row[7]:
        try:
            groq_json = json.loads(row[7])
        except Exception:
            groq_json = row[7]
    return {
        "suggestion_id": row[0],
        "label_suggestion": row[1],
        "confidence_score": row[2],
        "sample_utts": sample,
        "summary": row[4],
        "example_action": row[5],
        "status": row[6],
        "groq": groq_json,
        "created_at": row[8],
        "updated_at": row[9],
    }


@app.post("/admin/intent_suggestions/{suggestion_id}/label")
def admin_label_intent_suggestion(
    suggestion_id: str,
    body: IntentLabelRequest,
    authorization: str | None = Header(default=None),
):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_SUGGESTIONS_TABLE, INTENT_LABELS_TABLE
    import sqlite3

    sid = (suggestion_id or "").strip().upper()
    label = (body.label or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="label is required")
    approved_by = (body.approved_by or "admin").strip()
    notes = (body.notes or "").strip() or None

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT suggestion_id FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?",
            (sid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        conn.execute(
            f"""INSERT INTO {INTENT_LABELS_TABLE}(suggestion_id, label, approved_by, notes, created_at)
            VALUES (?, ?, ?, ?, ?)""",
            (sid, label, approved_by, notes, datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()),
        )
        conn.execute(
            f"UPDATE {INTENT_SUGGESTIONS_TABLE} SET status = 'APPROVED', updated_at = ? WHERE suggestion_id = ?",
            (datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(), sid),
        )
        conn.commit()

    logger.info(
        "intent_discovery.label",
        extra={"extra_data": {"suggestion_id": sid, "label": label, "approved_by": approved_by}},
    )
    return {"success": True, "suggestion_id": sid, "label": label}


@app.post("/admin/intent_suggestions/{suggestion_id}/deploy")
def admin_deploy_intent_suggestion(
    suggestion_id: str,
    body: IntentDeployRequest | None = None,
    authorization: str | None = Header(default=None),
):
    """Deploy to *staging* table `intent_candidates` only (active=false).

    Hard requirement: never auto-deploy to production. This endpoint only stages.
    """

    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_SUGGESTIONS_TABLE, INTENT_CANDIDATES_TABLE, INTENT_LABELS_TABLE
    import sqlite3

    sid = (suggestion_id or "").strip().upper()
    handler = (body.handler if body else None) or None
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        sug = conn.execute(
            f"SELECT suggestion_id, label_suggestion, status FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?",
            (sid,),
        ).fetchone()
        if not sug:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        if str(sug[2]) not in {"APPROVED", "DEPLOYED"}:
            raise HTTPException(status_code=400, detail="Suggestion must be APPROVED before deploy")

        # Require at least one human label record before staging.
        lbl = conn.execute(
            f"SELECT label FROM {INTENT_LABELS_TABLE} WHERE suggestion_id = ? ORDER BY id DESC LIMIT 1",
            (sid,),
        ).fetchone()
        if not lbl:
            raise HTTPException(status_code=400, detail="No human label found for suggestion")
        label = str(lbl[0])

        candidate_id = f"CAND-{sid}"
        approvals = [{"approved_by": "admin", "at": now}]
        conn.execute(
            f"""INSERT OR REPLACE INTO {INTENT_CANDIDATES_TABLE}(
                candidate_id, source_suggestion_id, label, handler, active, approvals_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (candidate_id, sid, label, handler, 0, json.dumps(approvals), now, now),
        )

        conn.execute(
            f"UPDATE {INTENT_SUGGESTIONS_TABLE} SET status = 'DEPLOYED', updated_at = ? WHERE suggestion_id = ?",
            (now, sid),
        )
        conn.commit()

    logger.info(
        "intent_discovery.deploy_staging",
        extra={"extra_data": {"suggestion_id": sid, "candidate_id": candidate_id, "label": label}},
    )
    return {"success": True, "candidate_id": candidate_id, "active": False}


@app.post("/admin/intent_suggestions/{suggestion_id}/reject")
def admin_reject_intent_suggestion(
    suggestion_id: str, authorization: str | None = Header(default=None)
):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_SUGGESTIONS_TABLE
    import sqlite3

    sid = (suggestion_id or "").strip().upper()
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT suggestion_id FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?",
            (sid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        conn.execute(
            f"UPDATE {INTENT_SUGGESTIONS_TABLE} SET status = 'REJECTED', updated_at = ? WHERE suggestion_id = ?",
            (now, sid),
        )
        conn.commit()

    logger.info(
        "intent_discovery.reject",
        extra={"extra_data": {"suggestion_id": sid}},
    )
    return {"success": True}


@app.post("/admin/intent_suggestions/{suggestion_id}/rollback")
def admin_rollback_intent_suggestion(
    suggestion_id: str, authorization: str | None = Header(default=None)
):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_SUGGESTIONS_TABLE, INTENT_CANDIDATES_TABLE
    import sqlite3

    sid = (suggestion_id or "").strip().upper()
    candidate_id = f"CAND-{sid}"
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"DELETE FROM {INTENT_CANDIDATES_TABLE} WHERE candidate_id = ?",
            (candidate_id,),
        )
        conn.execute(
            f"UPDATE {INTENT_SUGGESTIONS_TABLE} SET status = 'APPROVED', updated_at = ? WHERE suggestion_id = ?",
            (now, sid),
        )
        conn.commit()

    logger.info(
        "intent_discovery.rollback",
        extra={"extra_data": {"suggestion_id": sid, "candidate_id": candidate_id}},
    )
    return {"success": True}


@app.get("/admin/intent_candidates")
def admin_list_intent_candidates(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_CANDIDATES_TABLE
    import sqlite3

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"""SELECT candidate_id, source_suggestion_id, label, handler, active, approvals_json, created_at, updated_at
            FROM {INTENT_CANDIDATES_TABLE}
            ORDER BY created_at DESC
            LIMIT 200"""
        ).fetchall()
    out = []
    for r in rows:
        try:
            approvals = json.loads(r[5] or "[]")
        except Exception:
            approvals = []
        out.append(
            {
                "candidate_id": r[0],
                "source_suggestion_id": r[1],
                "label": r[2],
                "handler": r[3],
                "active": bool(int(r[4] or 0)),
                "approvals": approvals,
                "created_at": r[6],
                "updated_at": r[7],
            }
        )
    return out


@app.post("/admin/intent_candidates/{candidate_id}/activate")
def admin_activate_intent_candidate(
    candidate_id: str,
    body: IntentActivateRequest,
    authorization: str | None = Header(default=None),
):
    """Activate a staged candidate intent.

    Safety requirement:
    - Never auto-activate. This endpoint requires admin token.
    - Two human approvals required unless role==admin.
    """

    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_CANDIDATES_TABLE
    import sqlite3

    cid = (candidate_id or "").strip().upper()
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    approver = (body.approved_by or "admin").strip()
    role = (body.role or "").strip().lower()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT approvals_json, active FROM {INTENT_CANDIDATES_TABLE} WHERE candidate_id = ?",
            (cid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found")

        try:
            approvals = json.loads(row[0] or "[]")
        except Exception:
            approvals = []
        if not isinstance(approvals, list):
            approvals = []

        approvals.append({"approved_by": approver, "at": now})
        unique_approvers = {str(a.get("approved_by")) for a in approvals if isinstance(a, dict) and a.get("approved_by")}

        can_activate = (role == "admin") or (len(unique_approvers) >= 2)
        active = 1 if can_activate else 0

        conn.execute(
            f"UPDATE {INTENT_CANDIDATES_TABLE} SET approvals_json = ?, active = ?, updated_at = ? WHERE candidate_id = ?",
            (json.dumps(approvals), active, now, cid),
        )
        conn.commit()

    logger.info(
        "intent_discovery.activate",
        extra={"extra_data": {"candidate_id": cid, "active": bool(active), "approver": approver, "role": role}},
    )
    return {"success": True, "candidate_id": cid, "active": bool(active), "unique_approvers": len(unique_approvers)}


@app.post("/admin/intent_candidates/{candidate_id}/deactivate")
def admin_deactivate_intent_candidate(
    candidate_id: str, authorization: str | None = Header(default=None)
):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_CANDIDATES_TABLE
    import sqlite3

    cid = (candidate_id or "").strip().upper()
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            f"UPDATE {INTENT_CANDIDATES_TABLE} SET active = 0, updated_at = ? WHERE candidate_id = ?",
            (now, cid),
        )
        if cur.rowcount <= 0:
            raise HTTPException(status_code=404, detail="Candidate not found")
        conn.commit()

    logger.info(
        "intent_discovery.deactivate",
        extra={"extra_data": {"candidate_id": cid}},
    )
    return {"success": True, "candidate_id": cid, "active": False}


@app.post("/admin/intent_suggestions/{suggestion_id}/test")
def admin_test_intent_suggestion(
    suggestion_id: str, authorization: str | None = Header(default=None)
):
    _require_admin(authorization)
    from .intent_discovery import test_candidate_intent

    # Runs the lightweight staging test and stores metrics for audit.
    return test_candidate_intent(suggestion_id)


@app.get("/admin/intent_metrics")
def admin_intent_metrics(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    from .storage import DB_PATH, INTENT_METRICS_TABLE
    import sqlite3

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f"""SELECT candidate_id, precision, recall, f1, evaluated_at, details_json
            FROM {INTENT_METRICS_TABLE}
            ORDER BY evaluated_at DESC
            LIMIT 200"""
        ).fetchall()

    out = []
    for r in rows:
        out.append(
            {
                "candidate_id": r[0],
                "precision": r[1],
                "recall": r[2],
                "f1": r[3],
                "evaluated_at": r[4],
                "details": json.loads(r[5] or "{}") if isinstance(r[5], str) else {},
            }
        )
    return out

# ---------------------------
# Health Endpoint
# ---------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": config.llm_provider,
        "groq_ready": True,
        "cors_origins": config.cors_origins,
    }


@app.get("/health/llm")
def health_llm():
    """Groq health check endpoint."""

    h = groq_health_check()
    if h.status == "ok":
        return {"provider": h.provider, "status": "ok"}
    return {"provider": h.provider, "status": "error", "detail": h.detail}


# ---------------------------
# TEST LLM CONNECTION
# ---------------------------
@app.get("/test_llm")
def test_llm():
    """Legacy endpoint kept for convenience; now Groq-only."""

    try:
        result = _safe_classify("hello", {})
        return {"success": True, "provider": "groq", "result": result}
    except Exception as e:
        logger.error(f"LLM test failed: {str(e)}")
        return {"success": False, "error": str(e), "provider": config.llm_provider}
