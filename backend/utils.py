"""Utility functions for entity extraction and validation."""

import re
from typing import Dict, Any, Optional

def extract_entities(text: str) -> Dict[str, Any]:
    """Extract common entities from user message."""
    text_lower = text.lower()
    entities = {}
    
    # Meter/Account numbers (simple patterns)
    meter_match = re.search(r'(?:meter|account|acc|no?[:\-]?\s*)?(\d{6,10})', text, re.IGNORECASE)
    if meter_match:
        entities['meter_number'] = meter_match.group(1)
    
    # Phone numbers
    phone_match = re.search(r'(\+?260|0)?[7-9]\d{8}', text)
    if phone_match:
        entities['phone'] = phone_match.group(1)
    
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_match:
        entities['email'] = email_match.group(0)
    
    # Addresses/Areas (simple keyword matching)
    area_keywords = ['road', 'street', 'house', 'plot', 'avenue']
    if any(keyword in text_lower for keyword in area_keywords):
        # Extract potential address
        potential_address = re.search(r'[A-Z][a-z]+(?:\s+(?:Road|Street|House|Plot|Avenue|Rd|St|Hse|Plt|Avn))?', text)
        if potential_address:
            entities['address'] = potential_address.group(0)
    
    return entities

def is_valid_name(name: str) -> bool:
    """Validate name format."""
    name = name.strip()
    if len(name) < 2 or len(name) > 100:
        return False
    
    # Basic name validation
    words = name.split()
    if len(words) < 1 or len(words) > 4:
        return False
    
    # No numbers, reasonable word length
    return not any(c.isdigit() for c in name) and all(2 <= len(word) <= 20 for word in words)