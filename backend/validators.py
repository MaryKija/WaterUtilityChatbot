"""backend/validators.py

Validation helpers used by the new context engine.

Hard requirement: provide these exact functions:
- `is_valid_account()`
- `is_valid_phone()`
- `is_valid_name()`
- `is_valid_email()`

These are intentionally lightweight and deterministic so they can be used in
regex-first extraction and as guardrails before any LLM fallback.
"""

from __future__ import annotations

from typing import Optional
import re


_RE_MULTI_SPACE = re.compile(r"\s+")


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def is_valid_account(account: str) -> bool:
    """Return True if `account` looks like a plausible account number.

    Policy (local heuristic):
    - digits only after cleanup
    - length 6..20
    """

    digits = _digits_only(account)
    return 6 <= len(digits) <= 20


def is_valid_phone(phone: str) -> bool:
    """Return True if `phone` looks like a plausible phone number.

    Accepts:
    - +260970000000
    - 260970000000
    - 0970000000
    - 970000000 (treated as local)

    Policy (heuristic):
    - digits length 9..15 (to cover local + E.164 without being too strict)
    """

    raw = (phone or "").strip()
    if not raw:
        return False

    cleaned = re.sub(r"[\s\-\(\)\.]+", "", raw)
    # Allow leading '+' then digits.
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    digits = _digits_only(cleaned)
    if digits != cleaned:
        return False

    return 9 <= len(digits) <= 15


def is_valid_name(name: str) -> bool:
    """Return True if `name` looks like a plausible human name.

    Policy (heuristic):
    - 2..60 chars
    - letters plus spaces / apostrophes / hyphens
    - must contain at least 2 letters
    """

    n = (name or "").strip()
    n = _RE_MULTI_SPACE.sub(" ", n)
    if not (2 <= len(n) <= 60):
        return False

    # Allow typical name punctuation.
    if not re.fullmatch(r"[A-Za-z][A-Za-z\s'\-\.]*[A-Za-z]", n):
        return False

    # Ensure at least two letters overall.
    letters = re.findall(r"[A-Za-z]", n)
    return len(letters) >= 2


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def extract_account_number(text: str) -> Optional[str]:
    """Extract account number from text using heuristic regex."""
    match = re.search(r'\b\d{6,20}\b', text)
    return match.group(0) if match else None


def extract_ticket_id(text: str) -> Optional[str]:
    """Extract ticket ID like WC-ABC123 from text."""
    match = re.search(r'WC-[A-Z0-9]{6}', text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def normalize_phone(phone: str) -> str:
    """Best-effort phone normalization to E.164-like form for Zambia (+260).

    Not required by the spec, but useful for consistent storage.
    """

    raw = (phone or "").strip()
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", raw)
    if cleaned.startswith("+"):
        digits = _digits_only(cleaned)
        return "+" + digits if digits else ""

    digits = _digits_only(cleaned)
    if not digits:
        return ""

    if digits.startswith("0"):
        return "+260" + digits[1:]
    if digits.startswith("260"):
        return "+" + digits
    # Local without leading 0.
    return "+260" + digits

