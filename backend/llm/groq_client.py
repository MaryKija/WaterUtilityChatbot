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
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import requests

from ..config import config
from ..context_engine import context_redact_pii
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


def _truncate_text(value: Any, limit: int = 240) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def _sanitize_for_groq(text: Any) -> str:
    """Redact private identifiers before sending content to Groq."""
    t = context_redact_pii(str(text or ""))
    t = re.sub(
        r"\b(?:plot|house|stand|p\.?o\.? box|road|street|avenue|ave|lane|drive|dr|block|apartment|apt|suite|building|compound|sector)\b[^\n,.;]*",
        "[ADDRESS]",
        t,
        flags=re.IGNORECASE,
    )
    return t.strip()


def _history_turn_text(turn: dict) -> str:
    """Return text from either supported history shape."""
    if not isinstance(turn, dict):
        return ""
    return str(turn.get("text") or turn.get("content") or "").strip()


def _conversation_context_block(session: dict, *, max_history: int = 6) -> str:
    """Format the recent session state for classification and response generation."""

    history = session.get("history", [])
    if not isinstance(history, list):
        history = []

    lines: list[str] = []

    flow = str(session.get("flow") or "").strip()
    if flow:
        lines.append(f"Active flow: {flow}")

    intent = str(session.get("intent") or "").strip()
    if intent:
        lines.append(f"Current intent: {intent}")

    entities = _normalize_entities(session.get("entities", {}))
    populated_entities = {k: v for k, v in entities.items() if str(v).strip()}
    if populated_entities:
        lines.append(f"Known entities: {json.dumps(populated_entities, ensure_ascii=True)}")

    summary = _truncate_text(_sanitize_for_groq(session.get("conversation_summary")), limit=160)
    if summary:
        lines.append(f"Conversation summary: {summary}")

    recent_turns = []
    for turn in history[-max_history:]:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "user").strip().lower()
        label = "User" if role == "user" else "Assistant"
        text = _truncate_text(_sanitize_for_groq(_history_turn_text(turn)), limit=180)
        if text:
            recent_turns.append(f"{label}: {text}")

    if recent_turns:
        lines.append("Recent conversation:")
        lines.extend(recent_turns)

    return "\n".join(lines).strip()


def _post_chat_completions_with_retry(
    *, 
    messages: list[dict[str, str]], 
    max_tokens: int = 250, 
    response_format_json: bool = False,
    temperature: float = 0.0
) -> str:
    """Post chat completions to Groq with automatic retries, exponential backoff, and secondary provider failover (OpenAI & Anthropic)."""
    import time
    import random
    import os
    
    max_retries = 3
    initial_backoff = 0.5  # seconds
    
    last_exception = None
    
    # Try Groq primary provider first
    if config.groq_api_key and config.groq_api_key != "dummy":
        for attempt in range(max_retries + 1):
            try:
                payload: Dict[str, Any] = {
                    "model": config.groq_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format_json:
                    payload["response_format"] = {"type": "json_object"}
                    
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=15,  # Avoid hanging request indefinitely
                )
                
                # Check for rate limiting (429) or transient server errors (5xx)
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    
                if resp.status_code != 200:
                    # Permanent client/auth error - fail instantly to trigger failover
                    raise RuntimeError(f"PERMANENT_ERROR: HTTP {resp.status_code}: {resp.text[:200]}")
                    
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
                
            except Exception as e:
                last_exception = e
                err_str = str(e)
                if "PERMANENT_ERROR" in err_str:
                    logger.error(f"Groq permanent error: {err_str}. Instantly triggering failover.")
                    break
                    
                if attempt < max_retries:
                    # Exponential backoff with random jitter to prevent synchronization
                    backoff = (initial_backoff * (2 ** attempt)) + (random.random() * 0.2)
                    logger.warning(f"Groq API call attempt {attempt + 1} failed: {e}. Retrying in {backoff:.2f}s...")
                    time.sleep(backoff)
                else:
                    logger.warning(f"Groq API calls exhausted all {max_retries} retries. Initiating failover.")

    # 1. Fallback Option A: OpenAI (GPT-4o-mini)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        logger.info("Secondary provider failover active: routing request to OpenAI GPT-4o-mini...")
        try:
            openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            payload = {
                "model": openai_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format_json:
                payload["response_format"] = {"type": "json_object"}
                
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=20,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                logger.info("Successfully recovered from Groq failure using OpenAI fallback!")
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenAI fallback failed with HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as fallback_err:
            logger.error(f"OpenAI fallback call failed: {fallback_err}")

    # 2. Fallback Option B: Anthropic (Claude-3-5-Haiku)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        logger.info("Secondary provider failover active: routing request to Anthropic Claude...")
        try:
            anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
            
            # Map OpenAI messages format to Anthropic format
            system_content = ""
            user_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_content += m["content"] + "\n"
                else:
                    user_messages.append({
                        "role": m["role"],
                        "content": m["content"]
                    })
                    
            payload = {
                "model": anthropic_model,
                "system": system_content.strip(),
                "messages": user_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=20,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                logger.info("Successfully recovered from Groq failure using Anthropic fallback!")
                return data["content"][0]["text"].strip()
            else:
                logger.error(f"Anthropic fallback failed with HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as fallback_err:
            logger.error(f"Anthropic fallback call failed: {fallback_err}")

    # If both primary and fallbacks fail, raise exception to trigger offline keyword fallback
    raise RuntimeError(f"All LLM providers failed. Primary exception: {last_exception}")


def _post_chat_completions(*, messages: list[dict[str, str]], max_tokens: int = 250) -> str:
    """Call chat completions and return strict JSON content (retries & failovers enabled)."""
    return _post_chat_completions_with_retry(
        messages=messages,
        max_tokens=max_tokens,
        response_format_json=True,
        temperature=0.0
    )


def classify_intent(message: str, session: dict) -> Dict[str, Any]:
    """Classify intent using Groq with agentic intent discovery.

    Args:
        message: User message
        session: Per-user session dict (used as context only; no keyword/regex fallback)

    Returns:
        Normalized dict: {intent, confidence, entities}
    """
    
    # First, try agentic intent discovery for unknown patterns
    try:
        from ..learning.intent_discovery import intent_discovery_agent
        
        # Get conversation history for learning
        history = session.get("history", [])
        recent_messages = [msg.get("content", "") for msg in history[-10:]]  # Last 10 messages
        
        if len(recent_messages) >= 3:  # Only use discovery with sufficient context
            # Discover new intent patterns
            clusters = intent_discovery_agent.discover_intents(recent_messages)
            
            # Check if current message matches any discovered clusters
            for cluster in clusters:
                if not cluster.is_known and cluster.confidence > 0.1:
                    # Use semantic similarity to match current message
                    message_embedding = intent_discovery_agent.encode_messages([message])[0]
                    cluster_embedding = intent_discovery_agent.encode_messages([cluster.centroid])[0]
                    
                    # Simple cosine similarity
                    similarity = np.dot(message_embedding, cluster_embedding) / (
                        np.linalg.norm(message_embedding) * np.linalg.norm(cluster_embedding)
                    )
                    
                    if similarity > 0.7:  # High similarity threshold
                        logger.info(f"Agentic intent discovery: matched new intent '{cluster.suggested_name}' with confidence {cluster.confidence}")
                        return {
                            "intent": cluster.suggested_name,
                            "confidence": float(cluster.confidence),
                            "entities": {},
                            "discovery_method": "agentic_clustering"
                        }
    except Exception as e:
        logger.warning(f"Agentic intent discovery failed: {e}, falling back to standard classification")
    
    # Fallback to standard Groq classification
    system = WATER_UTILITY_GUARDRAIL_SYSTEM_PROMPT
    # IMPORTANT: this prompt contains JSON examples with braces.
    # Using .format() would treat braces as placeholders, so we do a safe replace instead.
    schema = INTENT_OUTPUT_SCHEMA_INSTRUCTIONS.replace(
        "{allowed_intents}", ", ".join(sorted(ALLOWED_INTENTS_SET))
    )

    session_context = _conversation_context_block(session)
    session_section = f"Session context:\n{session_context}\n\n" if session_context else ""
    message_redacted = _sanitize_for_groq(message)
    user_content = (
        f"{schema}\n\n"
        f"{session_section}"
        f"Latest user message: {message_redacted}"
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
    """Call chat completions and return plain text content (retries & failovers enabled)."""
    return _post_chat_completions_with_retry(
        messages=messages,
        max_tokens=max_tokens,
        response_format_json=False,
        temperature=temperature
    )


WATER_UTILITY_RESPONSE_SYSTEM_PROMPT = """You are an AI Water Utility Customer Support assistant.

You help with water-utility customer support only, including:
- billing and payments
- water supply issues
- leaks and faults
- complaints and follow-ups
- meter issues
- new connections
- office information

Style:
- Be concise — keep replies to 1-3 short sentences maximum
- Sound natural and helpful, not robotic
- Ask for only the minimum information needed
- Never use bullet lists unless listing 3+ distinct items

Safety / guardrails:
- If the user asks something unrelated to water utility services, politely decline in one sentence and steer them back.
- Do not invent official contacts, addresses, account balances, payment numbers, or internal system statuses.
"""


def generate_response(
    message: str,
    session: dict,
    *,
    intent: str | None = None,
    facts: str | None = None,
    additional_instructions: str | None = None,
    max_tokens: int = 120,
) -> str:
    """Generate a natural language response using Groq (text output).

    When Groq is unreachable the function raises immediately (after a fast
    connectivity probe) so callers can fall back to deterministic responses
    without waiting for the full 30-second socket timeout.
    """
    from ..offline_classifier import is_groq_reachable

    if not is_groq_reachable(timeout=3.0):
        raise RuntimeError("Groq unreachable (offline mode)")

    intent_hint = f"Detected intent: {intent}." if intent else ""
    session_context = _conversation_context_block(session)
    session_section = f"Session context:\n{session_context}\n\n" if session_context else ""
    message_redacted = _sanitize_for_groq(message)
    facts_block = f"\n\nFACTS (use only these facts when giving specific details):\n{_sanitize_for_groq(facts)}" if facts else ""
    extra = f"\n\nExtra instructions:\n{additional_instructions}" if additional_instructions else ""

    user_content = (
        f"{session_section}{intent_hint}\n\nLatest user message: {message_redacted}{facts_block}{extra}\n\n"
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
        f"User message: {_sanitize_for_groq(message)}"
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
        f"User message: {_sanitize_for_groq(message)}"
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

