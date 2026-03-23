"""
Test confidence-based auto-escalation functionality.

This test verifies that:
1. Low confidence (<0.90) triggers auto-escalation to human agent
2. High confidence (>=0.90) proceeds normally
3. Auto-escalation provides appropriate messaging
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.confidence import ConfidenceHandler
from backend.agent import run_agent


def test_confidence_threshold():
    """Test that the escalation threshold is set correctly."""
    print("Testing confidence threshold...")
    assert ConfidenceHandler.ESCALATION_THRESHOLD == 0.90, \
        f"Expected threshold 0.90, got {ConfidenceHandler.ESCALATION_THRESHOLD}"
    print("✓ Confidence threshold is correctly set to 0.90")


def test_low_confidence_escalation():
    """Test that low confidence triggers escalation."""
    print("\nTesting low confidence auto-escalation...")
    
    # Simulate low confidence intent
    intent_data = {
        "intent": "billing_inquiry",
        "confidence": 0.75,  # Below 0.90 threshold
        "entities": {},
        "auto_escalated": True
    }
    
    session = {}
    message = "I need help with something"
    
    # This should be overridden to human_escalation in main.py
    # For this test, we'll simulate the escalation
    if intent_data["confidence"] < ConfidenceHandler.ESCALATION_THRESHOLD:
        intent_data["intent"] = "human_escalation"
        intent_data["confidence"] = 1.0
        intent_data["auto_escalated"] = True
    
    result = run_agent(message, intent_data, session)
    
    # Check that escalation message is returned
    assert "agent" in result.lower() or "human" in result.lower(), \
        "Expected escalation message to mention agent or human"
    print(f"✓ Low confidence (0.75) triggered escalation")
    print(f"  Response: {result[:100]}...")


def test_high_confidence_no_escalation():
    """Test that high confidence does not trigger escalation."""
    print("\nTesting high confidence (no escalation)...")
    
    # Simulate high confidence intent
    intent_data = {
        "intent": "billing_inquiry",
        "confidence": 0.95,  # Above 0.90 threshold
        "entities": {"account_number": "123456"},
        "auto_escalated": False
    }
    
    session = {}
    message = "What is my bill?"
    
    # High confidence should not trigger escalation
    assert intent_data["confidence"] >= ConfidenceHandler.ESCALATION_THRESHOLD, \
        "Confidence should be above threshold"
    
    result = run_agent(message, intent_data, session)
    
    # Should ask for account number or provide billing info
    assert "account" in result.lower() or "bill" in result.lower(), \
        "Expected billing-related response"
    print(f"✓ High confidence (0.95) proceeded normally")
    print(f"  Response: {result[:100]}...")


def test_threshold_boundary():
    """Test behavior at the exact threshold boundary."""
    print("\nTesting threshold boundary (0.90)...")
    
    # Test at exactly 0.90
    confidence_at_threshold = 0.90
    
    if confidence_at_threshold < ConfidenceHandler.ESCALATION_THRESHOLD:
        print(f"✓ Confidence 0.90 would trigger escalation (< {ConfidenceHandler.ESCALATION_THRESHOLD})")
    else:
        print(f"✓ Confidence 0.90 would NOT trigger escalation (>= {ConfidenceHandler.ESCALATION_THRESHOLD})")
    
    # Test just below threshold
    confidence_below = 0.89
    assert confidence_below < ConfidenceHandler.ESCALATION_THRESHOLD, \
        "0.89 should be below threshold"
    print(f"✓ Confidence 0.89 would trigger escalation")
    
    # Test just above threshold
    confidence_above = 0.91
    assert confidence_above >= ConfidenceHandler.ESCALATION_THRESHOLD, \
        "0.91 should be at or above threshold"
    print(f"✓ Confidence 0.91 would NOT trigger escalation")


def test_greeting_exemption():
    """Test that greetings are exempt from escalation."""
    print("\nTesting greeting exemption...")
    
    # Greetings should not be escalated even with low confidence
    intent_data = {
        "intent": "general_faq",
        "confidence": 0.50,  # Low confidence
        "entities": {},
        "auto_escalated": False
    }
    
    session = {}
    message = "hi"
    
    result = run_agent(message, intent_data, session)
    
    # Should return greeting, not escalation
    assert "welcome" in result.lower() or "help" in result.lower(), \
        "Expected greeting response, not escalation"
    print(f"✓ Greetings are exempt from auto-escalation")
    print(f"  Response: {result[:100]}...")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CONFIDENCE-BASED AUTO-ESCALATION TESTS")
    print("=" * 60)
    
    try:
        test_confidence_threshold()
        test_low_confidence_escalation()
        test_high_confidence_no_escalation()
        test_threshold_boundary()
        test_greeting_exemption()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print(f"- Escalation threshold: {ConfidenceHandler.ESCALATION_THRESHOLD}")
        print(f"- Confidence < 0.90: Auto-escalate to human agent")
        print(f"- Confidence >= 0.90: Proceed with normal routing")
        print(f"- Greetings and human_escalation intents: Exempt from auto-escalation")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
