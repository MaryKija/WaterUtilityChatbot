"""backend/context_engine.py

Central state manager for conversation flow control.

Manages strict context structure with fields:
- session_id: Unique session identifier
- active_agent: Currently assigned agent
- intent: Current intent classification
- step: Current workflow step
- entities: Extracted entities
- history: Conversation history

Handles:
- Context loading/saving
- Flow decision logic (classify, continue, escalate)
- Progressive context updates
- Workflow state prevention of reclassification
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional, Tuple

import requests

from .config import config
from .logger import logger
from .validators import is_valid_account, is_valid_name, is_valid_phone, normalize_phone


Role = Literal["user", "bot"]


FLOW_TIMEOUT_HOURS = int(os.getenv("FLOW_TIMEOUT_HOURS", "24"))
CONTEXT_HISTORY_HEAD_N = int(os.getenv("CONTEXT_HISTORY_HEAD_N", "12"))
SUMMARY_TRIGGER_TURNS = int(os.getenv("SUMMARY_TRIGGER_TURNS", "24"))


def context_redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text for logging.
    
    Replaces sensitive information with placeholders:
    - Phone numbers: [PHONE]
    - Account numbers: [ACCOUNT]
    - Names: [NAME]
    - Email addresses: [EMAIL]
    """
    if not text:
        return text
    
    # Phone numbers (various formats)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}', '[PHONE]', text)
    
    # Account numbers (sequences of digits, 6-12 chars)
    text = re.sub(r'\b\d{6,12}\b', '[ACCOUNT]', text)
    
    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Names (capitalized words that look like names)
    text = re.sub(r'\b[A-Z][a-z]+\b', '[NAME]', text)
    
    return text


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
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
    """Redact PII for storage in analytics/training tables."""
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


class ContextManager:
    """Central state manager for conversation context."""

    def __init__(self):
        self.context_schema = {
            "session_id": None,  # str
            "active_agent": None,  # str
            "intent": None,  # str
            "step": None,  # str or int
            "entities": {},  # dict
            "history": [],  # list of dicts
            "last_updated": None,  # str (ISO)
            "flow_started": False,  # bool - prevents reclassification
            "escalated": False,  # bool
            "confidence": None,  # float
            "intent_source": None,  # str - 'rule', 'lightweight', 'llm', 'arbitration'
        }

    def initialize_context(self, user_id: str) -> dict:
        """Initialize default context for a user."""
        uid = (user_id or "").strip() or "unknown"
        context = self.context_schema.copy()
        context.update({
            "session_id": uid,
            "user_id": uid,
            "last_updated": _utc_now_iso(),
        })
        return context

    def load_context(self, user_id: str) -> dict:
        """Load persisted context from database."""
        from .storage import get_session_context
        ctx = get_session_context(user_id)
        if not isinstance(ctx, dict):
            return self.initialize_context(user_id)

        # Ensure all required fields exist
        context = self.context_schema.copy()
        context.update(ctx)
        return context

    def save_context(self, user_id: str, context: dict) -> None:
        """Persist context to database."""
        from .storage import upsert_session_context
        context["last_updated"] = _utc_now_iso()
        upsert_session_context(user_id, context)

    def should_classify_intent(self, context: dict) -> bool:
        """Decide whether to run intent classification."""
        # Don't classify if workflow already started
        if context.get("flow_started", False):
            return False

        # Don't classify if escalated
        if context.get("escalated", False):
            return False

        # Don't classify if active agent is set (ongoing workflow)
        if context.get("active_agent"):
            return False

        return True

    def should_continue_workflow(self, context: dict) -> bool:
        """Check if we should continue existing workflow."""
        return context.get("flow_started", False) and not context.get("escalated", False)

    def should_escalate(self, context: dict, confidence: float, failure_count: int) -> bool:
        """Decide whether to escalate based on confidence and failures."""
        # Low confidence threshold
        if confidence < 0.6:
            return True

        # Multiple failures
        if failure_count >= 3:
            return True

        return False

    def update_context_with_intent(self, context: dict, intent_result: dict) -> dict:
        """Update context with intent classification result."""
        context["intent"] = intent_result.get("intent")
        context["confidence"] = intent_result.get("confidence", 0.0)
        context["intent_source"] = intent_result.get("source", "unknown")

        # Merge entities
        entities = context.get("entities", {})
        entities.update(intent_result.get("entities", {}))
        context["entities"] = entities

        # Set active agent based on intent
        context["active_agent"] = self._map_intent_to_agent(context["intent"])

        # Mark flow as started once we have an intent and agent
        if context["intent"] and context["active_agent"]:
            context["flow_started"] = True

        return context

    def update_context_with_step(self, context: dict, step: str, entities: dict = None) -> dict:
        """Update context with workflow step progress."""
        context["step"] = step

        if entities:
            current_entities = context.get("entities", {})
            current_entities.update(entities)
            context["entities"] = current_entities

        return context

    def update_context_with_history(self, context: dict, role: Role, message: str) -> dict:
        """Add message to conversation history."""
        history = context.get("history", [])
        history.append({
            "role": role,
            "text": message,
            "timestamp": _utc_now_iso()
        })

        # Keep only recent history
        if len(history) > CONTEXT_HISTORY_HEAD_N:
            history = history[-CONTEXT_HISTORY_HEAD_N:]

        context["history"] = history
        return context

    def escalate_context(self, context: dict, reason: str) -> dict:
        """Mark context as escalated."""
        context["escalated"] = True
        context["escalation_reason"] = reason
        context["active_agent"] = "human_agent"
        return context

    def reset_context(self, context: dict) -> dict:
        """Reset context for new conversation."""
        context.update({
            "active_agent": None,
            "intent": None,
            "step": None,
            "flow_started": False,
            "escalated": False,
            "confidence": None,
            "intent_source": None,
        })
        return context

    def _map_intent_to_agent(self, intent: str) -> str:
        """Map intent to appropriate agent."""
        intent_agent_map = {
            "report_fault": "complaint_agent",
            "leak_report": "complaint_agent",
            "billing_inquiry": "billing_agent",
            "payment_info": "billing_agent",
            "new_connection": "connection_agent",
            "complaint_followup": "complaint_agent",
            "meter_problem": "complaint_agent",
            "office_info": "info_agent",
            "general_chat": "general_agent",
            "escalation": "human_agent",
            "out_of_scope": "general_agent",
        }
        return intent_agent_map.get(intent, "general_agent")

    def expire_flow_if_needed(self, context: dict) -> dict:
        """Expire active flow if last_updated is beyond timeout."""
        last_updated = _parse_ts(context.get("last_updated"))
        if not context.get("flow_started") or not last_updated:
            return context

        timeout = timedelta(hours=max(1, FLOW_TIMEOUT_HOURS))
        if datetime.now(timezone.utc) - last_updated <= timeout:
            return context

        # Expire flow
        logger.info("ContextManager: flow expired", extra={
            "session_id": context.get("session_id"),
            "timeout_hours": FLOW_TIMEOUT_HOURS,
        })
        return self.reset_context(context)


# Global context manager instance
context_manager = ContextManager()


# Legacy compatibility functions
def initialize_context(user_id: str) -> dict:
    return context_manager.initialize_context(user_id)


def update_context(user_id: str, role: Role, message: str, session: dict) -> dict:
    """Legacy update_context - now delegates to ContextManager."""
    context = _safe_dict(session)

    # Handle reply override for pending questions
    action_hint = {}

    # Resolve pending question on user turn
    if role == "user" and context.get("pending_question"):
        context, resolved = resolve_pending_question(context, message)
        if resolved:
            action_hint["pending_resolved"] = True
        else:
            attempts = _safe_dict(context.get("pending_attempts")).get(str(context.get("pending_question")), 0)
            if attempts <= 3:
                prompts = {
                    "account_number": "Please reply with your account number (6+ digits).",
                    "phone": "Please reply with your phone number (e.g., +26097XXXXXXX).",
                    "name": "Please reply with your full name.",
                }
                action_hint["reply_override"] = prompts.get(str(context.get("pending_question")), "Please provide the requested detail.")
                action_hint["needs_clarification"] = True
            else:
                action_hint["reply_override"] = (
                    "I'm having trouble capturing that detail. "
                    "I can connect you to a customer service agent to help."
                )
                action_hint["escalate_suggested"] = True

    # Update history
    context = context_manager.update_context_with_history(context, role, message)

    # Summarize if needed
    if role == "user":
        try:
            context = summarize_if_needed(user_id, context)
        except Exception:
            pass

    # Expire flow if needed
    context = context_manager.expire_flow_if_needed(context)

    context["action_hint"] = action_hint
    return context


def resolve_pending_question(session: dict, message: str) -> Tuple[dict, bool]:
    """Resolve pending_question using message."""
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


def summarize_if_needed(user_id: str, session: dict) -> dict:
    """Summarize conversation when long."""
    sess = _safe_dict(session)
    head = _safe_list(sess.get("history"))
    if len(head) < SUMMARY_TRIGGER_TURNS:
        return sess

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
    sess["history"] = head[-CONTEXT_HISTORY_HEAD_N:]
    return sess


def extract_entities(message: str) -> dict:
    """Extract entities from message (regex first, with validation)."""
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
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{2,4}|today|yesterday|last\s+week|last\s+month)\b",
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
    """Groq fallback entity extraction."""
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


def clear_workflow_for_ticket(ticket_id: str) -> int:
    """Clear workflow for sessions referencing this ticket."""
    tid = (ticket_id or "").upper().strip()
    if not tid:
        return 0

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
            ctx = context_manager.reset_context(ctx)
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
            conn.close()
        except Exception:
            pass

    logger.info(
        "context_engine.clear_workflow_for_ticket",
        extra={"extra_data": {"ticket_id": tid, "affected": affected}},
    )
    return affected