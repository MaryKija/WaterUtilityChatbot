"""backend/security.py

Deterministic security guardrails to harden the LgWSC Water Utility Chatbot.
Handles input sanitization (stripping jailbreak patterns, blocking adversarial URLs)
and output validation (filtering code blocks and prompt leakage).
"""

from __future__ import annotations

import re
from .logger import logger


class SecurityViolation(Exception):
    """Raised when an input or output fails security validation."""
    pass


# Deterministic prompt injection and jailbreak patterns (case-insensitive)
JAILBREAK_PATTERNS = [
    r"\bignore\s+(?:all\s+|previous\s+)?instructions\b",
    r"\bdisregard\s+(?:all\s+|previous\s+)?instructions\b",
    r"\bdisregard\s+(?:all\s+|previous\s+)?directives\b",
    r"\bsystem\s*:\s*\b",
    r"\bhuman\s*:\s*\b",
    r"\byou\s+are\s+now\s+a\s+\b",
    r"\bforget\s+(?:everything\s+|all\s+)?(?:you\s+know|learned|instructions)\b",
]

# Domain and URL patterns to prevent phishing/spam link injection
URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)\S+\b|"
    r"\b[a-zA-Z0-9.-]+\.(?:com|org|net|gov|edu|co|io|biz|info|me|zm|co\.zm)\b",
    re.IGNORECASE
)


def sanitize_input(message: str) -> str:
    """Sanitize the incoming user message against prompt injection and malicious links.

    Strips suspicious directive override phrases and strictly blocks URLs/domains
    to prevent phishing link forwarding.

    Args:
        message: The raw incoming user message.

    Returns:
        The sanitized user message.

    Raises:
        SecurityViolation: If the input contains a URL or a serious jailbreak attempt.
    """
    clean_msg = (message or "").strip()
    if not clean_msg:
        return clean_msg

    # 1. Check for URL / domain links to prevent forwarding phishing/spam
    if URL_PATTERN.search(clean_msg):
        logger.warning(f"Security: Blocked user message containing URL/domain link: {clean_msg[:100]}...")
        raise SecurityViolation("Sending links or domains is not allowed for security reasons.")

    # 2. Scan and strip suspicious jailbreak phrases
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, clean_msg, re.IGNORECASE):
            logger.warning(f"Security: Detected suspicious jailbreak pattern match '{pattern}' in: {clean_msg[:100]}...")
            
            # Refuse the jailbreak query outright for high security
            raise SecurityViolation("I am unable to process that request due to security policy restrictions.")

    return clean_msg


def validate_output(output: str) -> str:
    """Validate and sanitize generated LLM response before delivering it to the user.

    Blocks responses containing markdown code blocks, raw JSON instructions,
    or indicators of system prompt/logic leakage.

    Args:
        output: The generated LLM response.

    Returns:
        The validated and sanitized output response string, or a pre-approved safe fallback.
    """
    cleaned_out = (output or "").strip()
    if not cleaned_out:
        return cleaned_out

    violation_detected = False
    reason = ""

    # 1. Block outputs containing markdown code blocks (often used to dump system files/code)
    if "```" in cleaned_out:
        violation_detected = True
        reason = "markdown code block detected"

    # 2. Block outputs containing obvious system prompt variables or instruction leaks
    system_leak_patterns = [
        r"\bWATER_UTILITY_RESPONSE_SYSTEM_PROMPT\b",
        r"\bWATER_UTILITY_GUARDRAIL_SYSTEM_PROMPT\b",
        r"\bYou are an AI Water Utility Customer Support assistant\b",
        r"\bYou ONLY handle\b",
        r"\bIf the user asks anything unrelated\b",
        r"\bAllowed intents\b",
        r"\bDo not invent official contacts\b",
    ]
    for pattern in system_leak_patterns:
        if re.search(pattern, cleaned_out, re.IGNORECASE):
            violation_detected = True
            reason = f"system instruction leakage pattern '{pattern}'"
            break

    if violation_detected:
        logger.error(f"Security: Intercepted LLM output leakage ({reason}). Delivering pre-approved safe fallback.")
        return (
            "I apologize, but I am unable to provide that response as it violates security policies. "
            "How can I help you with your water services today?"
        )

    return cleaned_out
