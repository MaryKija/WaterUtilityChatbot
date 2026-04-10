"""backend/escalation_model.py

Behavioral escalation model with:
1. Context-aware escalation triggers
2. Confidence-based escalation thresholds
3. Conversation history analysis
4. User frustration detection
5. Escalation reason tracking
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from .logger import logger


class EscalationTrigger(Enum):
    """Types of escalation triggers."""
    LOW_CONFIDENCE = "low_confidence"           # <50% confidence
    REPEATED_FAILURE = "repeated_failure"       # Same intent failed multiple times
    USER_FRUSTRATION = "user_frustration"       # Negative sentiment detected
    OUT_OF_SCOPE = "out_of_scope"              # Intent not recognized
    TOOL_ERROR = "tool_error"                  # Tool execution failed
    EXPLICIT_REQUEST = "explicit_request"      # User explicitly requested agent
    TIMEOUT = "timeout"                        # Response took too long
    COMPLEX_ISSUE = "complex_issue"            # Multi-step issue
    USER_ANGER = "user_anger"                  # Strong negative sentiment


class EscalationLevel(Enum):
    """Escalation severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EscalationSignal:
    """Individual escalation signal with weight."""
    trigger: EscalationTrigger
    level: EscalationLevel
    weight: float
    explanation: str
    timestamp: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.context_data is None:
            self.context_data = {}


class BehavioralEscalationModel:
    """Context-aware escalation model for autonomous decision-making."""

    def __init__(self):
        self.trigger_weights = {
            EscalationTrigger.LOW_CONFIDENCE: 0.3,
            EscalationTrigger.REPEATED_FAILURE: 0.6,
            EscalationTrigger.USER_FRUSTRATION: 0.5,
            EscalationTrigger.OUT_OF_SCOPE: 0.4,
            EscalationTrigger.TOOL_ERROR: 0.7,
            EscalationTrigger.EXPLICIT_REQUEST: 1.0,  # Highest priority
            EscalationTrigger.TIMEOUT: 0.5,
            EscalationTrigger.COMPLEX_ISSUE: 0.4,
            EscalationTrigger.USER_ANGER: 0.8,
        }

        self.escalation_history: List[EscalationSignal] = []

    def evaluate_escalation(self, message: str, context: dict, confidence: float) -> dict:
        """
        Evaluate whether conversation should be escalated.
        
        Returns:
            {
                "should_escalate": bool,
                "escalation_score": float (0-1),
                "signals": list of EscalationSignal,
                "primary_reason": str,
                "severity": EscalationLevel
            }
        """
        signals = []

        # Signal 1: Low confidence
        if confidence < 0.5:
            signals.append(self._create_signal(
                EscalationTrigger.LOW_CONFIDENCE,
                EscalationLevel.MEDIUM if confidence > 0.3 else EscalationLevel.HIGH,
                f"Intent confidence very low: {confidence:.2f}"
            ))

        # Signal 2: Explicit escalation request
        if self._contains_escalation_keywords(message):
            signals.append(self._create_signal(
                EscalationTrigger.EXPLICIT_REQUEST,
                EscalationLevel.CRITICAL,
                "User explicitly requested to speak with agent"
            ))

        # Signal 3: Detected user frustration/anger
        frustration_level = self._detect_frustration(message)
        if frustration_level > 0.6:
            trigger = EscalationTrigger.USER_ANGER if frustration_level > 0.8 else EscalationTrigger.USER_FRUSTRATION
            signals.append(self._create_signal(
                trigger,
                EscalationLevel.HIGH if frustration_level > 0.8 else EscalationLevel.MEDIUM,
                f"Detected user frustration/anger (score: {frustration_level:.2f})"
            ))

        # Signal 4: Out of scope
        if context.get("intent") == "out_of_scope":
            signals.append(self._create_signal(
                EscalationTrigger.OUT_OF_SCOPE,
                EscalationLevel.MEDIUM,
                "Intent classified as out of scope"
            ))

        # Signal 5: Repeated failures
        failure_count = self._count_recent_failures(context)
        if failure_count > 2:
            signals.append(self._create_signal(
                EscalationTrigger.REPEATED_FAILURE,
                EscalationLevel.HIGH,
                f"User encountered {failure_count} failed attempts in last 5 turns"
            ))

        # Signal 6: Complex issue detection
        if self._is_complex_issue(message, context):
            signals.append(self._create_signal(
                EscalationTrigger.COMPLEX_ISSUE,
                EscalationLevel.MEDIUM,
                "Issue appears to require multi-step resolution"
            ))

        # Calculate escalation score
        escalation_score = self._calculate_escalation_score(signals)

        # Determine if escalation is needed
        should_escalate = escalation_score > 0.6 or any(
            s.trigger == EscalationTrigger.EXPLICIT_REQUEST for s in signals
        )

        # Determine severity
        if signals:
            max_level = max((s.level.value for s in signals), default=EscalationLevel.LOW.value)
            severity = EscalationLevel(max_level)
        else:
            severity = EscalationLevel.LOW

        # Determine primary reason
        if signals:
            primary_signal = max(signals, key=lambda s: s.weight * s.level.value)
            primary_reason = primary_signal.explanation
        else:
            primary_reason = "No escalation signals detected"

        result = {
            "should_escalate": should_escalate,
            "escalation_score": escalation_score,
            "signals": [self._signal_to_dict(s) for s in signals],
            "primary_reason": primary_reason,
            "severity": severity.name,
            "signal_count": len(signals),
        }

        # Log if escalating
        if should_escalate:
            self._log_escalation(result, message, context)
            self.escalation_history.extend(signals)

        return result

    def _create_signal(self, trigger: EscalationTrigger, level: EscalationLevel, explanation: str) -> EscalationSignal:
        """Create an escalation signal."""
        return EscalationSignal(
            trigger=trigger,
            level=level,
            weight=self.trigger_weights.get(trigger, 0.5),
            explanation=explanation
        )

    def _contains_escalation_keywords(self, message: str) -> bool:
        """Detect if user is explicitly asking for escalation."""
        escalation_phrases = [
            "speak to", "talk to", "connect me", "transfer me",
            "agent", "human", "representative", "supervisor", "manager",
            "please help", "frustrated", "angry", "upset"
        ]
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in escalation_phrases)

    def _detect_frustration(self, message: str) -> float:
        """
        Detect frustration/anger in message.
        Returns score 0-1 (0=calm, 1=very angry)
        """
        message_lower = message.lower()

        # Negative indicators
        negative_words = {
            "angry": 0.9, "frustrated": 0.85, "upset": 0.8,
            "terrible": 0.85, "horrible": 0.85, "worse": 0.7,
            "don't": 0.3, "not": 0.2, "no": 0.1, "problem": 0.4,
            "issue": 0.4, "complaint": 0.5, "broken": 0.7,
        }

        frustration_score = 0.0
        detected_words = []

        for word, score in negative_words.items():
            if word in message_lower:
                frustration_score += score
                detected_words.append(word)

        # Penalize for ALL CAPS
        if message.isupper() and len(message) > 3:
            frustration_score += 0.2

        # Penalize for multiple punctuation marks
        exclamation_count = message.count("!")
        if exclamation_count > 2:
            frustration_score += 0.1 * exclamation_count

        # Normalize to 0-1
        frustration_score = min(1.0, frustration_score / len(detected_words) if detected_words else frustration_score)

        if detected_words:
            logger.debug(f"Frustration detection: detected {detected_words}, score={frustration_score:.2f}")

        return frustration_score

    def _count_recent_failures(self, context: dict) -> int:
        """Count failed responses in recent conversation history."""
        history = context.get("conversation_history", [])
        recent_history = history[-5:] if len(history) > 5 else history

        failure_count = 0
        for turn in recent_history:
            # Check if bot's response was unhelpful
            if turn.get("role") == "bot":
                response = turn.get("text", "").lower()
                unhelpful_indicators = [
                    "i don't know", "i'm not sure", "unclear", "didn't understand",
                    "out of scope", "can't help"
                ]
                if any(indicator in response for indicator in unhelpful_indicators):
                    failure_count += 1

        return failure_count

    def _is_complex_issue(self, message: str, context: dict) -> bool:
        """Detect if issue is complex and requires multiple steps."""
        message_lower = message.lower()

        # Multi-part indicators
        multi_part_keywords = ["and", "also", "additionally", ","]
        has_multiple_parts = sum(1 for kw in multi_part_keywords if kw in message_lower) >= 2

        # Complex issue types
        complex_issuespatterns = [
            "billing.*leak",  # Multiple issues
            "no water.*fault",
            "multiple problems",
        ]

        import re
        has_complex_pattern = any(
            re.search(pattern, message_lower) for pattern in complex_issuespatterns
        )

        return has_multiple_parts or has_complex_pattern

    def _calculate_escalation_score(self, signals: List[EscalationSignal]) -> float:
        """Calculate overall escalation probability (0-1)."""
        if not signals:
            return 0.0

        # Weighted sum of signals
        total_weight = 0.0
        for signal in signals:
            # Weight is multiplied by escalation level (1-4)
            weighted_contribution = signal.weight * (signal.level.value / 4.0)
            total_weight += weighted_contribution

        # Normalize: average weight across signals
        escalation_score = total_weight / len(signals) if signals else 0.0

        return min(1.0, escalation_score)  # Cap at 1.0

    def _signal_to_dict(self, signal: EscalationSignal) -> dict:
        """Convert signal to dictionary."""
        return {
            "trigger": signal.trigger.value,
            "level": signal.level.name,
            "weight": signal.weight,
            "explanation": signal.explanation,
            "timestamp": signal.timestamp,
        }

    def _log_escalation(self, result: dict, message: str, context: dict):
        """Log escalation event for analysis."""
        logger.warning(
            f"ESCALATION TRIGGERED - Score: {result['escalation_score']:.2f}, "
            f"Reason: {result['primary_reason']}, "
            f"Message: '{message[:50]}...'"
        )

    def get_escalation_stats(self) -> dict:
        """Get escalation statistics."""
        if not self.escalation_history:
            return {
                "total_escalations": 0,
                "escalation_triggers": {},
                "most_common_trigger": None,
                "avg_score": 0.0,
            }

        triggers = {}
        for signal in self.escalation_history:
            trigger_name = signal.trigger.value
            triggers[trigger_name] = triggers.get(trigger_name, 0) + 1

        return {
            "total_escalations": len(self.escalation_history),
            "escalation_triggers": triggers,
            "most_common_trigger": max(triggers, key=lambda k: triggers[k]) if triggers else None,
            "avg_weight": sum(s.weight for s in self.escalation_history) / len(self.escalation_history),
        }


# Global escalation model instance
escalation_model = BehavioralEscalationModel()
