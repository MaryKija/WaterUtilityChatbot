"""Quick manual smoke-test for Groq-only classifier via FastAPI.

Kept intentionally simple for the capstone demo.
"""

import json
import requests

print("Testing Groq-only intent classification...")
print("=" * 60)

# Test with a few sample messages
test_messages = [
    "Report a water fault",
    "Check my bill",
    "I need a new connection",
    "No water in my area"
]

for msg in test_messages:
    print(f"\nMessage: {msg}")
    resp = requests.post(
        "http://localhost:8000/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"phone": "+260970000000", "message": msg}),
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    print(f"Intent: {result['intent']}")
    print(f"Confidence: {result['confidence']}")
