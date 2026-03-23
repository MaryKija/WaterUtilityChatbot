"""
Input validation module for the Water Utility Chatbot.

Provides validation for:
- Phone numbers (E.164 format)
- Message content (length, format)
- Account numbers
- Ticket IDs
"""

import re
from typing import Tuple, Optional


# Constants
MIN_MESSAGE_LENGTH = 1
MAX_MESSAGE_LENGTH = 1000
MIN_PHONE_LENGTH = 10
MAX_PHONE_LENGTH = 15


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Validate phone number format.
    
    Accepts:
    - E.164 format: +260970000000
    - Local format: 0970000000
    - Numeric only: 260970000000
    
    Args:
        phone: Phone number to validate
    
    Returns:
        Tuple of (is_valid, normalized_phone)
    """
    if not phone or not isinstance(phone, str):
        return False, "Phone number is required"
    
    # Remove whitespace and common separators
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", phone.strip())
    
    # Check length
    if len(cleaned) < MIN_PHONE_LENGTH or len(cleaned) > MAX_PHONE_LENGTH:
        return False, f"Phone number must be {MIN_PHONE_LENGTH}-{MAX_PHONE_LENGTH} digits"
    
    # Check if numeric
    if not cleaned.isdigit():
        return False, "Phone number must contain only digits"
    
    # Normalize to E.164 format (assuming Zambia +260)
    if cleaned.startswith("0"):
        normalized = "+260" + cleaned[1:]
    elif cleaned.startswith("260"):
        normalized = "+" + cleaned
    elif cleaned.startswith("+"):
        normalized = cleaned
    else:
        # Assume it's a Zambian number
        normalized = "+260" + cleaned
    
    return True, normalized


def validate_message(message: str) -> Tuple[bool, str]:
    """
    Validate user message.
    
    Args:
        message: Message to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or not isinstance(message, str):
        return False, "Message cannot be empty"
    
    # Strip whitespace
    message = message.strip()
    
    if len(message) < MIN_MESSAGE_LENGTH:
        return False, "Message is too short"
    
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH} characters"
    
    return True, ""


def validate_account_number(account: str) -> Tuple[bool, str]:
    """
    Validate account number format.
    
    Args:
        account: Account number to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not account or not isinstance(account, str):
        return False, "Account number is required"
    
    # Extract numeric part
    cleaned = re.sub(r"\D", "", account.strip())
    
    if len(cleaned) < 6:
        return False, "Account number must be at least 6 digits"
    
    if len(cleaned) > 20:
        return False, "Account number is too long"
    
    return True, ""


def validate_ticket_id(ticket_id: str) -> Tuple[bool, str]:
    """
    Validate ticket ID format (WC-XXXXXX).
    
    Args:
        ticket_id: Ticket ID to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ticket_id or not isinstance(ticket_id, str):
        return False, "Ticket ID is required"
    
    # Check format: WC-XXXXXX (WC prefix, dash, 6 alphanumeric chars)
    pattern = r"^WC-[A-Z0-9]{6}$"
    if not re.match(pattern, ticket_id.upper().strip()):
        return False, "Ticket ID must be in format WC-XXXXXX"
    
    return True, ""


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ""
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Limit consecutive whitespace
    text = re.sub(r"\s+", " ", text)
    
    # Remove control characters except newlines and tabs
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
    
    return text.strip()


def extract_account_number(text: str) -> Optional[str]:
    """
    Extract account number from text.
    
    Handles formats like:
    - "account_number: 123456"
    - "123456"
    - "account 123456"
    
    Args:
        text: Text to extract from
    
    Returns:
        Extracted account number or None
    """
    if not text:
        return None
    
    # Try explicit format: "account_number: 123456"
    match = re.search(r"account_number\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Try "account: 123456" or "account 123456"
    match = re.search(r"account\s*[:=]?\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Try to find any sequence of 6+ digits
    match = re.search(r"\b(\d{6,})\b", text)
    if match:
        return match.group(1)
    
    return None


def extract_ticket_id(text: str) -> Optional[str]:
    """
    Extract ticket ID from text.
    
    Handles formats like:
    - "ticket_id: WC-1234ABCD"
    - "WC-1234ABCD"
    - "reference WC-1234ABCD"
    
    Args:
        text: Text to extract from
    
    Returns:
        Extracted ticket ID or None
    """
    if not text:
        return None
    
    # Try explicit format: "ticket_id: WC-1234ABCD"
    match = re.search(r"ticket_id\s*[:=]\s*(WC-[A-Z0-9]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Try "ticket: WC-..." or "reference: WC-..."
    for keyword in ["ticket", "reference", "ref"]:
        match = re.search(rf"{keyword}\s*[:=]?\s*(WC-[A-Z0-9]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    # Try to find WC-XXXXXXXX pattern anywhere
    match = re.search(r"(WC-[A-Z0-9]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return None
