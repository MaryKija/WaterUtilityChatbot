"""backend/offline_classifier.py

Keyword-based intent classifier that runs when Groq is unreachable.

This is intentionally simple and deterministic — no ML, no network calls.
It covers the most common water-utility intents so the bot remains useful
on weak or no-internet connections (common in rural Zambia).

Priority order matters: more specific patterns are checked first.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Connectivity cache
# ---------------------------------------------------------------------------
# We cache the last known connectivity state so we don't attempt a 30-second
# Groq timeout on every single message when the network is down.

_CONNECTIVITY_CACHE: Dict[str, Any] = {
    "online": None,       # True / False / None (unknown)
    "checked_at": 0.0,    # epoch seconds
    "ttl": 30.0,          # re-check every 30 seconds
}


def is_groq_reachable(timeout: float = 3.0) -> bool:
    """Quick TCP probe to api.groq.com:443.

    Returns cached result if checked within the last TTL seconds.
    Uses a 3-second timeout so a bad network fails fast instead of
    blocking the user for 30 seconds.
    """
    import socket

    now = time.monotonic()
    cache = _CONNECTIVITY_CACHE

    # Return cached result if still fresh
    if cache["online"] is not None and (now - cache["checked_at"]) < cache["ttl"]:
        return bool(cache["online"])

    try:
        sock = socket.create_connection(("api.groq.com", 443), timeout=timeout)
        sock.close()
        online = True
    except OSError:
        online = False

    cache["online"] = online
    cache["checked_at"] = now
    return online


def invalidate_connectivity_cache() -> None:
    """Force a fresh connectivity check on the next call."""
    _CONNECTIVITY_CACHE["online"] = None
    _CONNECTIVITY_CACHE["checked_at"] = 0.0


# ---------------------------------------------------------------------------
# Keyword rules
# ---------------------------------------------------------------------------
# Each rule is (intent_name, confidence, list_of_regex_patterns).
# Patterns are matched case-insensitively against the full message.
# First match wins.

_RULES: list[tuple[str, float, list[str]]] = [
    # --- Emergencies / escalation (check before generic fault) ---
    ("escalation", 0.90, [
        r"\bhuman\b.*\bagent\b",
        r"\bspeak\b.*\b(person|agent|staff|representative|rep)\b",
        r"\btalk\b.*\b(person|agent|staff|representative|rep)\b",
        r"\bconnect\b.*\b(agent|staff|representative)\b",
        r"\bcustomer\s+service\b",
        r"\breal\s+person\b",
    ]),

    # --- Complaint follow-up (check before report_fault) ---
    ("complaint_followup", 0.88, [
        r"\bWC-[A-Z0-9]{4,8}\b",
        r"\b(status|update|progress)\b.*\b(complaint|ticket|reference|report)\b",
        r"\b(check|track)\b.*\b(complaint|ticket|reference)\b",
        r"\bmy\s+(complaint|ticket|report)\b",
        r"\breference\s+(number|no\.?|#)\b",
    ]),

    # --- Leak report ---
    ("leak_report", 0.92, [
        r"\b(leak|leaking|leakage|burst|pipe\s+burst|broken\s+pipe)\b",
        r"\bwater\s+(is\s+)?(coming\s+out|flowing|gushing|spilling)\b",
        r"\bpipe\s+(is\s+)?(broken|cracked|damaged)\b",
    ]),

    # --- Report fault / no water / outage ---
    ("report_fault", 0.90, [
        r"\bno\s+water\b",
        r"\bwater\s+(is\s+)?(out|off|cut|gone|not\s+coming)\b",
        r"\bwithout\s+water\b",
        r"\b(low|poor|weak)\s+(water\s+)?pressure\b",
        r"\bdirty\s+water\b",
        r"\bcontaminat(ed|ion)\b",
        r"\bwater\s+quality\b",
        r"\bsmell(y|ing)?\s+water\b",
        r"\bbad\s+taste\b",
        r"\bunsafe\s+water\b",
        r"\bwater\s+(supply|outage|shortage|problem|issue|fault)\b",
        r"\b(report|log)\b.*\b(fault|problem|issue)\b",
        r"\boutage\b",
    ]),

    # --- Payment info ---
    ("payment_info", 0.88, [
        r"\b(how|where)\b.*\bpay\b",
        r"\bpayment\s+(method|option|channel|way)\b",
        r"\b(mtn|airtel|zamtel)\b.*\b(money|pay)\b",
        r"\bmobile\s+money\b",
        r"\bbank\s+transfer\b",
        r"\bpay\b.*\b(bill|balance|water)\b",
    ]),

    # --- Billing ---
    ("billing_inquiry", 0.90, [
        r"\b(my\s+)?(bill|balance|amount\s+due|statement)\b",
        r"\bhow\s+much\b.*\b(owe|pay|due)\b",
        r"\b(check|view|see)\b.*\b(bill|balance|account)\b",
        r"\bbilling\b",
        r"\baccount\s+(number|balance|statement)\b",
        r"\bdue\s+date\b",
        r"\boverdue\b",
        r"\bunpaid\b",
    ]),

    # --- Meter problem ---
    ("meter_problem", 0.88, [
        r"\bmeter\b.*\b(not\s+working|broken|faulty|wrong|issue|problem)\b",
        r"\b(broken|faulty|wrong)\b.*\bmeter\b",
        r"\bmeter\s+reading\b",
        r"\bsubmit\b.*\breading\b",
        r"\bmy\s+meter\b",
    ]),

    # --- New connection ---
    ("new_connection", 0.88, [
        r"\bnew\s+(water\s+)?(connection|supply|line|pipe)\b",
        r"\b(apply|application)\b.*\b(connection|water\s+supply)\b",
        r"\bconnect\b.*\b(water|supply|pipe)\b",
        r"\binstall\b.*\b(water|meter|pipe)\b",
        r"\bget\s+water\s+(connected|installed)\b",
    ]),

    # --- Office info ---
    ("office_info", 0.88, [
        r"\b(office|branch|location|address)\b",
        r"\b(opening|working|operating)\s+hours\b",
        r"\bwhere\b.*\b(office|branch|located)\b",
        r"\bcontact\b.*\b(number|details|info)\b",
        r"\bphone\s+number\b",
    ]),

    # --- General chat / greeting ---
    ("general_chat", 0.75, [
        r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|howzit|muli\s+bwanji)\b",
        r"^(thanks?|thank\s+you|thx|cheers)\b",
        r"\bwho\s+are\s+you\b",
        r"\bwhat\s+can\s+you\s+do\b",
        r"\bhelp\s+me\b",
        r"^help$",
    ]),
]

# Pre-compile all patterns
_COMPILED_RULES: list[tuple[str, float, list[re.Pattern[str]]]] = [
    (intent, conf, [re.compile(p, re.IGNORECASE) for p in patterns])
    for intent, conf, patterns in _RULES
]


def classify_offline(message: str) -> Dict[str, Any]:
    """Classify intent using keyword rules — no network required.

    Returns the same shape as groq_client.classify_intent():
      {"intent": str, "confidence": float, "entities": dict, "source": "offline_keywords"}
    """
    text = (message or "").strip()

    for intent, confidence, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(text):
                entities = _extract_entities_offline(text)
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "entities": entities,
                    "source": "offline_keywords",
                }

    # Nothing matched — treat as general chat so the bot still responds
    return {
        "intent": "general_chat",
        "confidence": 0.55,
        "entities": {},
        "source": "offline_keywords",
    }


def _extract_entities_offline(text: str) -> Dict[str, str]:
    """Extract the most common entities without an LLM."""
    entities: Dict[str, str] = {
        "account_number": "",
        "ticket_id": "",
        "name": "",
        "area": "",
    }

    # Ticket ID: WC-XXXXXX
    m = re.search(r"\b(WC-[A-Z0-9]{4,8})\b", text, re.IGNORECASE)
    if m:
        entities["ticket_id"] = m.group(1).upper()

    # Account number: 6+ digit standalone number
    m = re.search(r"\b(\d{6,12})\b", text)
    if m:
        entities["account_number"] = m.group(1)

    # Known Zambian locations
    locations = [
        "kabwe", "lusaka", "ndola", "kitwe", "mufulira", "livingstone",
        "kasama", "chibombo", "kapiri", "mkushi", "serenje", "makululu",
        "riverside", "industrial area", "city center",
    ]
    text_lower = text.lower()
    for loc in locations:
        if loc in text_lower:
            entities["area"] = loc.title()
            break

    return entities


# ---------------------------------------------------------------------------
# Offline response templates
# ---------------------------------------------------------------------------
# When Groq is down, the bot can still give useful structured responses
# for the most common intents using these templates + local DB data.

OFFLINE_RESPONSES: Dict[str, str] = {
    "general_chat": (
        "Hello! I am your Water Utility Assistant. I can help with:\n\n"
        "- Report a fault: no water, leaks, low pressure\n"
        "- Billing: check your balance or bill\n"
        "- Complaint status: track your reference number\n"
        "- Payment methods: how and where to pay\n"
        "- Office info: branch locations and hours\n\n"
        "What can I help you with today?"
    ),
    "out_of_scope": (
        "I can only assist with water utility services — billing, faults, "
        "complaints, payments, and connections. How can I help you?"
    ),
    "offline_notice": (
        "Limited connectivity detected.\n\n"
        "I am running in offline mode. I can still:\n"
        "- Log complaints\n"
        "- Check your bill (with account number)\n"
        "- Check complaint status (with reference number)\n"
        "- Provide office information\n\n"
        "Some AI features are temporarily unavailable. "
        "Please try again when connectivity improves."
    ),
}
