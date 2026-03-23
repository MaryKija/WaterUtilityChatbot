"""backend/llm/groq_client.py

Groq-only intent classification client.

This module is the *single* interface used by the application to classify user intent.
It enforces:
- Groq as the only provider
- Water-utility-only scope guardrail
- JSON-only output
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from ..config import config
from ..intents import ALLOWED_INTENTS_SET
from ..logger import logger


WATER_UTILITY_GUARDRAIL_SYSTEM_PROMPT = """You are a Water Utility Customer Support AI.

You ONLY handle:
- Water supply problems
- Billing
- Connections
- Complaints
- Leakages
- Meter issues
- Payments
- Account support

If the user asks anything unrelated
(sports, politics, jokes, coding, schoolwork),
return:

{
  "intent": "out_of_scope",
  "confidence": 1.0,
  "entities": {}
}

Return ONLY a JSON object and NOTHING else.
"""


INTENT_OUTPUT_SCHEMA_INSTRUCTIONS = """You are an intent classifier.

If the user's message is related to water utility customer support, choose the single best intent from the allowed list.
Use out_of_scope ONLY when the message is unrelated to water utility services.

 ALLOWED INTENTS (choose ONE):
 - general_chat: greetings, thanks, identity questions, and short clarifications (within water-utility support)
 - report_fault: reporting a water problem (no water, low pressure, outage, dirty water)
 - leak_report: reporting leaks/burst pipes
 - billing_inquiry: balance, bill amount, charges, due date
 - payment_info: payment methods, how/where to pay
 - new_connection: applying for a new connection / connection guidance
 - complaint_followup: track a complaint / check reference/ticket status
 - meter_problem: meter not working, meter fault, submit reading issues
 - office_info: office location, hours, contacts
 - escalation: asking to speak to a human/agent
 - out_of_scope: anything else

Return ONLY JSON in this exact shape:
{{
  "intent": "billing_inquiry",
  "confidence": 0.92,
  "entities": {{
    "account_number": "123456",
    "ticket_id": "WC-A1B2C3",
    "name": "",
    "area": ""
  }}
}}

Rules:
- intent MUST be one of: {allowed_intents}
- confidence MUST be a number from 0.0 to 1.0
- entities MUST be an object (can be empty)
- Extract account_number if user provides a 6+ digit number
- Extract ticket_id if it matches WC-XXXXXX style
- If the message is vague/ambiguous (e.g., "help", "something is not right"), set confidence <= 0.59
- If the message mixes multiple different problems in one message, set confidence <= 0.59
- If the user asks to speak to a human agent/customer service, choose intent "escalation".
- Only choose "billing_inquiry" if the user is actually discussing bills/payments/accounts.
- Output JSON ONLY (no markdown, no commentary)
"""


@dataclass(frozen=True)
class GroqHealth:
    provider: str
    status: str
    detail: Optional[str] = None


def _clamp_confidence(value: Any) -> float:
    try:
        c = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, c))


def _normalize_entities(entities: Any) -> Dict[str, str]:
    if not isinstance(entities, dict):
        entities = {}

    def _s(key: str) -> str:
        v = entities.get(key, "")
        if v is None:
            return ""
        return str(v)

    return {
        "account_number": _s("account_number"),
        "ticket_id": _s("ticket_id"),
        "name": _s("name"),
        "area": _s("area"),
    }


def _normalize_result(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}

    intent = raw.get("intent")
    if intent not in ALLOWED_INTENTS_SET:
        intent = "out_of_scope"

    confidence = _clamp_confidence(raw.get("confidence", 0.0))
    entities = _normalize_entities(raw.get("entities"))

    return {"intent": intent, "confidence": confidence, "entities": entities}


def _post_chat_completions(*, messages: list[dict[str, str]], max_tokens: int = 250) -> str:
    """Call Groq's OpenAI-compatible chat completions endpoint and return content."""

    payload: Dict[str, Any] = {
        "model": config.groq_model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        # Ask for strict JSON. Groq supports OpenAI-compatible response_format.
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

    if resp.status_code != 200:
        raise RuntimeError(f"Groq HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError(f"Unexpected Groq response: {str(data)[:300]}")


def classify_intent(message: str, session: dict) -> Dict[str, Any]:
    """Classify intent using Groq only.

    Args:
        message: User message
        session: Per-user session dict (used as context only; no keyword/regex fallback)

    Returns:
        Normalized dict: {intent, confidence, entities}
    """

    flow = session.get("flow")
    session_hint = ""
    if flow in {"complaint", "billing", "followup", "payment_reflection", "escalation_form"}:
        # Provide lightweight context to keep multi-turn flows stable.
        session_hint = f"Active flow: {flow}."

    system = WATER_UTILITY_GUARDRAIL_SYSTEM_PROMPT
    # IMPORTANT: this prompt contains JSON examples with braces.
    # Using .format() would treat braces as placeholders, so we do a safe replace instead.
    schema = INTENT_OUTPUT_SCHEMA_INSTRUCTIONS.replace(
        "{allowed_intents}", ", ".join(sorted(ALLOWED_INTENTS_SET))
    )

    user_content = (
        f"{schema}\n\n"
        f"{session_hint}\n"
        f"User message: {message}"
    ).strip()

    text = _post_chat_completions(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        max_tokens=250,
    )

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Groq returned non-JSON output: {text[:250]!r} err={e}")
        raise

    result = _normalize_result(raw)
    if result["intent"] == "out_of_scope" and raw.get("intent") not in ALLOWED_INTENTS_SET:
        logger.warning(f"Groq produced invalid intent: raw={raw!r}")
    return result


def health_check() -> GroqHealth:
    """Ping Groq with a 1-token request to verify connectivity."""

    try:
        text = _post_chat_completions(
            messages=[
                {"role": "system", "content": "Return only JSON: {\"ok\": true}"},
                {"role": "user", "content": "ping"},
            ],
            max_tokens=10,
        )
        json.loads(text)
        return GroqHealth(provider="groq", status="ok")
    except Exception as e:
        return GroqHealth(provider="groq", status="error", detail=str(e))


def _post_chat_completions_text(
    *,
    messages: list[dict[str, str]],
    max_tokens: int = 250,
    temperature: float = 0.4,
) -> str:
    """Call Groq chat completions and return plain text content."""

    payload: Dict[str, Any] = {
        "model": config.groq_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
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

    if resp.status_code != 200:
        raise RuntimeError(f"Groq HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError(f"Unexpected Groq response: {str(data)[:300]}")


WATER_UTILITY_RESPONSE_SYSTEM_PROMPT = """You are a Water Utility Customer Support AI.

You help with water-utility customer support only, including:
- billing and payments
- water supply issues
- leaks and faults
- complaints and follow-ups
- meter issues
- new connections
- office information

Style:
- sound natural and helpful (not robotic)
- keep answers concise
- ask for the minimum information needed to help

Safety / guardrails:
- If the user asks something unrelated to water utility services, politely decline and steer them back.
- Do not invent official contacts, addresses, account balances, payment numbers, or internal system statuses.
"""


def generate_response(
    message: str,
    session: dict,
    *,
    intent: str | None = None,
    facts: str | None = None,
    additional_instructions: str | None = None,
    max_tokens: int = 220,
) -> str:
    """Generate a natural language response using Groq (text output)."""

    flow = session.get("flow")
    session_hint = f"Active flow: {flow}." if flow else ""
    intent_hint = f"Detected intent: {intent}." if intent else ""
    facts_block = f"\n\nFACTS (use only these facts when giving specific details):\n{facts}" if facts else ""
    extra = f"\n\nExtra instructions:\n{additional_instructions}" if additional_instructions else ""

    user_content = (
        f"{session_hint}\n{intent_hint}\n\nUser message: {message}{facts_block}{extra}\n\n"
        "Reply as the assistant."
    ).strip()

    return _post_chat_completions_text(
        messages=[
            {"role": "system", "content": WATER_UTILITY_RESPONSE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=0.4,
    )


def detect_human_request(message: str, session: dict) -> Dict[str, Any]:
    """LLM-only detector for explicit human/agent requests."""

    system = "Return ONLY JSON: {\"request_human\": true|false}."
    user = (
        "Detect if the user explicitly asks to speak to a human agent/operator/real person/customer service. "
        "Return request_human=true only for explicit requests.\n\n"
        f"User message: {message}"
    )

    text = _post_chat_completions(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=40,
    )

    try:
        raw = json.loads(text)
    except Exception:
        return {"request_human": False}

    return {"request_human": bool(raw.get("request_human", False))}


def classify_billing_subintent(message: str, session: dict) -> Dict[str, Any]:
    """LLM-only billing sub-intent classifier.

    Returns JSON: {"case": "payment_not_reflected"|"wrong_bill"|"bill_check"}
    """

    system = (
        "Return ONLY JSON: {\"case\": <one of: payment_not_reflected, wrong_bill, bill_check>}."
    )
    user = (
        "Classify the user's billing-related message into exactly one case:\n"
        "- payment_not_reflected: user paid but payment is missing/not updated/still unpaid\n"
        "- wrong_bill: bill is incorrect/too high/wrong reading\n"
        "- bill_check: balance/bill amount/due date\n\n"
        f"User message: {message}"
    )

    text = _post_chat_completions(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=60,
    )

    try:
        raw = json.loads(text)
    except Exception:
        return {"case": "bill_check"}

    case = raw.get("case")
    if case not in {"payment_not_reflected", "wrong_bill", "bill_check"}:
        case = "bill_check"
    return {"case": case}

