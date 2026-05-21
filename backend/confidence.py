"""
Tiered Confidence Handler with Progressive Escalation

Implements a sophisticated confidence-based system that:
1. Uses multiple confidence tiers for different handling strategies
2. Tracks low-confidence interactions per session
3. Only escalates after 3 consecutive low-confidence turns
4. Requests clarification before escalating
5. Learns from escalations to improve future responses
"""

<<<<<<< HEAD
from typing import Dict, Tuple, Optional
=======
from typing import Dict, Tuple, Any, Optional
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
from enum import Enum


class ConfidenceTier(Enum):
    """Confidence tiers for intent handling."""
    COMMAND = "command"  # ≥90% - Direct command match
    KEYWORD = "keyword"  # 84-89% - Keyword match
    ACCEPTABLE = "acceptable"  # 75-83% - Use LLM to interpret
    LOW = "low"  # 50-74% - Ask for clarification
    VERY_LOW = "very_low"  # <50% - Request rephrase


class ConfidenceHandler:
    """Handle tiered confidence classifications with progressive escalation."""
    
    # Confidence thresholds
    COMMAND_THRESHOLD = 0.90  # Direct command match
    KEYWORD_THRESHOLD = 0.84  # Keyword match only
    ACCEPTABLE_THRESHOLD = 0.75  # Acceptable but uncertain
    LOW_THRESHOLD = 0.50  # Low confidence
    
    # Escalation settings
    MAX_LOW_CONFIDENCE_TURNS = 3  # Escalate after 3 low-confidence turns
    
    @staticmethod
    def get_confidence_tier(confidence: float) -> ConfidenceTier:
        """
        Determine confidence tier based on score.
        
        Args:
            confidence: Confidence score (0.0-1.0)
        
        Returns:
            ConfidenceTier enum value
        """
        if confidence >= ConfidenceHandler.COMMAND_THRESHOLD:
            return ConfidenceTier.COMMAND
        elif confidence >= ConfidenceHandler.KEYWORD_THRESHOLD:
            return ConfidenceTier.KEYWORD
        elif confidence >= ConfidenceHandler.ACCEPTABLE_THRESHOLD:
            return ConfidenceTier.ACCEPTABLE
        elif confidence >= ConfidenceHandler.LOW_THRESHOLD:
            return ConfidenceTier.LOW
        else:
            return ConfidenceTier.VERY_LOW
    
    @staticmethod
    def should_escalate(session: dict) -> bool:
        """
        Determine if session should be escalated based on low-confidence history.
        
        Args:
            session: User session dictionary
        
        Returns:
            True if should escalate, False otherwise
        """
        low_confidence_count = session.get("low_confidence_count", 0)
        return low_confidence_count >= ConfidenceHandler.MAX_LOW_CONFIDENCE_TURNS
    
    @staticmethod
    def increment_low_confidence(session: dict) -> int:
        """
        Increment low-confidence counter for session.
        
        Args:
            session: User session dictionary
        
        Returns:
            Updated low-confidence count
        """
        count = session.get("low_confidence_count", 0) + 1
        session["low_confidence_count"] = count
        return count
    
    @staticmethod
    def reset_low_confidence(session: dict):
        """
        Reset low-confidence counter (called on successful interaction).
        
        Args:
            session: User session dictionary
        """
        session["low_confidence_count"] = 0
    
    @staticmethod
    def get_clarification_prompt(tier: ConfidenceTier, intent: str, message: str, low_confidence_count: int) -> Optional[str]:
        """
        Generate appropriate clarification prompt based on confidence tier.
        
        Args:
            tier: Confidence tier
            intent: Classified intent
            message: Original user message
            low_confidence_count: Number of consecutive low-confidence turns
        
        Returns:
            Clarification prompt or None if no clarification needed
        """
        if tier == ConfidenceTier.LOW:
            return (
<<<<<<< HEAD
                f"I think you're asking about **{intent.replace('_', ' ')}**, but I'm not entirely sure.\n\n"
=======
                f"I think you are asking about {intent.replace('_', ' ')}, but I am not entirely sure.\n\n"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
                f"Could you please clarify or rephrase your request?\n\n"
                f"For example:\n"
                f"- 'Check my water bill'\n"
                f"- 'Report no water supply'\n"
                f"- 'Track my complaint'\n\n"
                f"Or type 'help' to see all options."
            )
        
        elif tier == ConfidenceTier.VERY_LOW:
            if low_confidence_count >= 2:
                return (
<<<<<<< HEAD
                    f"I'm having trouble understanding your request (attempt {low_confidence_count}/3).\n\n"
=======
                    f"I am having trouble understanding your request (attempt {low_confidence_count}/3).\n\n"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
                    f"Please try rephrasing, or I can connect you with a human agent.\n\n"
                    f"Type 'agent' to speak with someone, or 'help' to see what I can do."
                )
            else:
                return (
<<<<<<< HEAD
                    f"I didn't quite understand that. Could you please rephrase?\n\n"
                    f"Try being more specific, like:\n"
                    f"- 'I need to check my bill'\n"
                    f"- 'There's no water in my area'\n"
=======
                    f"I did not quite understand that. Could you please rephrase?\n\n"
                    f"Try being more specific, like:\n"
                    f"- 'I need to check my bill'\n"
                    f"- 'There is no water in my area'\n"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
                    f"- 'I want to track my complaint'\n\n"
                    f"Or type 'help' for options."
                )
        
        return None
    
    @staticmethod
    def get_escalation_message() -> str:
        """
        Get message for automatic escalation after repeated low confidence.
        
        Returns:
            Escalation message
        """
        return (
<<<<<<< HEAD
            "🤔 **I've tried my best to understand, but I'm still not sure how to help.**\n\n"
=======
            "I have tried my best to understand, but I am still not sure how to help.\n\n"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
            "Let me connect you with a human agent who can better assist you.\n\n"
            "This will help me learn to handle similar requests in the future."
        )
    
    @staticmethod
    def get_guided_menu() -> str:
        """
        Generate guided menu for low-confidence or repeated failures.
        
        Returns:
            Menu prompt
        """
        return (
<<<<<<< HEAD
            "I'm not sure what you need. Please choose:\n\n"
            "**Water Issues:**\n"
            "1️⃣ No water / Low pressure\n"
            "2️⃣ Leak or burst pipe\n"
            "3️⃣ Water quality problem\n\n"
            "**Billing & Payments:**\n"
            "4️⃣ Check my bill\n"
            "5️⃣ Payment methods\n\n"
            "**Other:**\n"
            "6️⃣ Track complaint (ticket number)\n"
            "7️⃣ New connection\n"
            "8️⃣ Office information\n"
            "9️⃣ Speak to agent\n\n"
=======
            "I am not sure what you need. Please choose:\n\n"
            "Water Issues:\n"
            "1. No water / Low pressure\n"
            "2. Leak or burst pipe\n"
            "3. Water quality problem\n\n"
            "Billing and Payments:\n"
            "4. Check my bill\n"
            "5. Payment methods\n\n"
            "Other:\n"
            "6. Track complaint (ticket number)\n"
            "7. New connection\n"
            "8. Office information\n"
            "9. Speak to agent\n\n"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
            "Reply with the number of your choice."
        )
    
    @staticmethod
<<<<<<< HEAD
    def handle_menu_selection(selection: str) -> Dict[str, any]:
=======
    def handle_menu_selection(selection: str) -> Dict[str, Any]:
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
        """
        Handle menu selection and map to intent.
        
        Args:
            selection: User's menu selection (1-9)
        
        Returns:
            Dict with mapped intent and confidence
        """
        menu_map = {
            "1": ("no_water_supply", 0.95),
            "2": ("burst_pipe_emergency", 0.95),
            "3": ("water_quality_issue", 0.95),
            "4": ("billing_inquiry", 0.95),
            "5": ("payment_methods_info", 0.95),
            "6": ("complaint_followup", 0.95),
            "7": ("new_connection_request", 0.95),
            "8": ("office_location_hours", 0.95),
            "9": ("human_escalation", 0.95),
        }
        
        if selection.strip() in menu_map:
            intent, confidence = menu_map[selection.strip()]
            return {
                "intent": intent,
                "confidence": confidence,
                "source": "menu_selection"
            }
        
        return {
            "intent": "general_faq",
            "confidence": 0.5,
            "source": "invalid_selection"
        }


class ConfidenceTracker:
    """Track confidence patterns for debugging and learning."""
    
    def __init__(self):
        """Initialize tracker."""
        self.classifications = []
        self.clarifications = []
        self.escalations = []
        self.menu_selections = []
    
    def record_classification(self, intent: str, confidence: float, tier: str):
        """Record a classification event."""
        self.classifications.append({
            'intent': intent,
            'confidence': confidence,
            'tier': tier
        })
    
    def record_clarification(self, original_intent: str, user_response: str, tier: str):
        """Record a clarification event."""
        self.clarifications.append({
            'original_intent': original_intent,
            'user_response': user_response,
            'tier': tier
        })
    
    def record_escalation(self, reason: str, low_confidence_count: int, last_intent: str):
        """Record an escalation event for learning."""
        self.escalations.append({
            'reason': reason,
            'low_confidence_count': low_confidence_count,
            'last_intent': last_intent
        })
    
    def record_menu_selection(self, selection: str, mapped_intent: str):
        """Record a menu selection."""
        self.menu_selections.append({
            'selection': selection,
            'mapped_intent': mapped_intent
        })
    
    def get_stats(self) -> Dict:
        """Get tracking statistics."""
        total_classifications = len(self.classifications)
        
        if total_classifications == 0:
            return {'total': 0}
        
        tiers = {}
        for c in self.classifications:
            tier = c['tier']
            tiers[tier] = tiers.get(tier, 0) + 1
        
        avg_confidence = sum(c['confidence'] for c in self.classifications) / total_classifications
        
        return {
            'total_classifications': total_classifications,
            'tiers': tiers,
            'avg_confidence': avg_confidence,
            'clarifications': len(self.clarifications),
            'escalations': len(self.escalations),
            'menu_selections': len(self.menu_selections)
        }


# Global tracker
confidence_tracker = ConfidenceTracker()
