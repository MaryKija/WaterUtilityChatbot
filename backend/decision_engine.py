"""backend/decision_engine.py

Contextual decision trees for agentic behavior.

This module implements dynamic decision-making capabilities that allow
the system to choose optimal response strategies based on context,
user history, and real-time factors.
"""

from __future__ import annotations

import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import sqlite3
from datetime import datetime, timedelta

from backend.config import config
from backend.logger import logger
from backend.intents import ALLOWED_INTENTS


class DecisionStrategy(Enum):
    """Decision-making strategies for agentic behavior."""
    CONSERVATIVE = "conservative"  # Stick to known patterns
    BALANCED = "balanced"        # Mix of known and experimental
    AGGRESSIVE = "aggressive"    # Try new approaches frequently
    LEARNED = "learned"          # Use historical success data


@dataclass
class DecisionOption:
    """Represents a possible decision with associated metadata."""
    action: str
    confidence: float
    expected_outcome: str
    risk_level: float
    success_probability: float
    context_requirements: List[str]


@dataclass
class DecisionContext:
    """Context information for decision making."""
    user_id: str
    intent: str
    entities: Dict[str, Any]
    conversation_history: List[Dict]
    previous_decisions: List[Dict]
    user_satisfaction_score: float
    session_duration: float


class DecisionEngine:
    """Agentic decision-making engine with contextual awareness."""
    
    def __init__(self):
        self.strategy = DecisionStrategy.BALANCED
        self.min_confidence_threshold = 0.6
        self.risk_tolerance = 0.3
        self.learning_rate = 0.1
        self.decision_history = []
        self.success_patterns = {}
        
    def make_decision(self, context: DecisionContext) -> DecisionOption:
        """Make an autonomous decision based on context."""
        try:
            # Generate possible decision options
            options = self._generate_options(context)
            
            # Evaluate each option
            evaluated_options = []
            for option in options:
                score = self._evaluate_option(option, context)
                evaluated_options.append((option, score))
            
            # Sort by score and select best option
            evaluated_options.sort(key=lambda x: x[1], reverse=True)
            
            # Apply strategy-specific selection
            selected_option = self._select_option(evaluated_options, context)
            
            # Log decision for learning
            self._log_decision(selected_option, context)
            
            logger.info(f"Agentic decision: {selected_option.action} (confidence: {selected_option.confidence:.2f})")
            return selected_option
            
        except Exception as e:
            logger.error(f"Error in decision making: {e}")
            # Fallback to conservative option
            return self._get_fallback_option(context)
    
    def _generate_options(self, context: DecisionContext) -> List[DecisionOption]:
        """Generate possible decision options based on context."""
        options = []
        intent = context.intent
        
        if intent == "leak_report":
            options.extend([
                DecisionOption(
                    action="collect_name_first",
                    confidence=0.8,
                    expected_outcome="Get user identity for complaint logging",
                    risk_level=0.1,
                    success_probability=0.9,
                    context_requirements=["conversation_active"]
                ),
                DecisionOption(
                    action="collect_location_first",
                    confidence=0.7,
                    expected_outcome="Get location for immediate assessment",
                    risk_level=0.2,
                    success_probability=0.8,
                    context_requirements=["conversation_active"]
                ),
                DecisionOption(
                    action="escalate_immediately",
                    confidence=0.4,
                    expected_outcome="Fast human intervention for urgent leaks",
                    risk_level=0.6,
                    success_probability=0.7,
                    context_requirements=["high_urgency_indicators"]
                )
            ])
        
        elif intent == "billing_inquiry":
            options.extend([
                DecisionOption(
                    action="request_account_number",
                    confidence=0.9,
                    expected_outcome="Access specific billing information",
                    risk_level=0.1,
                    success_probability=0.85,
                    context_requirements=["conversation_active"]
                ),
                DecisionOption(
                    action="provide_general_billing_info",
                    confidence=0.7,
                    expected_outcome="Answer general billing questions",
                    risk_level=0.2,
                    success_probability=0.8,
                    context_requirements=["conversation_active"]
                ),
                DecisionOption(
                    action="offer_payment_assistance",
                    confidence=0.5,
                    expected_outcome="Help with payment options",
                    risk_level=0.3,
                    success_probability=0.75,
                    context_requirements=["financial_indicators"]
                )
            ])
        
        elif intent == "general_chat":
            options.extend([
                DecisionOption(
                    action="provide_help_menu",
                    confidence=0.8,
                    expected_outcome="Guide user to available services",
                    risk_level=0.1,
                    success_probability=0.9,
                    context_requirements=["conversation_active"]
                ),
                DecisionOption(
                    action="engage_small_talk",
                    confidence=0.6,
                    expected_outcome="Build rapport with user",
                    risk_level=0.2,
                    success_probability=0.7,
                    context_requirements=["positive_sentiment"]
                ),
                DecisionOption(
                    action="direct_to_specific_service",
                    confidence=0.4,
                    expected_outcome="Quickly address user needs",
                    risk_level=0.3,
                    success_probability=0.6,
                    context_requirements=["clear_intent_indicators"]
                )
            ])
        
        # Add experimental options for agentic behavior
        if self.strategy in [DecisionStrategy.AGGRESSIVE, DecisionStrategy.LEARNED]:
            options.extend(self._generate_experimental_options(context))
        
        return options
    
    def _generate_experimental_options(self, context: DecisionContext) -> List[DecisionOption]:
        """Generate experimental options for agentic exploration."""
        options = []
        
        # Proactive assistance option
        if len(context.conversation_history) > 3:
            options.append(DecisionOption(
                action="proactive_assistance",
                confidence=0.5,
                expected_outcome="Anticipate user needs based on patterns",
                risk_level=0.4,
                success_probability=0.6,
                context_requirements=["sufficient_history", "pattern_detected"]
            ))
        
        # Multi-step problem solving
        if context.entities.get("complexity_score", 0) > 0.7:
            options.append(DecisionOption(
                action="complex_problem_solving",
                confidence=0.6,
                expected_outcome="Break down complex issues into steps",
                risk_level=0.3,
                success_probability=0.7,
                context_requirements=["high_complexity", "user_cooperation"]
            ))
        
        return options
    
    def _evaluate_option(self, option: DecisionOption, context: DecisionContext) -> float:
        """Evaluate a decision option based on multiple factors."""
        score = 0.0
        
        # Base confidence score
        score += option.confidence * 0.3
        
        # Success probability
        score += option.success_probability * 0.3
        
        # Risk assessment (lower risk = higher score for conservative strategies)
        if self.strategy == DecisionStrategy.CONSERVATIVE:
            score += (1.0 - option.risk_level) * 0.3
        elif self.strategy == DecisionStrategy.AGGRESSIVE:
            score += option.risk_level * 0.2  # Some risk tolerance
        else:  # BALANCED
            score += (1.0 - option.risk_level * 0.5) * 0.25
        
        # Context match
        context_match = self._calculate_context_match(option, context)
        score += context_match * 0.1
        
        # Learning from past successes
        if option.action in self.success_patterns:
            success_rate = self.success_patterns[option.action]
            score += success_rate * 0.1
        
        return min(score, 1.0)
    
    def _calculate_context_match(self, option: DecisionOption, context: DecisionContext) -> float:
        """Calculate how well the option matches current context."""
        if not option.context_requirements:
            return 0.5  # Neutral for options with no requirements
        
        matches = 0
        total_requirements = len(option.context_requirements)
        
        for requirement in option.context_requirements:
            if self._check_context_requirement(requirement, context):
                matches += 1
        
        return matches / total_requirements if total_requirements > 0 else 0.5
    
    def _check_context_requirement(self, requirement: str, context: DecisionContext) -> bool:
        """Check if a specific context requirement is met."""
        if requirement == "conversation_active":
            return len(context.conversation_history) < 20  # Reasonable length
        
        elif requirement == "high_urgency_indicators":
            message_text = " ".join([msg.get("content", "") for msg in context.conversation_history[-3:]])
            urgent_words = ["urgent", "emergency", "immediately", "asap", "right now"]
            return any(word in message_text.lower() for word in urgent_words)
        
        elif requirement == "financial_indicators":
            message_text = " ".join([msg.get("content", "") for msg in context.conversation_history[-3:]])
            financial_words = ["pay", "bill", "cost", "afford", "money"]
            return any(word in message_text.lower() for word in financial_words)
        
        elif requirement == "sufficient_history":
            return len(context.conversation_history) >= 5
        
        elif requirement == "pattern_detected":
            # Simple pattern detection - could be enhanced with ML
            return len(context.conversation_history) >= 3
        
        elif requirement == "high_complexity":
            return context.entities.get("complexity_score", 0) > 0.7
        
        elif requirement == "user_cooperation":
            # Check if user has been providing information
            recent_responses = [msg for msg in context.conversation_history[-5:] if msg.get("role") == "user"]
            return len(recent_responses) >= 2
        
        elif requirement == "positive_sentiment":
            # Simple sentiment check - could be enhanced with NLP
            message_text = " ".join([msg.get("content", "") for msg in context.conversation_history[-3:]])
            positive_words = ["thanks", "good", "great", "ok", "yes"]
            return any(word in message_text.lower() for word in positive_words)
        
        elif requirement == "clear_intent_indicators":
            message_text = context.conversation_history[-1].get("content", "") if context.conversation_history else ""
            return len(message_text.split()) > 5  # User provided detailed message
        
        return False
    
    def _select_option(self, evaluated_options: List[Tuple[DecisionOption, float]], context: DecisionContext) -> DecisionOption:
        """Select the best option based on strategy."""
        if not evaluated_options:
            return self._get_fallback_option(context)
        
        best_option, best_score = evaluated_options[0]
        
        # Apply strategy-specific selection logic
        if self.strategy == DecisionStrategy.CONSERVATIVE:
            # Only select options with high confidence and low risk
            if best_option.confidence < self.min_confidence_threshold or best_option.risk_level > self.risk_tolerance:
                return self._get_fallback_option(context)
        
        elif self.strategy == DecisionStrategy.AGGRESSIVE:
            # Consider experimental options more readily
            if best_score > 0.5:  # Lower threshold for aggressive strategy
                return best_option
        
        elif self.strategy == DecisionStrategy.LEARNED:
            # Prioritize options with proven success
            learned_options = [(opt, score) for opt, score in evaluated_options 
                             if opt.action in self.success_patterns and self.success_patterns[opt.action] > 0.8]
            if learned_options:
                return learned_options[0][0]
        
        # Default: return best option if it meets minimum threshold
        if best_score >= self.min_confidence_threshold:
            return best_option
        
        return self._get_fallback_option(context)
    
    def _get_fallback_option(self, context: DecisionContext) -> DecisionOption:
        """Get a safe fallback option."""
        return DecisionOption(
            action="standard_response",
            confidence=0.5,
            expected_outcome="Provide standard utility response",
            risk_level=0.1,
            success_probability=0.8,
            context_requirements=[]
        )
    
    def _log_decision(self, option: DecisionOption, context: DecisionContext) -> None:
        """Log decision for learning and analytics."""
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": context.user_id,
            "intent": context.intent,
            "action": option.action,
            "confidence": option.confidence,
            "risk_level": option.risk_level,
            "strategy": self.strategy.value
        }
        
        self.decision_history.append(decision_record)
        
        # Keep history manageable
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-500:]
    
    def learn_from_outcome(self, decision_action: str, success: bool, user_feedback: Optional[Dict] = None) -> None:
        """Learn from decision outcomes for future improvement."""
        if decision_action not in self.success_patterns:
            self.success_patterns[decision_action] = []
        
        # Record outcome
        outcome = {
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "feedback": user_feedback or {}
        }
        
        self.success_patterns[decision_action].append(outcome)
        
        # Calculate success rate
        recent_outcomes = self.success_patterns[decision_action][-20:]  # Last 20 outcomes
        success_rate = sum(1 for o in recent_outcomes if o["success"]) / len(recent_outcomes)
        
        # Update success patterns
        self.success_patterns[decision_action] = success_rate
        
        # Adjust strategy based on overall performance
        self._adjust_strategy()
        
        logger.info(f"Learned from decision '{decision_action}': success_rate={success_rate:.2f}")
    
    def _adjust_strategy(self) -> None:
        """Adjust decision strategy based on overall performance."""
        if len(self.success_patterns) < 5:
            return  # Not enough data to adjust
        
        # Calculate overall success rate
        overall_success = np.mean(list(self.success_patterns.values()))
        
        # Adjust strategy based on performance
        if overall_success > 0.85:
            # High success - can be more aggressive
            if self.strategy == DecisionStrategy.CONSERVATIVE:
                self.strategy = DecisionStrategy.BALANCED
            elif self.strategy == DecisionStrategy.BALANCED:
                self.strategy = DecisionStrategy.AGGRESSIVE
        
        elif overall_success < 0.6:
            # Low success - be more conservative
            if self.strategy == DecisionStrategy.AGGRESSIVE:
                self.strategy = DecisionStrategy.BALANCED
            elif self.strategy == DecisionStrategy.BALANCED:
                self.strategy = DecisionStrategy.CONSERVATIVE
        
        logger.info(f"Adjusted strategy to {self.strategy.value} based on success rate {overall_success:.2f}")
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """Get statistics about decision making."""
        if not self.decision_history:
            return {"total_decisions": 0}
        
        recent_decisions = self.decision_history[-100:]  # Last 100 decisions
        
        stats = {
            "total_decisions": len(self.decision_history),
            "recent_decisions": len(recent_decisions),
            "strategy": self.strategy.value,
            "success_patterns": dict(self.success_patterns),
            "action_distribution": {},
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0}
        }
        
        # Calculate action distribution
        for decision in recent_decisions:
            action = decision["action"]
            stats["action_distribution"][action] = stats["action_distribution"].get(action, 0) + 1
        
        # Calculate confidence distribution
        for decision in recent_decisions:
            confidence = decision["confidence"]
            if confidence >= 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif confidence >= 0.5:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
        
        return stats


# Global decision engine instance
decision_engine = DecisionEngine()
