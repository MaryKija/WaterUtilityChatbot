"""backend/entity_extractor.py

Universal entity extraction: regex-first → validate → LLM fallback.

Integrates with workflows to skip redundant questions."""

import re
from typing import Dict, Optional

from .validation import is_valid_name, is_valid_phone, is_valid_email, normalize_phone, extract_account_number, extract_ticket_id
from .validators import is_valid_account
from .llm.groq_client import generate_response
from .config import config
from .logger import logger

def extract_entities(text: str) -> Dict[str, str]:
    """Extract entities from natural language text.

    Regex-first for speed/accuracy, LLM fallback only when needed.
    """
    text = text.strip()
    entities: Dict[str, str] = {}

    # Account number
    acct = extract_account_number(text)
    if acct and is_valid_account(acct):
        entities["account_number"] = acct

    # Ticket ID
    tid = extract_ticket_id(text)
    if tid:
        entities["ticket_id"] = tid

    # Phone: multiple patterns
    phone_patterns = [
        r"(\+260[\d\s\-]{9,})",  # +260XXXXXXXXX
        r"(0[\d\s\-]{9,})",  # 09XXXXXXXXX
        r"(\d{10,})",  # Raw digits
    ]
    for pattern in phone_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = re.sub(r"[\s\-]", "", m.group(1))
            if is_valid_phone(candidate):
                entities["phone"] = normalize_phone(candidate)
                break

    # Email
    m_email = re.search(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", text)
    if m_email and is_valid_email(m_email.group(0)):
        entities["email"] = m_email.group(0)

    # Name: explicit patterns first
    name_patterns = [
        r"(?:my name is|i am|i'm|name)\s*[:=]?\s*([A-Za-z][A-Za-z\s'\-\.]{1,60})\b",
        r"\b([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)\b",  # Lastname first + middle
    ]
    for pattern in name_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if is_valid_name(name):
                entities["name"] = name
                break

    # Address: heuristic (streets, plot, house)
    m_addr = re.search(r"\b(plot|house|street|avenue|road|area)[\s\w\-\,\.0-9]+", text, re.IGNORECASE)
    if m_addr and len(m_addr.group(0)) > 10:
        entities["address"] = m_addr.group(0).strip()

    # Amount
    m_amt = re.search(r"\b(?:k\s*)?(\d+(?:,\d{3})*(?:\.\d{2})?)\b", text, re.IGNORECASE)
    if m_amt:
        entities["amount"] = m_amt.group(1)

    # Date
    m_date = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|today|yesterday)\b", text, re.IGNORECASE)
    if m_date:
        entities["date"] = m_date.group(1)

    logger.info("entities_extracted", extra={"entities": entities, "text_preview": text[:100]})
    return entities

def _llm_fallback(text: str, missing_entities: list[str]) -> Dict[str, str]:
    """Groq fallback for when regex fails."""
    system = (
        "Extract these entities from the message: " + ", ".join(missing_entities) +
        ". Return JSON: {\"name\": \"...\", \"phone\": \"...\"}. Only include found entities."
    )
    
    try:
        result = generate_response(
            text,
            {},
            intent="entity_extraction",
            additional_instructions=system,
            max_tokens=100,
        )
        # Parse simple JSON response.
        parsed = {}
        for k in missing_entities:
            if k in result:
                parsed[k] = result[k]
        return parsed
    except Exception as e:
        logger.warning(f"llm_fallback_failed err={e}")
        return {}

def extract_and_validate(text: str, required: list[str]) -> Dict[str, str]:
    """Full pipeline: extract → validate → LLM fallback → normalize."""
    entities = extract_entities(text)
    missing = [k for k in required if k not in entities]
    
    if missing:
        logger.debug("regex_missed", extra={"missing": missing})
        fallback = _llm_fallback(text, missing)
        entities.update(fallback)
    
    # Final validation/normalization.
    validated = {}
    if "phone" in entities:
        validated["phone"] = normalize_phone(entities["phone"])
    validated.update({k: v for k, v in entities.items() if k != "phone"})
    
    return validated
