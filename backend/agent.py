"""backend/agent.py

Groq-only, LLM-first agent router.

Deterministic templates remain only for:
- complaint ticket creation
- bill lookup
- escalation forms

Everything else is answered naturally via Groq with water-utility guardrails.
"""

from __future__ import annotations

import random
import re
import string
from typing import Any, Dict, Optional

from .intents import ALLOWED_INTENTS_SET
from .logger import logger
from .storage import (
    append_escalation_message,
    create_escalation,
    find_open_escalation_for_user,
    set_complaint_status,
)
from .tools import (
    escalate_to_human,
    create_connection_request,
    get_bill,
    get_complaint_status,
    get_office_info,
    get_payment_methods,
    log_complaint,
)
from .validators import extract_account_number, extract_ticket_id, is_valid_name, is_valid_phone, is_valid_email
from .llm.groq_client import generate_response, detect_human_request, classify_billing_subintent


def _ensure_escalated_footer(text: str) -> str:
    footer = "A customer service agent will assist you shortly."
    if footer.lower() in text.lower():
        return text
    return f"{text.rstrip()}\n\n{footer}"


def _generate_ticket_id() -> str:
    chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"WC-{chars}"


def _log_escalation(*, reason: str, intent: str, confidence: float) -> None:
    logger.info(
        f"ESCALATION_REQUEST reason={reason} intent={intent} confidence={confidence:.2f}"
    )


def _normalize_escalation_reason(reason: str) -> str:
    r = (reason or "").strip().lower()
    if r in {"low_confidence", "payment_issue", "human_request", "complex_case"}:
        return r
    if r.startswith("low"):
        return "low_confidence"
    if "payment" in r:
        return "payment_issue"
    if "human" in r or "agent" in r or "person" in r:
        return "human_request"
    return "complex_case"


def _ensure_escalation_record(
    *,
    session: dict,
    ticket_id: str,
    reason: str,
    initial_messages: list[dict[str, Any]],
) -> str:
    """Create an escalation record once and cache escalation_id in session."""

    if session.get("escalation_id"):
        return str(session["escalation_id"])

    user_id = str(session.get("user_id") or "unknown")
    esc_id = create_escalation(
        ticket_id=ticket_id,
        user_id=user_id,
        reason=_normalize_escalation_reason(reason),
        messages=initial_messages,
    )
    session["escalation_id"] = esc_id
    session["escalation_ticket_id"] = ticket_id
    return esc_id


def _decline_out_of_scope(message: str, session: dict) -> str:
    return generate_response(
        message,
        session,
        intent="out_of_scope",
        additional_instructions=(
            "Politely say you can only assist with water utility services such as billing, faults, meter issues, "
            "complaints, payments, and connections. Do not escalate. End by asking how you can help with their water service."
        ),
        max_tokens=120,
    )


def _extract_phone_number(message: str) -> Optional[str]:
    m = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", message)
    if not m:
        return None
    phone = re.sub(r"[\s\-]", "", m.group(1))
    if len(re.sub(r"\D", "", phone)) < 9:
        return None
    return phone


def _extract_amount(message: str) -> Optional[str]:
    m = re.search(
        r"\b(?:amount\s*[:=]\s*)?(?:k\s*)?(\d+(?:\.\d{1,2})?)\b",
        message,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


def _extract_payment_method(message: str) -> Optional[str]:
    m = re.search(r"\b(mtn|airtel|zamtel|bank)\b", message, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m2 = re.search(
        r"payment\s*method\s*[:=]\s*([a-zA-Z0-9\- ]{2,30})",
        message,
        flags=re.IGNORECASE,
    )
    return m2.group(1).strip() if m2 else None


def _extract_payment_date(message: str) -> Optional[str]:
    m = re.search(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|yesterday|today|last\s+week|last\s+month)\b",
        message,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


def _payment_not_reflected_prompt(missing: Optional[list[str]] = None) -> str:
    if not missing:
        return (
            "I can help check your payment.\n\n"
            "Please provide:\n\n"
            "• Account Number\n"
            "• Payment Method (MTN/Airtel/Bank)\n"
            "• Approximate Payment Date\n"
            "• Amount Paid"
        )

    missing_lines = "\n".join(f"• {m}" for m in missing)
    return (
        "I can help check your payment.\n\n"
        "Please provide:\n\n"
        f"{missing_lines}"
    )


def _fill_complaint_fields_from_message(message: str, session: dict) -> dict:
    """Extract complaint fields from free-form message text (not used for routing)."""

    msg = message.strip()
    lowered = message.lower().strip()

    # Ignore simple greetings so they don't become a name
    greetings = {"hi", "hello", "hey", "hiya", "hie", "yo", "good morning", "good afternoon", "good evening"}
    if lowered in greetings or re.fullmatch(r"hi+|hey+|hello+", lowered):
        return session

    # Key:value patterns
    for key in ["name", "area", "issue"]:
        m = re.search(rf"{key}\s*[:\-]\s*(.+)", message, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val:
                session[key] = val

    # Comma-separated fragments with keys
    parts = [p.strip() for p in message.split(",") if p.strip()]
    for p in parts:
        for key in ["name", "area", "issue"]:
            if p.lower().startswith(key):
                parts_val = p.split(":", 1)
                if len(parts_val) == 2:
                    session[key] = parts_val[1].strip()

    # Short replies fill next missing field
    required = ["name", "area", "issue"]
    missing = [f for f in required if f not in session]
    if missing and msg and len(msg.split()) <= 6:
        session[missing[0]] = msg

    return session


def run_agent(message: str, intent_data: dict, session: dict) -> str:
    routed_intent = str(intent_data.get("intent", "out_of_scope"))
    confidence = float(intent_data.get("confidence", 0.0))
    auto_escalated = bool(intent_data.get("auto_escalated", False))
    original_intent = str(intent_data.get("original_intent") or routed_intent)
    entities = intent_data.get("entities", {}) or {}

    if routed_intent not in ALLOWED_INTENTS_SET:
        logger.warning(f"Invalid routed intent from classifier: {routed_intent!r}. Forcing out_of_scope")
        routed_intent = "out_of_scope"

    # Required log format for verification
    logger.info(
        f"Intent={original_intent} confidence={confidence:.2f} routed_intent={routed_intent} auto_escalated={auto_escalated}"
    )

    flow = session.get("flow")

    def _escalation_include_account_number() -> bool:
        """Only request account number when it is relevant (billing/payment flows)."""

        # If we already have an account number, don't ask again.
        if session.get("account_number") or extract_account_number(message):
            return False

        # Billing intent or payment issue needs account number.
        if original_intent == "billing_inquiry":
            return True
        if session.get("billing_case") in {"payment_not_reflected", "wrong_bill", "bill_check"}:
            return True
        if session.get("flow") == "payment_reflection":
            return True

        return False

    # =====================================================
    # Payment not reflected flow (collect details, then record + escalate)
    # =====================================================
    if flow == "payment_reflection":
        # Keep a transcript for the admin escalation chat.
        payment_msgs: list[dict[str, Any]] = session.setdefault("payment_reflection_messages", [])
        payment_msgs.append({"sender": "user", "text": message})

        details: Dict[str, Any] = session.setdefault("payment_details", {})

        acct = extract_account_number(message)
        if acct:
            details["account_number"] = acct

        method = _extract_payment_method(message)
        if method:
            details["payment_method"] = method

        pdate = _extract_payment_date(message)
        if pdate:
            details["payment_date"] = pdate

        amt = _extract_amount(message)
        if amt:
            details["amount_paid"] = amt

        missing: list[str] = []
        if not details.get("account_number"):
            missing.append("Account Number")
        if not details.get("payment_method"):
            missing.append("Payment Method (MTN/Airtel/Bank)")
        if not details.get("payment_date"):
            missing.append("Approximate Payment Date")
        if not details.get("amount_paid"):
            missing.append("Amount Paid")

        if missing:
            return _payment_not_reflected_prompt(missing)

        ticket = session.get("payment_ticket") or _generate_ticket_id()
        session["payment_ticket"] = ticket
        session.pop("flow", None)
        session["escalated"] = True

        final_text = (
            "Thank you. Your payment issue has been recorded.\n\n"
            "A customer service agent will verify the payment.\n\n"
            f"Ticket: {ticket}"
        )
        payment_msgs.append({"sender": "bot", "text": final_text})

        # Create an escalation record (WAITING) with full transcript.
        _ensure_escalation_record(
            session=session,
            ticket_id=ticket,
            reason="payment_issue",
            initial_messages=payment_msgs,
        )

        # Prefer logging the confidence from the first payment-issue turn.
        log_conf = float(session.get("payment_issue_confidence", confidence))
        _log_escalation(reason="payment_issue", intent="billing_inquiry", confidence=log_conf)

        return _ensure_escalated_footer(final_text)

    # =====================================================
    # Escalation form flow
    # =====================================================
    if flow == "escalation_form":
        # Store the user's message to the escalation transcript, if linked.
        if session.get("escalation_id"):
            append_escalation_message(
                escalation_id=str(session["escalation_id"]),
                sender="user",
                text=message,
            )

        if "name" not in session:
            maybe = message.strip()
            if 2 <= len(maybe.split()) <= 4 and not re.search(r"\d", maybe):
                session["name"] = maybe

        if "phone_number" not in session:
            p = _extract_phone_number(message)
            if p:
                session["phone_number"] = p

        if "account_number" not in session:
            acct = extract_account_number(message)
            if acct:
                session["account_number"] = acct

        required_fields = ["name", "phone_number"]
        if session.get("escalation_needs_account") is True:
            required_fields.append("account_number")

        missing_fields = [f for f in required_fields if f not in session]
        if missing_fields:
            return escalate_to_human(include_account_number=session.get("escalation_needs_account") is True)

        session.pop("flow", None)
        session["escalated"] = True

        ack = "Thank you. Your details have been received."
        if session.get("escalation_id"):
            append_escalation_message(
                escalation_id=str(session["escalation_id"]),
                sender="bot",
                text=ack,
            )
        return _ensure_escalated_footer(ack)

    # =====================================================
    # Escalated chat mode (MANDATORY)
    # =====================================================
    # While escalated, do NOT call Groq.
    # Store the user's message in the escalation transcript and confirm delivery.
    if session.get("escalated"):
        user_id = str(session.get("user_id") or "unknown")
        open_esc = find_open_escalation_for_user(user_id)

        if not open_esc:
            # Escalation closed -> resume normal bot mode.
            session.pop("escalated", None)
            session.pop("escalation_id", None)
            session.pop("escalation_ticket_id", None)
        else:
            session["escalation_id"] = open_esc.escalation_id
            session["escalation_ticket_id"] = open_esc.ticket_id
            append_escalation_message(
                escalation_id=open_esc.escalation_id,
                sender="user",
                text=message,
            )
            return "Your message has been sent to the agent."

    # =====================================================
    # Out of scope (must not escalate)
    # =====================================================
    if routed_intent == "out_of_scope":
        session.clear()
        return _decline_out_of_scope(message, session)

    # =====================================================
    # Human request detection (Groq-only; confidence irrelevant)
    # =====================================================
    if routed_intent != "escalation":
        human = detect_human_request(message, session)
        if human.get("request_human"):
            routed_intent = "escalation"
            intent_data["escalation_reason"] = "human_request"

    # =====================================================
    # General chat (greetings, who-are-you, thanks)
    # =====================================================
    if routed_intent == "general_chat":
        session.clear()
        return generate_response(message, session, intent=routed_intent, max_tokens=140)

    # =====================================================
    # Complaints / faults (template flow)
    # =====================================================
    if routed_intent in {"report_fault", "leak_report"}:
        session.setdefault("flow", "complaint")
        required = ["name", "area", "issue"]

        for field in ["name", "area"]:
            if entities.get(field) and field not in session:
                session[field] = entities[field]

        if "issue" not in session:
            session["issue"] = "Pipe leak" if routed_intent == "leak_report" else "Water fault"

        _fill_complaint_fields_from_message(message, session)

        missing = [f for f in required if f not in session]
        if missing:
            return (
                "I can help report this issue. Please provide:\n" + "\n".join(f"- {f}" for f in missing)
            )

        result = log_complaint(session)
        session.clear()
        return result

    # =====================================================
    # Billing intent with subcases (Groq-only)
    # =====================================================
    if routed_intent == "billing_inquiry":
        session.setdefault("flow", "billing")
        if "billing_case" not in session:
            session["billing_case"] = classify_billing_subintent(message, session).get("case", "bill_check")

        billing_case = session.get("billing_case", "bill_check")

        # Case A: payment not reflected
        if billing_case == "payment_not_reflected":
            session["flow"] = "payment_reflection"
            session.setdefault("payment_details", {})
            session["payment_issue_confidence"] = confidence
            prompt = _payment_not_reflected_prompt()
            session["payment_reflection_messages"] = [
                {"sender": "user", "text": message},
                {"sender": "bot", "text": prompt},
            ]
            return prompt

        # Case B: wrong bill
        if billing_case == "wrong_bill":
            acct = extract_account_number(message)
            if acct:
                session["account_number"] = acct
            if "bill_issue" not in session and not acct:
                session["bill_issue"] = message.strip()

            if "account_number" not in session:
                return (
                    "I understand you believe your bill is incorrect.\n\n"
                    "Please provide:\n\n"
                    "• Account Number\n"
                    "• What seems incorrect (high bill, wrong reading, etc)\n\n"
                    "We will investigate this."
                )

            if "bill_issue" not in session:
                return "Please describe what seems incorrect about the bill (e.g., high bill, wrong reading)."

            session.clear()
            return (
                "Thank you. We have recorded your report of an incorrect bill and will investigate this."
            )

        # Case C: simple bill check
        acct = extract_account_number(message) or session.get("account_number")
        if acct:
            session["account_number"] = acct
        if not acct:
            return "Please provide your account number (e.g., 123456 or account_number: 123456)."

        result = get_bill(acct)
        session.clear()
        return result

    # =====================================================
    # New connection request (deterministic flow)
    # =====================================================
    if routed_intent == "new_connection":
        session.setdefault("flow", "new_connection")
        step = session.get("step", 0)
        required = ["name", "address", "phone", "email"]
        fields = {}

        # Extract from entities/message
        if "name" in entities and is_valid_name(entities["name"]):
            fields["name"] = entities["name"]
        if "address" in entities:
            fields["address"] = entities["address"].strip()
        if "phone" in entities and is_valid_phone(entities["phone"]):
            fields["phone"] = entities["phone"]
        if "email" in entities and is_valid_email(entities["email"]):
            fields["email"] = entities["email"].strip()

        # Update session
        for k, v in fields.items():
            session[k] = v

        collected = sum(1 for f in required if f in session)
        current_step = min(step, len(required) - 1)

        if collected >= len(required):
            # Complete
            result = create_connection_request(session)
            session.clear()
            return result

        # Prompt next step
        prompt_fields = [
            "your full name",
            "your full address",
            "your phone number (e.g. +26097...)",
            "your email address"
        ]
        next_prompt = prompt_fields[current_step]
        return f"I can help you apply for a new water connection. Please provide {next_prompt}."

    # =====================================================
    # Payment methods (only when explicitly asked)
    # =====================================================
    if routed_intent == "payment_info":
        session.clear()
        return get_payment_methods()

    # =====================================================
    # Complaint follow-up (deterministic)
    # =====================================================
    if routed_intent == "complaint_followup":
        ticket = extract_ticket_id(message) or session.get("ticket_id")
        if ticket:
            session["ticket_id"] = ticket
        if not ticket:
            return "Please provide your reference number (e.g., WC-A1B2C3)."

        result = get_complaint_status(ticket)
        session.clear()
        return result

    # =====================================================
    # Office info: ground the response on known facts
    # =====================================================
    if routed_intent == "office_info":
        office = get_office_info()
        session.clear()
        return generate_response(
            message,
            session,
            intent=routed_intent,
            facts=office,
            additional_instructions="Use the FACTS content verbatim when providing addresses, hours, or contacts.",
            max_tokens=180,
        )

    # =====================================================
    # Escalation
    # =====================================================
    if routed_intent == "escalation":
        ticket_id = session.get("ticket_id")
        if isinstance(ticket_id, str) and ticket_id.strip():
            set_complaint_status(ticket_id.strip(), "escalated")

        # Ensure we have a ticket id for the escalation record.
        if not isinstance(ticket_id, str) or not ticket_id.strip():
            ticket_id = _generate_ticket_id()
            session["ticket_id"] = ticket_id

        reason = str(intent_data.get("escalation_reason") or ("low_confidence" if auto_escalated else "human_request"))
        if reason not in {"low_confidence", "payment_issue", "human_request", "complex_case"}:
            reason = "complex_case"

        _log_escalation(reason=reason, intent=original_intent, confidence=confidence)

        # Only request account number when relevant.
        needs_account = _escalation_include_account_number()
        session["escalation_needs_account"] = needs_account
        form_prompt = escalate_to_human(include_account_number=needs_account)

        _ensure_escalation_record(
            session=session,
            ticket_id=str(ticket_id),
            reason=reason,
            initial_messages=[
                {"sender": "user", "text": message},
                {"sender": "bot", "text": form_prompt},
            ],
        )

        session["escalated"] = True
        session["flow"] = "escalation_form"
        return form_prompt

    # =====================================================
    # Default: Groq natural response inside guardrails
    # =====================================================
    session.clear()
    return generate_response(message, session, intent=routed_intent, max_tokens=180)
