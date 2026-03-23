"""
Conversation Context Manager

Maintains conversation context across multiple turns to enable:
- Multi-turn understanding
- Context-aware responses
- Fallback prevention
- Entity persistence
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta


class ConversationContext:
    """Manages conversation state and context."""
    
    def __init__(self, phone: str, ttl_minutes: int = 30):
        """
        Initialize conversation context.
        
        Args:
            phone: User phone number
            ttl_minutes: Context time-to-live in minutes
        """
        self.phone = phone
        self.created_at = datetime.now()
        self.ttl = timedelta(minutes=ttl_minutes)
        
        # Conversation history
        self.messages = []  # List of (role, message, intent, confidence)
        
        # Current state
        self.current_intent = None
        self.current_confidence = 0.0
        self.current_entities = {}
        
        # Previous state (for context)
        self.previous_intent = None
        self.previous_entities = {}
        
        # Flow state
        self.active_flow = None
        self.flow_step = 0
        self.pending_action = None
        
        # Fallback tracking
        self.fallback_count = 0
        self.last_fallback_time = None
        
        # Entity accumulation
        self.accumulated_entities = {}
    
    def is_expired(self) -> bool:
        """Check if context has expired."""
        return datetime.now() - self.created_at > self.ttl
    
    def add_message(self, role: str, message: str, intent: Optional[str] = None, 
                   confidence: float = 0.0, entities: Optional[Dict] = None):
        """
        Add a message to conversation history.
        
        Args:
            role: "user" or "bot"
            message: Message text
            intent: Detected intent (for user messages)
            confidence: Intent confidence score
            entities: Extracted entities
        """
        self.messages.append({
            'timestamp': datetime.now().isoformat(),
            'role': role,
            'message': message,
            'intent': intent,
            'confidence': confidence,
            'entities': entities or {}
        })
    
    def update_intent(self, intent: str, confidence: float, entities: Optional[Dict] = None):
        """
        Update current intent and entities.
        
        Args:
            intent: New intent
            confidence: Confidence score
            entities: Extracted entities
        """
        # Save previous state
        self.previous_intent = self.current_intent
        self.previous_entities = self.current_entities.copy()
        
        # Update current state
        self.current_intent = intent
        self.current_confidence = confidence
        self.current_entities = entities or {}
        
        # Accumulate entities
        if entities:
            self.accumulated_entities.update(entities)
    
    def set_flow(self, flow_type: str, step: int = 0):
        """
        Set active conversation flow.
        
        Args:
            flow_type: Type of flow (complaint, billing, followup, etc.)
            step: Current step in flow
        """
        self.active_flow = flow_type
        self.flow_step = step
        self.fallback_count = 0  # Reset fallback counter on new flow
    
    def advance_flow(self):
        """Advance to next step in flow."""
        self.flow_step += 1
    
    def clear_flow(self):
        """Clear active flow."""
        self.active_flow = None
        self.flow_step = 0
        self.pending_action = None
    
    def record_fallback(self):
        """Record a fallback event."""
        self.fallback_count += 1
        self.last_fallback_time = datetime.now()
    
    def should_show_menu(self) -> bool:
        """
        Determine if guided menu should be shown.
        
        Returns True if:
        - 2+ consecutive fallbacks
        - Low confidence classification
        """
        return self.fallback_count >= 2
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context."""
        return {
            'phone': self.phone,
            'current_intent': self.current_intent,
            'confidence': self.current_confidence,
            'active_flow': self.active_flow,
            'flow_step': self.flow_step,
            'fallback_count': self.fallback_count,
            'accumulated_entities': self.accumulated_entities,
            'message_count': len(self.messages),
            'is_expired': self.is_expired()
        }
    
    def get_recent_context(self, n: int = 3) -> str:
        """
        Get recent conversation context as string.
        
        Args:
            n: Number of recent messages to include
        
        Returns:
            Formatted context string for LLM
        """
        recent = self.messages[-n:] if len(self.messages) > 0 else []
        
        context_lines = []
        for msg in recent:
            role = "User" if msg['role'] == "user" else "Bot"
            context_lines.append(f"{role}: {msg['message']}")
        
        return "\n".join(context_lines)
    
    def clear(self):
        """Clear all context."""
        self.messages = []
        self.current_intent = None
        self.current_confidence = 0.0
        self.current_entities = {}
        self.previous_intent = None
        self.previous_entities = {}
        self.active_flow = None
        self.flow_step = 0
        self.pending_action = None
        self.fallback_count = 0
        self.accumulated_entities = {}


class ContextManager:
    """Manages contexts for multiple users."""
    
    def __init__(self):
        """Initialize context manager."""
        self.contexts: Dict[str, ConversationContext] = {}
    
    def get_context(self, phone: str) -> ConversationContext:
        """
        Get or create context for user.
        
        Args:
            phone: User phone number
        
        Returns:
            ConversationContext for user
        """
        if phone not in self.contexts:
            self.contexts[phone] = ConversationContext(phone)
        
        context = self.contexts[phone]
        
        # Check if expired
        if context.is_expired():
            context.clear()
        
        return context
    
    def clear_context(self, phone: str):
        """Clear context for user."""
        if phone in self.contexts:
            self.contexts[phone].clear()
    
    def cleanup_expired(self):
        """Remove expired contexts."""
        expired = [
            phone for phone, ctx in self.contexts.items()
            if ctx.is_expired()
        ]
        for phone in expired:
            del self.contexts[phone]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            'active_contexts': len(self.contexts),
            'total_messages': sum(len(ctx.messages) for ctx in self.contexts.values()),
            'active_flows': sum(1 for ctx in self.contexts.values() if ctx.active_flow)
        }


# Global context manager
context_manager = ContextManager()
