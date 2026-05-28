from fastapi import FastAPI, HTTPException, Header, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import os
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import asdict, dataclass
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))  # Add project root to path

from backend.orchestrator import Orchestrator
from backend.intent_pipeline import IntentPipeline
from backend.tool_executor import tool_executor
from backend.context_engine import context_manager, context_redact_pii
from backend.config import config
from backend.logger import logger
from backend.auth import auth_service, AdminUser, Permission, UserRole, PIIProtection
from backend.rate_limiter import rate_limiter, get_client_key, RateLimitMiddleware
from backend.validation import sanitize_input


from backend.storage import (
    assign_complaint as storage_assign_complaint,
    list_complaints as storage_list_complaints,
    get_complaint as storage_get_complaint,
    set_complaint_status as storage_set_complaint_status,
    set_complaint_priority as storage_set_complaint_priority,
    add_complaint_note as storage_add_complaint_note,
    list_user_feedback as storage_list_user_feedback,
    list_escalations as storage_list_escalations,
    get_escalation as storage_get_escalation,
    append_escalation_message as storage_append_escalation_message,
    close_escalation as storage_close_escalation,
    find_open_escalation_for_user as storage_find_open_escalation_for_user,
    get_session_context as storage_get_session_context,
    upsert_session_context as storage_upsert_session_context,
    log_conversation_turn as storage_log_conversation_turn,
)

intent_engine = IntentPipeline()
orchestrator = Orchestrator(config, context_manager, intent_engine, tool_executor)


def _require_admin(authorization: str | None) -> str:
    """Verify the request carries a valid admin credential and return the admin identifier.

    Accepts two token types so both auth flows work:
    1. Static ADMIN_TOKEN from .env  — used by scripts / curl / legacy tools
    2. Session token from /auth/login — used by the React admin dashboard
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing admin bearer token")

    provided = authorization.split(" ", 1)[1].strip()

    # --- Path 1: static ADMIN_TOKEN ---
    admin_token = os.getenv("ADMIN_TOKEN")
    if admin_token and provided == admin_token:
        return "static_admin"  # valid

    # --- Path 2: session token issued by /auth/login ---
    user = auth_service.verify_token(provided)
    if user is not None:
        return user.username  # valid session token

    raise HTTPException(status_code=403, detail="Invalid or expired admin token")


class IntentLabelRequest(BaseModel):
    label: str
    notes: Optional[str] = None
    approved_by: Optional[str] = None


class IntentDeployRequest(BaseModel):
    handler: Optional[str] = None


class IntentActivateRequest(BaseModel):
    approved_by: Optional[str] = None
    role: Optional[str] = None  # "admin" bypasses 2-approval rule


@dataclass
class SLATracker:
    uptime_start: str = datetime.now(timezone.utc).isoformat()
    total_requests: int = 0
    sla_latency_successes: int = 0  # < 3.0 seconds responses
    error_count: int = 0
    total_latency_seconds: float = 0.0

    @property
    def latency_sla_compliance_pct(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return (self.sla_latency_successes / self.total_requests) * 100.0

    @property
    def error_rate_pct(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.error_count / self.total_requests) * 100.0

    @property
    def estimated_availability_pct(self) -> float:
        if self.total_requests == 0:
            return 99.9
        # Server unhandled failures deduct from overall operational availability
        unavailability = (self.error_count / self.total_requests) * 0.5
        return max(0.0, min(100.0, 100.0 - unavailability))

sla_tracker = SLATracker()


# Log startup
logger.info(f"Starting Water Utility Chatbot with config: {config}")

# Groq-only: configuration validation happens in config.py
logger.info(f"Groq LLM configured with model: {config.groq_model}")

# ---------------------------
# FastAPI App Setup
# ---------------------------
app = FastAPI(
    title="Water Utility Chatbot",
    version="1.0.0",
    # Hide detailed error info from API responses in non-debug mode
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# CORS — use the origins from config (set via CORS_ORIGINS env var).
# In debug mode we also allow localhost dev servers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

@app.middleware("http")
async def cookie_to_authorization_middleware(request: Request, call_next):
    """Intercepts requests to automatically inject the secure HttpOnly cookie as a Bearer token."""
    if "authorization" not in request.headers:
        cookie_token = request.cookies.get("admin_session")
        if cookie_token:
            scope_headers = [h for h in request.scope.get("headers", []) if h[0].lower() != b"authorization"]
            scope_headers.append((b"authorization", f"Bearer {cookie_token}".encode("utf-8")))
            request.scope["headers"] = scope_headers
    return await call_next(request)


# Mount static files for production
PROJECT_ROOT = Path(__file__).resolve().parent
frontend_path = PROJECT_ROOT / "frontend" / "aqua-chat-modern-main" / "dist"
admin_frontend_path = PROJECT_ROOT / "frontend" / "admin" / "dist"

# Ensure static directories exist so they can be unconditionally mounted safely
# without raising Starlette's Directory nonexistent RuntimeError on startup.
assets_path = frontend_path / "assets"
assets_path.mkdir(parents=True, exist_ok=True)

admin_assets_path = admin_frontend_path / "assets"
admin_assets_path.mkdir(parents=True, exist_ok=True)

# Mount Vite assets so resource requests like /assets/... are served with correct MIME types
app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
app.mount("/admin/assets", StaticFiles(directory=str(admin_assets_path)), name="admin_assets")

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


class ComplaintAssignUpdate(BaseModel):
    assigned_to: Optional[str] = None


class ComplaintPriorityUpdate(BaseModel):
    priority: str


class EscalationReplyCreate(BaseModel):
    message: str


def _complaint_to_dict(complaint: Any) -> dict[str, Any]:
    from backend.regulatory import compute_sla_status
    return {
        "ticket_id": complaint.ticket_id,
        "name": complaint.name,
        "area": complaint.area,
        "issue": complaint.issue,
        "status": complaint.status,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "phone": None,
        "assigned_to": complaint.assigned_to,
        "notes": complaint.notes or [],
        "category": complaint.category,
        "priority": complaint.priority,
        "sla_due_at": complaint.sla_due_at,
        "sla_status": compute_sla_status(complaint.sla_due_at, complaint.status),
    }


def _escalation_to_dict(escalation: Any) -> dict[str, Any]:
    return {
        "escalation_id": escalation.escalation_id,
        "ticket_id": escalation.ticket_id,
        "user_id": escalation.user_id,
        "reason": escalation.reason,
        "status": escalation.status,
        "messages": escalation.messages or [],
        "created_at": escalation.created_at,
        "updated_at": escalation.updated_at,
    }



# ---------------------------
# TEST ENDPOINT
# ---------------------------

# ---------------------------
# CHAT ENDPOINT
# ---------------------------
from backend.context_engine import context_redact_pii

@app.post("/chat")
async def chat(data: ChatRequest, request: Request):
    """Main chat endpoint.

    Applies:
    - Per-IP rate limiting (protects Groq budget)
    - Input sanitization (strips null bytes / control chars)
    - Graceful LLM timeout / error fallback
    - Conversation logging for admin dashboard
    """
    import requests as _requests

    # 1. Rate limit — keyed by IP or user_id
    phone = data.phone or data.user_id or "demo-user"
    client_key = get_client_key(request, phone)
    rate_limiter.check(client_key)

    # 2. Sanitize input — strip null bytes, control chars, excessive whitespace, jailbreak patterns, and blocked URLs
    from backend.security import sanitize_input as secure_sanitize, SecurityViolation
    try:
        message = secure_sanitize(data.message or "")
    except SecurityViolation as exc:
        logger.warning(f"Security violation blocked: {exc}")
        return {
            "response": str(exc),
            "intent": "out_of_scope",
            "confidence": 1.0,
            "entities": {},
            "tier": "high",
            "escalated": False,
            "auto_escalated": False,
            "escalation_reason": "security_violation",
            "active_agent": "general_agent",
            "tool_used": None,
            "tool_reason": None,
            "tool_trace": [],
        }
    if not message:
        return {
            "response": "Please send a message and I'll be happy to help.",
            "intent": None,
            "confidence": 0.0,
            "entities": {},
            "tier": "high",
            "escalated": False,
            "auto_escalated": False,
            "escalation_reason": None,
            "active_agent": None,
            "tool_used": None,
            "tool_reason": None,
            "tool_trace": [],
        }

    # 3. Enforce a maximum message length to prevent prompt-stuffing
    MAX_MSG_LEN = 1000
    if len(message) > MAX_MSG_LEN:
        message = message[:MAX_MSG_LEN]

    # Track metrics for SLA calculations
    start_time = time.time()
    sla_tracker.total_requests += 1

    try:
        # Enforce strict Service Level Agreement latency target: < 3 seconds
        result = await asyncio.wait_for(
            orchestrator.process(message=message, user_id=phone),
            timeout=3.0
        )
        
        # Calculate latency and count latency SLA successes
        latency = time.time() - start_time
        sla_tracker.total_latency_seconds += latency
        if latency < 3.0:
            sla_tracker.sla_latency_successes += 1
            
    except asyncio.TimeoutError:
        logger.warning(f"SLA Latency Violation: LLM timeout for user={phone} (>3.0s)")
        sla_tracker.error_count += 1
        
        latency = time.time() - start_time
        sla_tracker.total_latency_seconds += latency
        
        return {
            "response": (
                "I'm taking a little longer than usual to respond. "
                "Please try again in a moment."
            ),
            "intent": None,
            "confidence": 0.0,
            "entities": {},
            "tier": "high",
            "escalated": False,
            "auto_escalated": False,
            "escalation_reason": "sla_latency_timeout",
            "active_agent": None,
            "tool_used": None,
            "tool_reason": None,
            "tool_trace": [],
        }
    except _requests.Timeout:
        logger.warning(f"LLM request timeout for user={phone}")
        sla_tracker.error_count += 1
        
        latency = time.time() - start_time
        sla_tracker.total_latency_seconds += latency
        
        return {
            "response": (
                "I'm taking a little longer than usual to respond. "
                "Please try again in a moment."
            ),
            "intent": None,
            "confidence": 0.0,
            "entities": {},
            "tier": "high",
            "escalated": False,
            "auto_escalated": False,
            "escalation_reason": "network_timeout",
            "active_agent": None,
            "tool_used": None,
            "tool_reason": None,
            "tool_trace": [],
        }
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        sla_tracker.error_count += 1
        
        latency = time.time() - start_time
        sla_tracker.total_latency_seconds += latency
        
        return {
            "response": (
                "I'm sorry, something went wrong on my end. "
                "Please try again or type 'human agent' to speak with a representative."
            ),
            "intent": None,
            "confidence": 0.0,
            "entities": {},
            "tier": "high",
            "escalated": False,
            "auto_escalated": False,
            "escalation_reason": "system_error",
            "active_agent": None,
            "tool_used": None,
            "tool_reason": None,
            "tool_trace": [],
        }

    reply_text = result.get("response", "I'm sorry, I couldn't process that.")

    # 4. Log conversation turn for admin dashboard and intent learning
    try:
        storage_log_conversation_turn(
            user_id=phone,
            role="user",
            text_redacted=context_redact_pii(message),
            text_original=message,
            flow=None,
            intent=str(result.get("intent") or ""),
            confidence=float(result.get("confidence") or 0.0),
        )
        storage_log_conversation_turn(
            user_id=phone,
            role="bot",
            text_redacted=context_redact_pii(reply_text),
            text_original=reply_text,
            flow=None,
            intent=str(result.get("intent") or ""),
            confidence=float(result.get("confidence") or 0.0),
        )
    except Exception as log_err:
        logger.warning(f"conversation_history.log_failed err={log_err}")

    return {
        "response": reply_text,
        "intent": result.get("intent"),
        "confidence": result.get("confidence", 0.0),
        "entities": result.get("entities", {}),
        "tier": "high",
        "escalated": result.get("escalated", False),
        "auto_escalated": result.get("escalated", False),
        "escalation_reason": None,
        "active_agent": result.get("active_agent"),
        "tool_used": result.get("tool_used"),
        "tool_reason": result.get("tool_reason"),
        "tool_trace": result.get("tool_trace", []),
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
# Admin: Complaints (Secured)
# ---------------------------
# Note: Admin endpoints are now secured with authentication below


# ---------------------------
# Admin: Escalations (Secured)
# ---------------------------
# Note: Admin escalation endpoints are now secured with authentication below


# ---------------------------
# Admin: Customer PIN Reset
# ---------------------------

class ResetPinRequest(BaseModel):
    new_pin: str


@app.post("/admin/accounts/{account_number}/reset-pin")
def admin_reset_pin(
    account_number: str,
    body: ResetPinRequest,
    authorization: str | None = Header(default=None),
):
    """Reset a customer's PIN. Requires a valid admin bearer token.

    Returns:
        200 {"status": "ok", "account_number": "..."}  on success.
        401 / 403  when the admin token is missing or invalid.
        404  when the account_number does not exist in mock_accounts.
        422  when new_pin is not exactly 4 decimal digits.
        500  on an unexpected database error.
    """
    import sqlite3 as _sqlite3
    from backend.storage import DB_PATH, CUSTOMER_AUTH_TABLE
    from backend.auth import auth_service

    admin_id = _require_admin(authorization)
    from backend.customer_auth import customer_auth_service

    # Fetch before state
    before_state = None
    try:
        with _sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(f"SELECT pin_hash, pin_salt, failed_attempts, locked_until FROM {CUSTOMER_AUTH_TABLE} WHERE account_number = ?", (account_number,)).fetchone()
            if row:
                before_state = {"pin_hash": row[0], "pin_salt": row[1], "failed_attempts": row[2], "locked_until": row[3]}
    except Exception:
        pass

    try:
        customer_auth_service.reset_pin(account_number, body.new_pin)
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=422, detail=detail)
    except _sqlite3.Error:
        raise HTTPException(status_code=500, detail="Internal server error")

    # Fetch after state
    after_state = None
    try:
        with _sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(f"SELECT pin_hash, pin_salt, failed_attempts, locked_until FROM {CUSTOMER_AUTH_TABLE} WHERE account_number = ?", (account_number,)).fetchone()
            if row:
                after_state = {"pin_hash": row[0], "pin_salt": row[1], "failed_attempts": row[2], "locked_until": row[3]}
    except Exception:
        pass

    auth_service.log_admin_action(
        admin_id=admin_id,
        action="RESET_PIN",
        resource=account_number,
        before_state=before_state,
        after_state=after_state
    )

    return {"status": "ok", "account_number": account_number}


@app.post("/admin/escalations/{escalation_id}/close")
def admin_close_escalation(escalation_id: str, authorization: str | None = Header(default=None)):
    admin_id = _require_admin(authorization)
    from backend.storage import get_escalation
    from backend.auth import auth_service
    from dataclasses import asdict

    before_esc = get_escalation(escalation_id)
    before_state = asdict(before_esc) if before_esc else None

    ok = storage_close_escalation(escalation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Escalation not found")
    e = storage_get_escalation(escalation_id)
    after_state = asdict(e) if e else None

    auth_service.log_admin_action(
        admin_id=admin_id,
        action="CLOSE_ESCALATION",
        resource=escalation_id,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "escalation": _escalation_to_dict(e) if e else None}


# ---------------------------
# Admin: Intent discovery suggestions
# ---------------------------
@app.get("/admin/intent_suggestions")
def admin_list_intent_suggestions(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    from backend.storage import DB_PATH, INTENT_SUGGESTIONS_TABLE
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
    from backend.storage import DB_PATH, INTENT_SUGGESTIONS_TABLE
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
    admin_id = _require_admin(authorization)
    from backend.storage import DB_PATH, INTENT_SUGGESTIONS_TABLE, INTENT_LABELS_TABLE
    from backend.auth import auth_service
    import sqlite3

    sid = (suggestion_id or "").strip().upper()
    label = (body.label or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="label is required")
    approved_by = (body.approved_by or "admin").strip()
    notes = (body.notes or "").strip() or None

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT label_suggestion, status FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?",
            (sid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        before_state = {"label": row[0], "status": row[1]}

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
        
        row_after = conn.execute(
            f"SELECT label_suggestion, status FROM {INTENT_SUGGESTIONS_TABLE} WHERE suggestion_id = ?",
            (sid,),
        ).fetchone()
        after_state = {"label": row_after[0], "status": row_after[1]} if row_after else None

    logger.info(
        "intent_discovery.label",
        extra={"extra_data": {"suggestion_id": sid, "label": label, "approved_by": approved_by}},
    )
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="LABEL_INTENT_SUGGESTION",
        resource=sid,
        before_state=before_state,
        after_state=after_state
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

    admin_id = _require_admin(authorization)
    from backend.storage import DB_PATH, INTENT_SUGGESTIONS_TABLE, INTENT_CANDIDATES_TABLE, INTENT_LABELS_TABLE
    from backend.auth import auth_service
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
            
        before_state = {"status": sug[2], "deployed": False}

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
        
        after_state = {
            "status": "DEPLOYED",
            "candidate_id": candidate_id,
            "active": False,
            "approvals": approvals
        }

    logger.info(
        "intent_discovery.deploy_staging",
        extra={"extra_data": {"suggestion_id": sid, "candidate_id": candidate_id, "label": label}},
    )
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="DEPLOY_INTENT_SUGGESTION",
        resource=sid,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "candidate_id": candidate_id, "active": False}




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

    admin_id = _require_admin(authorization)
    from backend.storage import DB_PATH, INTENT_CANDIDATES_TABLE
    from backend.auth import auth_service
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
            
        before_state = {"approvals": json.loads(row[0] or "[]"), "active": bool(int(row[1] or 0))}

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
        
        after_state = {"approvals": approvals, "active": bool(active)}

    logger.info(
        "intent_discovery.activate",
        extra={"extra_data": {"candidate_id": cid, "active": bool(active), "approver": approver, "role": role}},
    )
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="ACTIVATE_INTENT_CANDIDATE",
        resource=cid,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "candidate_id": cid, "active": bool(active), "unique_approvers": len(unique_approvers)}


@app.post("/admin/intent_candidates/{candidate_id}/deactivate")
def admin_deactivate_intent_candidate(
    candidate_id: str, authorization: str | None = Header(default=None)
):
    admin_id = _require_admin(authorization)
    from backend.storage import DB_PATH, INTENT_CANDIDATES_TABLE
    from backend.auth import auth_service
    import sqlite3

    cid = (candidate_id or "").strip().upper()
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT approvals_json, active FROM {INTENT_CANDIDATES_TABLE} WHERE candidate_id = ?",
            (cid,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found")
        before_state = {"approvals": json.loads(row[0] or "[]"), "active": bool(int(row[1] or 0))}

        cur = conn.execute(
            f"UPDATE {INTENT_CANDIDATES_TABLE} SET active = 0, updated_at = ? WHERE candidate_id = ?",
            (now, cid),
        )
        conn.commit()
        
        after_state = {"approvals": before_state["approvals"], "active": False}

    logger.info(
        "intent_discovery.deactivate",
        extra={"extra_data": {"candidate_id": cid}},
    )
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="DEACTIVATE_INTENT_CANDIDATE",
        resource=cid,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "candidate_id": cid, "active": False}


@app.post("/admin/intent_suggestions/{suggestion_id}/test")
def admin_test_intent_suggestion(
    suggestion_id: str, authorization: str | None = Header(default=None)
):
    _require_admin(authorization)
    from backend.intent_discovery import test_candidate_intent

    # Runs the lightweight staging test and stores metrics for audit.
    return test_candidate_intent(suggestion_id)


@app.get("/admin/intent_metrics")
def admin_intent_metrics(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    from backend.storage import DB_PATH, INTENT_METRICS_TABLE
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
# Authentication Endpoints
# ---------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None
    expires_at: Optional[str] = None
    message: Optional[str] = None


@app.post("/auth/login", response_model=LoginResponse)
def admin_login(request: Request, login_data: LoginRequest, response: Response):
    """Authenticate admin user, issue JWT, and set secure HttpOnly cookie."""
    try:
        user = auth_service.authenticate_user(login_data.username, login_data.password)
        token = auth_service.generate_token(user)
        
        # Dynamically evaluate if we should set 'Secure' flag (HTTPS only in production)
        is_secure = request.url.scheme == "https"
        response.set_cookie(
            key="admin_session",
            value=token.token_hash,  # Set the full JWT token hash in the cookie
            httponly=True,
            secure=is_secure,
            samesite="strict",
            max_age=24 * 3600,  # 24 hours
        )
        
        return LoginResponse(
            success=True,
            token=token.token_hash,  # Still returned for backward compatibility
            user_id=user.user_id,
            role=user.role.value,
            expires_at=token.expires_at,
            message="Authentication successful"
        )
    except Exception as e:
        logger.warning(
            "auth.login_failed",
            extra={"extra_data": {"username": login_data.username, "error": str(e)}}
        )
        return LoginResponse(
            success=False,
            message="Invalid credentials"
        )


@app.post("/auth/logout")
def admin_logout(response: Response, authorization: str | None = Header(default=None)):
    """Logout, revoke JWT, and delete secure HttpOnly cookie."""
    # We always delete the cookie regardless of authorization header presence
    response.delete_cookie(
        key="admin_session",
        httponly=True,
        samesite="strict"
    )
    
    if not authorization:
        # If no authorization provided but cookie was deleted, just return success
        return {"success": True, "message": "Logged out successfully"}
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    success = auth_service.revoke_token(token)
    
    if success:
        logger.info("auth.logout_success", extra={"extra_data": {"token": token[:20] + "..."}})
        return {"success": True, "message": "Logged out successfully"}
    else:
        return {"success": False, "message": "Invalid token"}


def get_current_user(authorization: str | None = Header(default=None)) -> AdminUser:
    """Dependency to get current authenticated user."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Extract token from "Bearer <token>"
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    user = auth_service.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


def require_permission(permission: Permission):
    """Dependency factory to require specific permission."""
    def permission_dependency(current_user: AdminUser = Depends(get_current_user)):
        if not auth_service.check_permission(current_user, permission):
            raise HTTPException(status_code=403, detail=f"Permission required: {permission.value}")
        return current_user
    return permission_dependency


# ---------------------------
# User Feedback Endpoints
# ---------------------------

class FeedbackRequest(BaseModel):
    session_id: str
    user_id: str
    rating: int  # 1-5
    text_feedback: Optional[str] = None
    helpful: bool = True


@app.post("/feedback")
def submit_feedback(feedback: FeedbackRequest):
    """Submit user feedback for a conversation session."""
    from backend.storage import create_user_feedback, UserFeedback
    import uuid
    
    if feedback.rating < 1 or feedback.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    feedback_id = f"FB-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    user_feedback = UserFeedback(
        feedback_id=feedback_id,
        session_id=feedback.session_id,
        user_id=feedback.user_id,
        rating=feedback.rating,
        text_feedback=feedback.text_feedback,
        helpful=feedback.helpful,
        timestamp=timestamp
    )
    
    create_user_feedback(user_feedback)
    
    logger.info(
        "feedback.submitted",
        extra={"extra_data": {
            "feedback_id": feedback_id,
            "session_id": feedback.session_id,
            "rating": feedback.rating
        }}
    )
    
    return {"success": True, "feedback_id": feedback_id}


@app.get("/feedback/{session_id}")
def get_session_feedback(session_id: str):
    """Get feedback for a specific session."""
    from backend.storage import get_user_feedback
    
    feedback = get_user_feedback(session_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback found for this session")
    
    return {
        "feedback_id": feedback.feedback_id,
        "session_id": feedback.session_id,
        "user_id": feedback.user_id,
        "rating": feedback.rating,
        "text_feedback": feedback.text_feedback,
        "helpful": feedback.helpful,
        "timestamp": feedback.timestamp
    }


# ---------------------------
# Admin Dashboard Endpoints
# ---------------------------

@app.get("/admin/dashboard")
def admin_dashboard(authorization: str | None = Header(default=None)):
    """Get admin dashboard metrics."""
    from backend.storage import get_dashboard_metrics

    _require_admin(authorization)
    logger.info("admin.dashboard_accessed")

    metrics = get_dashboard_metrics()
    metrics["sla"] = {
        "latency_target_seconds": 3.0,
        "latency_actual_avg_seconds": round(sla_tracker.total_latency_seconds / max(1, sla_tracker.total_requests), 3),
        "latency_sla_compliance_pct": round(sla_tracker.latency_sla_compliance_pct, 2),
        "availability_target_pct": 99.5,
        "availability_actual_pct": round(sla_tracker.estimated_availability_pct, 2),
        "error_rate_target_pct": 1.0,
        "error_rate_actual_pct": round(sla_tracker.error_rate_pct, 2),
        "total_requests": sla_tracker.total_requests,
        "sla_violations": sla_tracker.error_count + (sla_tracker.total_requests - sla_tracker.sla_latency_successes),
    }
    return metrics


@app.get("/admin/sla-metrics")
def get_sla_metrics(authorization: str | None = Header(default=None)):
    """Expose codified Service Level Agreement (SLA) status."""
    _require_admin(authorization)
    return {
        "uptime_start": sla_tracker.uptime_start,
        "latency": {
            "target": "< 3 seconds",
            "actual_avg_seconds": round(sla_tracker.total_latency_seconds / max(1, sla_tracker.total_requests), 3),
            "sla_compliance_rate": f"{round(sla_tracker.latency_sla_compliance_pct, 2)}%"
        },
        "availability": {
            "target": "99.5%",
            "actual": f"{round(sla_tracker.estimated_availability_pct, 2)}%"
        },
        "error_rate": {
            "target": "< 1%",
            "actual": f"{round(sla_tracker.error_rate_pct, 2)}%"
        },
        "total_requests": sla_tracker.total_requests,
        "sla_violations": sla_tracker.error_count
    }


class ResolutionRequest(BaseModel):
    session_id: str
    resolution_status: str  # RESOLVED, UNRESOLVED, ESCALATED
    admin_notes: Optional[str] = None
    resolution_time: Optional[str] = None


@app.post("/admin/resolution")
def admin_set_resolution(
    resolution: ResolutionRequest, 
    current_user: AdminUser = Depends(require_permission(Permission.MANAGE_RESOLUTIONS))
):
    """Set admin resolution status for a session."""
    from backend.storage import create_admin_resolution, AdminResolution
    import uuid
    
    if resolution.resolution_status not in ["RESOLVED", "UNRESOLVED", "ESCALATED"]:
        raise HTTPException(status_code=400, detail="Invalid resolution status")
    
    resolution_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
    admin_user_id = current_user.user_id
    timestamp = datetime.now(timezone.utc).isoformat()
    
    admin_resolution = AdminResolution(
        resolution_id=resolution_id,
        session_id=resolution.session_id,
        admin_user_id=admin_user_id,
        resolution_status=resolution.resolution_status,
        admin_notes=resolution.admin_notes,
        resolution_time=resolution.resolution_time or timestamp,
        timestamp=timestamp
    )
    
    create_admin_resolution(admin_resolution)
    
    logger.info(
        "admin.resolution_set",
        extra={"extra_data": {
            "resolution_id": resolution_id,
            "session_id": resolution.session_id,
            "status": resolution.resolution_status,
            "admin_user_id": admin_user_id
        }}
    )
    
    return {"success": True, "resolution_id": resolution_id}


# ---------------------------
# Protected Admin Endpoints
# ---------------------------

@app.get("/admin/complaints")
def admin_list_complaints(authorization: str | None = Header(default=None)):
    """List all complaints with PII protection based on role."""
    _require_admin(authorization)
    complaints = storage_list_complaints()
    
    # Return complaints without redaction (admin endpoint)
    protected_complaints = []
    for complaint in complaints:
        complaint_dict = {
            "ticket_id": complaint.ticket_id,
            "name": complaint.name,
            "area": complaint.area,
            "issue": complaint.issue,
            "status": complaint.status,
            "created_at": complaint.created_at,
            "updated_at": complaint.updated_at,
            "assigned_to": complaint.assigned_to,
            "category": complaint.category,
            "priority": complaint.priority,
            "sla_due_at": complaint.sla_due_at,
        }
        protected_complaints.append(complaint_dict)
    
    logger.info("admin.complaints_accessed", extra={"extra_data": {"count": len(protected_complaints)}})
    
    return protected_complaints


@app.get("/admin/complaints/{ticket_id}")
def admin_get_complaint_plural(ticket_id: str, authorization: str | None = Header(default=None)):
    """Get a specific complaint for the admin UI."""
    _require_admin(authorization)
    complaint = storage_get_complaint(ticket_id)

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    logger.info("admin.complaint_accessed", extra={"extra_data": {"ticket_id": ticket_id}})

    return _complaint_to_dict(complaint)


@app.get("/admin/complaint/{ticket_id}")
def admin_get_complaint(ticket_id: str, authorization: str | None = Header(default=None)):
    """Backward-compatible singular complaint route."""
    return admin_get_complaint_plural(ticket_id, authorization)


@app.post("/admin/complaints/{ticket_id}/status")
def admin_update_complaint_status(
    ticket_id: str,
    body: ComplaintStatusUpdate,
    authorization: str | None = Header(default=None),
):
    """Update a complaint status from the admin UI."""
    admin_id = _require_admin(authorization)
    from backend.auth import auth_service
    
    before_c = storage_get_complaint(ticket_id)
    before_state = _complaint_to_dict(before_c) if before_c else None
    
    try:
        ok = storage_set_complaint_status(ticket_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint = storage_get_complaint(ticket_id)
    after_state = _complaint_to_dict(complaint) if complaint else None
    logger.info(
        "admin.complaint_status_updated",
        extra={"extra_data": {"ticket_id": ticket_id, "status": body.status}},
    )
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="UPDATE_COMPLAINT_STATUS",
        resource=ticket_id,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "complaint": after_state}


@app.post("/admin/complaints/{ticket_id}/note")
def admin_add_complaint_note(
    ticket_id: str,
    body: ComplaintNoteCreate,
    authorization: str | None = Header(default=None),
):
    """Add an internal admin note to a complaint."""
    admin_id = _require_admin(authorization)
    from backend.auth import auth_service
    
    before_c = storage_get_complaint(ticket_id)
    before_state = _complaint_to_dict(before_c) if before_c else None
    
    try:
        ok = storage_add_complaint_note(ticket_id, body.note, author="admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint = storage_get_complaint(ticket_id)
    after_state = _complaint_to_dict(complaint) if complaint else None
    logger.info("admin.complaint_note_added", extra={"extra_data": {"ticket_id": ticket_id}})
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="ADD_COMPLAINT_NOTE",
        resource=ticket_id,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "complaint": after_state}


@app.post("/admin/complaints/{ticket_id}/assign")
def admin_assign_complaint(
    ticket_id: str,
    body: ComplaintAssignUpdate,
    authorization: str | None = Header(default=None),
):
    """Assign or clear a complaint owner."""
    admin_id = _require_admin(authorization)
    from backend.auth import auth_service
    
    before_c = storage_get_complaint(ticket_id)
    before_state = _complaint_to_dict(before_c) if before_c else None
    
    ok = storage_assign_complaint(ticket_id, body.assigned_to)

    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint = storage_get_complaint(ticket_id)
    after_state = _complaint_to_dict(complaint) if complaint else None
    logger.info("admin.complaint_assigned", extra={"extra_data": {"ticket_id": ticket_id}})
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="ASSIGN_COMPLAINT",
        resource=ticket_id,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "complaint": after_state}


@app.post("/admin/complaints/{ticket_id}/priority")
def admin_update_complaint_priority(
    ticket_id: str,
    body: ComplaintPriorityUpdate,
    authorization: str | None = Header(default=None),
):
    """Update complaint priority and recompute its SLA deadline."""
    admin_id = _require_admin(authorization)
    from backend.auth import auth_service
    
    before_c = storage_get_complaint(ticket_id)
    before_state = _complaint_to_dict(before_c) if before_c else None
    
    try:
        ok = storage_set_complaint_priority(ticket_id, body.priority)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not ok:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint = storage_get_complaint(ticket_id)
    after_state = _complaint_to_dict(complaint) if complaint else None
    logger.info(
        "admin.complaint_priority_updated",
        extra={"extra_data": {"ticket_id": ticket_id, "priority": body.priority}},
    )
    
    auth_service.log_admin_action(
        admin_id=admin_id,
        action="UPDATE_COMPLAINT_PRIORITY",
        resource=ticket_id,
        before_state=before_state,
        after_state=after_state
    )
    return {"success": True, "complaint": after_state}


@app.post("/admin/complaint/{ticket_id}/status")
def admin_update_complaint_status_singular(
    ticket_id: str,
    body: ComplaintStatusUpdate,
    authorization: str | None = Header(default=None),
):
    """Backward-compatible singular complaint status route."""
    return admin_update_complaint_status(ticket_id, body, authorization)


@app.post("/admin/complaint/{ticket_id}/note")
def admin_add_complaint_note_singular(
    ticket_id: str,
    body: ComplaintNoteCreate,
    authorization: str | None = Header(default=None),
):
    """Backward-compatible singular complaint note route."""
    return admin_add_complaint_note(ticket_id, body, authorization)


@app.get("/admin/feedback")
def admin_list_feedback(authorization: str | None = Header(default=None), limit: int = 20):
    """List recent customer feedback for staff review."""
    _require_admin(authorization)
    feedback = storage_list_user_feedback(limit=limit)
    return [
        {
            "feedback_id": item.feedback_id,
            "session_id": item.session_id,
            "user_id": item.user_id,
            "rating": item.rating,
            "text_feedback": item.text_feedback,
            "helpful": item.helpful,
            "timestamp": item.timestamp,
        }
        for item in feedback
    ]


@app.get("/admin/escalations")
def admin_list_escalations(authorization: str | None = Header(default=None)):
    """List all escalations."""
    _require_admin(authorization)
    escalations = storage_list_escalations()
    
    # Return escalations without redaction (admin endpoint)
    protected_escalations = []
    for escalation in escalations:
        escalation_dict = {
            "escalation_id": escalation.escalation_id,
            "ticket_id": escalation.ticket_id,
            "user_id": escalation.user_id,
            "reason": escalation.reason,
            "status": escalation.status,
            "created_at": escalation.created_at,
            "updated_at": escalation.updated_at
        }
        protected_escalations.append(escalation_dict)
    
    logger.info("admin.escalations_accessed", extra={"extra_data": {"count": len(protected_escalations)}})
    
    return protected_escalations


@app.get("/admin/escalations/{escalation_id}")
def admin_get_escalation(escalation_id: str, authorization: str | None = Header(default=None)):
    """Get a specific escalation conversation."""
    _require_admin(authorization)
    escalation = storage_get_escalation(escalation_id)

    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    logger.info("admin.escalation_accessed", extra={"extra_data": {"escalation_id": escalation_id}})
    return _escalation_to_dict(escalation)


@app.post("/admin/escalations/{escalation_id}/reply")
def admin_reply_escalation(
    escalation_id: str,
    body: EscalationReplyCreate,
    authorization: str | None = Header(default=None),
):
    """Append an agent reply to an escalation conversation."""
    _require_admin(authorization)
    ok = storage_append_escalation_message(
        escalation_id=escalation_id,
        sender="agent",
        text=body.message,
    )

    if not ok:
        raise HTTPException(status_code=404, detail="Escalation not found")

    escalation = storage_get_escalation(escalation_id)
    logger.info("admin.escalation_replied", extra={"extra_data": {"escalation_id": escalation_id}})
    return {"success": True, "escalation": _escalation_to_dict(escalation)}


@app.get("/admin/session/{session_id}")
def admin_get_session_history(session_id: str, authorization: str | None = Header(default=None)):
    """Get session conversation history."""
    _require_admin(authorization)
    from backend.storage import get_conversation_history
    
    history = get_conversation_history(session_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.info("admin.session_accessed", extra={"extra_data": {"session_id": session_id, "message_count": len(history)}})
    
    return {"session_id": session_id, "history": history}


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
def groq_health_check():
    return config.is_online

def health_llm():
    """Checks if the LLM provider is reachable."""
    is_online = groq_health_check()
    provider = config.get_active_provider() 
    
    if is_online:
        return {"provider": provider, "status": "ok"}
    return {
        "provider": provider, 
        "status": "error", 
        "detail": "No internet connection for Groq and/or Ollama not responding"
    }


# ---------------------------
# TEST LLM CONNECTION
# ---------------------------
@app.get("/test_llm")
def test_llm():
    """Test endpoint to verify LLM connectivity."""
    try:
        # Route through the actual component instead of an undefined function
        # Ensure intent_pipeline is initialized earlier in main.py
        result = intent_engine.classify("hello", {}) 
        return {
            "success": True, 
            "provider": config.get_active_provider(), 
            "result": result
        }
    except Exception as e:
        logger.error(f"LLM test failed: {str(e)}")
        return {
            "success": False, 
            "error": str(e), 
            "provider": config.get_active_provider()
        }


# ============================================================
# WhatsApp Business API Webhook
# ============================================================
# These two endpoints are the only additions needed to go from
# web demo → WhatsApp deployment.
#
# Setup steps (when ready):
#   1. Create a Meta App at https://developers.facebook.com
#   2. Add "WhatsApp" product → configure webhook URL:
#      https://<your-domain>/whatsapp/webhook
#   3. Set WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN,
#      WHATSAPP_PHONE_NUMBER_ID in your .env
#   4. Uncomment the send_whatsapp_reply() call below
# ============================================================

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


@app.get("/whatsapp/webhook")
def whatsapp_verify(
    hub_mode: str = "",
    hub_verify_token: str = "",
    hub_challenge: str = "",
):
    """Meta webhook verification handshake.

    Meta sends a GET request with these query params when you register
    the webhook URL in the developer portal.
    """
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("whatsapp.webhook_verified")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/whatsapp/webhook")
async def whatsapp_incoming(payload: dict, request: Request):
    """Receive inbound WhatsApp messages and route them through the chatbot.

    The message body is identical to the web /chat endpoint — the same
    orchestrator, agents, and tools handle both channels.
    """
    import requests as _requests

    try:
        # Parse the WhatsApp message payload
        entry = (payload.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            # Delivery receipts and status updates — acknowledge and ignore
            return {"status": "ok"}

        msg = messages[0]
        from_number = msg.get("from", "")
        msg_type = msg.get("type", "")

        # Only handle text messages for now
        if msg_type != "text":
            logger.info(f"whatsapp.unsupported_type type={msg_type} from={from_number}")
            return {"status": "ok"}

        text = (msg.get("text") or {}).get("body", "").strip()
        if not text:
            return {"status": "ok"}

        # Rate limit by WhatsApp number
        rate_limiter.check(f"wa:{from_number}")

        # Sanitize and enforce length
        from backend.security import sanitize_input as secure_sanitize, SecurityViolation
        try:
            text = secure_sanitize(text)[:1000]
        except SecurityViolation as exc:
            logger.warning(f"WhatsApp webhook security violation blocked: {exc}")
            if WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
                _send_whatsapp_reply(from_number, str(exc))
            return {"status": "ok"}

        # Process through the same orchestrator as the web UI
        result = await orchestrator.process(message=text, user_id=f"wa:{from_number}")
        reply_text = result.get("response", "I'm sorry, I couldn't process that.")

        # Log conversation turn
        try:
            storage_log_conversation_turn(
                user_id=f"wa:{from_number}",
                role="user",
                text_redacted=context_redact_pii(text),
                text_original=text,
                flow="whatsapp",
                intent=str(result.get("intent") or ""),
                confidence=float(result.get("confidence") or 0.0),
            )
            storage_log_conversation_turn(
                user_id=f"wa:{from_number}",
                role="bot",
                text_redacted=context_redact_pii(reply_text),
                text_original=reply_text,
                flow="whatsapp",
                intent=str(result.get("intent") or ""),
                confidence=float(result.get("confidence") or 0.0),
            )
        except Exception as log_err:
            logger.warning(f"whatsapp.log_failed err={log_err}")

        # Send reply back via WhatsApp Cloud API
        if WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
            _send_whatsapp_reply(from_number, reply_text)
        else:
            logger.warning(
                "whatsapp.reply_skipped — WHATSAPP_ACCESS_TOKEN or "
                "WHATSAPP_PHONE_NUMBER_ID not configured"
            )

        return {"status": "ok"}

    except HTTPException:
        raise
    except _requests.Timeout:
        logger.warning("whatsapp.llm_timeout")
        return {"status": "ok"}  # Always return 200 to Meta to avoid retries
    except Exception as e:
        logger.error(f"whatsapp.webhook_error err={e}", exc_info=True)
        return {"status": "ok"}  # Always return 200 to Meta


def _send_whatsapp_reply(to: str, text: str) -> None:
    """Send a text reply via the WhatsApp Cloud API."""
    import requests as _requests

    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        resp = _requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"whatsapp.send_failed status={resp.status_code} body={resp.text[:200]}")
    except Exception as e:
        logger.error(f"whatsapp.send_error err={e}")

# ---------------------------
# Admin: Intent Cache Hot-Reloading
# ---------------------------
@app.post("/admin/intent_cache/invalidate")
def admin_invalidate_intent_cache(authorization: str | None = Header(default=None)):
    """Manually invalidates the in-memory intent candidate cache and reloads from DB."""
    admin_id = _require_admin(authorization)
    intent_engine.reload_cache()
    logger.info(f"Intent cache manually invalidated by admin {admin_id}")
    return {"success": True, "message": "Intent cache reloaded successfully"}


async def poll_intent_db_task():
    """Background task to poll the database for active intent candidate updates every 60 seconds."""
    import sqlite3
    import asyncio
    from backend.storage import DB_PATH, INTENT_CANDIDATES_TABLE
    
    last_count = -1
    try:
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {INTENT_CANDIDATES_TABLE} WHERE active = 1").fetchone()
            if row:
                last_count = row[0]
    except Exception as e:
        logger.warning(f"Error getting initial active intent count in polling task: {e}")
        
    while True:
        try:
            await asyncio.sleep(60)
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(f"SELECT COUNT(*) FROM {INTENT_CANDIDATES_TABLE} WHERE active = 1").fetchone()
                if row:
                    current_count = row[0]
                    if current_count != last_count:
                        logger.info(f"Background intent polling: active candidates count changed from {last_count} to {current_count}. Reloading cache.")
                        intent_engine.reload_cache()
                        last_count = current_count
        except asyncio.CancelledError:
            logger.info("Background intent polling task cancelled")
            break
        except Exception as e:
            logger.warning(f"Error in background intent polling task: {e}")


@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(poll_intent_db_task())


# ---------------------------
# FRONTEND SERVING (CATCH-ALL)
# ---------------------------
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend SPA - this catch-all must be last"""
    # Only block API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Skip asset requests - let static mount handle them or return 404
    # (Checking prefixes and standard file extensions to prevent browser module MIME type errors)
    is_asset = (
        full_path.startswith("assets/") or 
        full_path.startswith("static/") or 
        any(full_path.endswith(ext) for ext in [".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".json", ".txt", ".woff", ".woff2", ".ttf", ".map"])
    )
    if is_asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Admin SPA
    # Check if it's an admin route
    if full_path == "admin" or full_path == "admin/" or full_path.startswith("admin/"):
        admin_index = PROJECT_ROOT / "frontend" / "admin" / "dist" / "index.html"
        if admin_index.exists():
            return FileResponse(str(admin_index))
        # Fallback to static/admin.html for isolated dev fallback if React bundle not built
        admin_legacy = PROJECT_ROOT / "static" / "admin.html"
        if admin_legacy.exists():
            return FileResponse(str(admin_legacy))
    
    # Feedback page
    if full_path == "feedback" or full_path == "feedback/":
        feedback_path = PROJECT_ROOT / "static" / "feedback.html"
        if feedback_path.exists():
            return FileResponse(str(feedback_path))

    # Default to customer chat frontend
    frontend_path = PROJECT_ROOT / "frontend" / "aqua-chat-modern-main" / "dist"
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    raise HTTPException(status_code=404, detail="Frontend not built")
