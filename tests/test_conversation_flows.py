"""
Conversation Flow Tests

Tests complete conversation flows end-to-end to verify:
- Multi-turn interactions work correctly
- Context is maintained
- Tools are used appropriately
- Responses are coherent
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import ChatRequest, chat, sessions


class ConversationFlow:
    """Represents a complete conversation flow."""
    
    def __init__(self, name: str, description: str):
        """Initialize flow."""
        self.name = name
        self.description = description
        self.steps: List[Dict] = []
        self.results = []
    
    def add_step(self, user_message: str, expected_intent: str, 
                 should_contain: List[str] = None, should_not_contain: List[str] = None):
        """
        Add a step to the flow.
        
        Args:
            user_message: User's message
            expected_intent: Expected intent classification
            should_contain: Strings that should be in response
            should_not_contain: Strings that should NOT be in response
        """
        self.steps.append({
            'user_message': user_message,
            'expected_intent': expected_intent,
            'should_contain': should_contain or [],
            'should_not_contain': should_not_contain or []
        })
    
    def run(self, phone: str = "+260970000000") -> Tuple[bool, List[Dict]]:
        """
        Run the conversation flow.
        
        Args:
            phone: Phone number for session
        
        Returns:
            Tuple of (success, results)
        """
        sessions.clear()
        self.results = []
        all_passed = True
        
        print(f"\n🔄 Running: {self.name}")
        print(f"   {self.description}\n")
        
        for i, step in enumerate(self.steps, 1):
            try:
                # Send message
                req = ChatRequest(phone=phone, message=step['user_message'])
                response = chat(req)
                
                # Check intent
                intent_match = response['intent'] == step['expected_intent']
                
                # Check response content
                reply = response['reply'].lower()
                contains_all = all(s.lower() in reply for s in step['should_contain'])
                contains_none = not any(s.lower() in reply for s in step['should_not_contain'])
                
                passed = intent_match and contains_all and contains_none
                all_passed = all_passed and passed
                
                result = {
                    'step': i,
                    'user_message': step['user_message'],
                    'expected_intent': step['expected_intent'],
                    'actual_intent': response['intent'],
                    'confidence': response['confidence'],
                    'intent_match': intent_match,
                    'contains_all': contains_all,
                    'contains_none': contains_none,
                    'passed': passed,
                    'reply': response['reply'][:100]
                }
                
                self.results.append(result)
                
                # Print step result
                status = "✅" if passed else "❌"
                print(f"{status} Step {i}: {step['user_message'][:40]}...")
                if not intent_match:
                    print(f"   Intent: expected {step['expected_intent']}, got {response['intent']}")
                if not contains_all:
                    print(f"   Missing content in response")
                if not contains_none:
                    print(f"   Unwanted content in response")
                
            except Exception as e:
                all_passed = False
                result = {
                    'step': i,
                    'user_message': step['user_message'],
                    'error': str(e),
                    'passed': False
                }
                self.results.append(result)
                print(f"❌ Step {i}: ERROR - {str(e)[:50]}")
        
        return all_passed, self.results


def create_test_flows() -> List[ConversationFlow]:
    """Create all test conversation flows."""
    flows = []
    
    # Flow 1: Water Issue Reporting
    flow1 = ConversationFlow(
        "Water Issue Reporting",
        "User reports no water and provides details"
    )
    flow1.add_step(
        "No water coming out",
        "no_water_supply",
        should_contain=["help", "report", "issue"]
    )
    flow1.add_step(
        "name: John, area: Makululu, issue: No water",
        "report_water_fault",
        should_contain=["logged", "reference", "WC-"]
    )
    flows.append(flow1)
    
    # Flow 2: Billing Inquiry
    flow2 = ConversationFlow(
        "Billing Inquiry",
        "User checks their bill"
    )
    flow2.add_step(
        "How much do I owe?",
        "billing_inquiry",
        should_contain=["account", "number"]
    )
    flow2.add_step(
        "123456",
        "billing_inquiry",
        should_contain=["amount", "due", "K"]
    )
    flows.append(flow2)
    
    # Flow 3: Complaint Tracking
    flow3 = ConversationFlow(
        "Complaint Tracking",
        "User tracks existing complaint"
    )
    flow3.add_step(
        "Check my complaint status",
        "complaint_followup",
        should_contain=["reference", "ticket"]
    )
    flow3.add_step(
        "WC-A1B2C3",
        "complaint_followup",
        should_contain=["status", "reference"]
    )
    flows.append(flow3)
    
    # Flow 4: Help Menu
    flow4 = ConversationFlow(
        "Help Menu",
        "User requests help"
    )
    flow4.add_step(
        "Help",
        "general_faq",
        should_contain=["help", "can", "do"]
    )
    flows.append(flow4)
    
    # Flow 5: New Connection
    flow5 = ConversationFlow(
        "New Connection Request",
        "User requests new water connection"
    )
    flow5.add_step(
        "I want a new water connection",
        "new_connection_request",
        should_contain=["connection", "apply", "office"]
    )
    flows.append(flow5)
    
    # Flow 6: Payment Methods
    flow6 = ConversationFlow(
        "Payment Methods",
        "User asks about payment options"
    )
    flow6.add_step(
        "How can I pay?",
        "payment_methods_info",
        should_contain=["payment", "method", "mobile", "bank"]
    )
    flows.append(flow6)
    
    # Flow 7: Office Information
    flow7 = ConversationFlow(
        "Office Information",
        "User asks for office location"
    )
    flow7.add_step(
        "Where is your office?",
        "office_location_hours",
        should_contain=["office", "location", "hours"]
    )
    flows.append(flow7)
    
    # Flow 8: Water Quality Issue
    flow8 = ConversationFlow(
        "Water Quality Issue",
        "User reports water quality problem"
    )
    flow8.add_step(
        "My water is brown and smells bad",
        "water_quality_issue",
        should_contain=["quality", "issue", "report"]
    )
    flows.append(flow8)
    
    # Flow 9: Escalation
    flow9 = ConversationFlow(
        "Human Escalation",
        "User requests to speak with agent"
    )
    flow9.add_step(
        "I need to speak to someone",
        "human_escalation",
        should_contain=["agent", "representative", "escalat"]
    )
    flows.append(flow9)
    
    # Flow 10: Greeting
    flow10 = ConversationFlow(
        "Greeting",
        "User greets the bot"
    )
    flow10.add_step(
        "Hello",
        "general_faq",
        should_contain=["welcome", "help"]
    )
    flows.append(flow10)
    
    return flows


def run_all_flows() -> Tuple[int, int]:
    """Run all conversation flows."""
    flows = create_test_flows()
    
    print("\n" + "="*70)
    print("🧪 CONVERSATION FLOW TESTS")
    print("="*70)
    
    passed_flows = 0
    total_flows = len(flows)
    
    for flow in flows:
        success, results = flow.run()
        if success:
            passed_flows += 1
            print(f"✅ PASSED\n")
        else:
            print(f"❌ FAILED\n")
    
    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Flows Passed: {passed_flows}/{total_flows}")
    print(f"Success Rate: {passed_flows/total_flows*100:.1f}%")
    
    if passed_flows == total_flows:
        print("\n✅ All conversation flows passed!")
    else:
        print(f"\n⚠️  {total_flows - passed_flows} flow(s) failed")
    
    print("="*70 + "\n")
    
    return passed_flows, total_flows


if __name__ == "__main__":
    passed, total = run_all_flows()
    sys.exit(0 if passed == total else 1)
