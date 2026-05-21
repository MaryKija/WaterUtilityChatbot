"""backend/learning/confidence_learner.py

Confidence-based autonomy with adaptive thresholds.

This module implements adaptive confidence scoring that learns
from conversation outcomes to improve decision-making accuracy
and autonomy levels over time.
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


class AutonomyLevel(Enum):
    """Levels of system autonomy."""
    MANUAL = "manual"          # Always requires human confirmation
    CONSERVATIVE = "conservative"  # High confidence thresholds
    BALANCED = "balanced"      # Moderate confidence thresholds
    AGGRESSIVE = "aggressive"    # Low confidence thresholds
    FULL = "full"             # Maximum autonomy


@dataclass
class ConfidenceRecord:
    """Record of confidence prediction and actual outcome."""
    predicted_confidence: float
    actual_success: bool
    intent: str
    context_features: Dict[str, Any]
    timestamp: datetime
    user_feedback: Optional[Dict] = None


@dataclass
class AdaptiveThreshold:
    """Adaptive threshold configuration."""
    intent: str
    base_threshold: float
    current_threshold: float
    success_rate: float
    adjustment_factor: float
    last_updated: datetime


class ConfidenceLearner:
    """Adaptive confidence learning system for agentic behavior."""
    
    def __init__(self):
        self.autonomy_level = AutonomyLevel.BALANCED
        self.base_thresholds = {
            "leak_report": 0.7,
            "billing_inquiry": 0.8,
            "new_connection": 0.75,
            "complaint_followup": 0.7,
            "meter_problem": 0.8,
            "payment_info": 0.85,
            "office_info": 0.6,
            "general_chat": 0.5,
            "escalation": 0.9,
            "out_of_scope": 0.8
        }
        self.adaptive_thresholds: Dict[str, AdaptiveThreshold] = {}
        self.confidence_history: List[ConfidenceRecord] = []
        self.learning_rate = 0.1
        self.min_samples_for_learning = 10
        self.max_history_size = 1000
        
        # Initialize adaptive thresholds
        self._initialize_adaptive_thresholds()
    
    def _initialize_adaptive_thresholds(self) -> None:
        """Initialize adaptive thresholds from base thresholds."""
        for intent, threshold in self.base_thresholds.items():
            self.adaptive_thresholds[intent] = AdaptiveThreshold(
                intent=intent,
                base_threshold=threshold,
                current_threshold=threshold,
                success_rate=0.0,
                adjustment_factor=0.05,
                last_updated=datetime.now()
            )
    
    def get_adaptive_threshold(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Get adaptive confidence threshold for a specific intent."""
        if intent not in self.adaptive_thresholds:
            # Create new threshold for unknown intent
            base_threshold = self.base_thresholds.get("general_chat", 0.5)
            self.adaptive_thresholds[intent] = AdaptiveThreshold(
                intent=intent,
                base_threshold=base_threshold,
                current_threshold=base_threshold,
                success_rate=0.0,
                adjustment_factor=0.05,
                last_updated=datetime.now()
            )
        
        threshold = self.adaptive_thresholds[intent].current_threshold
        
        # Apply autonomy level adjustments
        threshold = self._apply_autonomy_adjustment(threshold, context)
        
        return threshold
    
    def _apply_autonomy_adjustment(self, threshold: float, context: Optional[Dict[str, Any]] = None) -> float:
        """Apply autonomy level adjustments to threshold."""
        if not context:
            return threshold
        
        adjustments = {
            AutonomyLevel.MANUAL: 0.3,      # Much higher threshold
            AutonomyLevel.CONSERVATIVE: 0.1,  # Higher threshold
            AutonomyLevel.BALANCED: 0.0,      # No adjustment
            AutonomyLevel.AGGRESSIVE: -0.1,    # Lower threshold
            AutonomyLevel.FULL: -0.2          # Much lower threshold
        }
        
        adjustment = adjustments.get(self.autonomy_level, 0.0)
        
        # Context-specific adjustments
        if context.get("user_satisfaction_score", 0.5) > 0.8:
            adjustment -= 0.05  # Lower threshold for satisfied users
        elif context.get("user_satisfaction_score", 0.5) < 0.3:
            adjustment += 0.05  # Higher threshold for dissatisfied users
        
        if context.get("session_duration", 0) > 30:  # Long session
            adjustment -= 0.03  # Slightly lower threshold
        
        return max(0.1, min(0.95, threshold + adjustment))
    
    def should_be_autonomous(self, confidence: float, intent: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if the system should act autonomously based on confidence."""
        threshold = self.get_adaptive_threshold(intent, context)
        
        # Additional autonomy checks
        if confidence < threshold:
            return False
        
        # High-risk intents require higher confidence
        high_risk_intents = ["escalation", "new_connection", "payment_info"]
        if intent in high_risk_intents and confidence < 0.8:
            return False
        
        # User history considerations
        if context and context.get("previous_success_rate", 1.0) < 0.6:
            return False  # Low success rate with this user
        
        return True
    
    def record_confidence_outcome(self, intent: str, predicted_confidence: float, 
                                actual_success: bool, context: Optional[Dict[str, Any]] = None,
                                user_feedback: Optional[Dict] = None) -> None:
        """Record confidence prediction outcome for learning."""
        record = ConfidenceRecord(
            predicted_confidence=predicted_confidence,
            actual_success=actual_success,
            intent=intent,
            context_features=context or {},
            timestamp=datetime.now(),
            user_feedback=user_feedback
        )
        
        self.confidence_history.append(record)
        
        # Maintain history size
        if len(self.confidence_history) > self.max_history_size:
            self.confidence_history = self.confidence_history[-self.max_history_size // 2:]
        
        # Update adaptive thresholds
        self._update_adaptive_threshold(intent)
        
        # Adjust autonomy level if needed
        self._adjust_autonomy_level()
        
        logger.info(f"Recorded confidence outcome: intent={intent}, predicted={predicted_confidence:.2f}, actual={actual_success}")
    
    def _update_adaptive_threshold(self, intent: str) -> None:
        """Update adaptive threshold based on recent outcomes."""
        if intent not in self.adaptive_thresholds:
            return
        
        # Get recent records for this intent
        recent_records = [
            record for record in self.confidence_history[-50:]  # Last 50 records
            if record.intent == intent
        ]
        
        if len(recent_records) < self.min_samples_for_learning:
            return  # Not enough data to update
        
        # Calculate success rate at different confidence levels
        confidence_ranges = [
            (0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)
        ]
        
        best_threshold = self.adaptive_thresholds[intent].base_threshold
        best_success_rate = 0.0
        
        for low, high in confidence_ranges:
            range_records = [r for r in recent_records if low <= r.predicted_confidence < high]
            if len(range_records) >= 5:  # Minimum samples for reliable estimate
                success_rate = sum(1 for r in range_records if r.actual_success) / len(range_records)
                
                # Find the lowest confidence level with good success rate
                if success_rate >= 0.8 and success_rate > best_success_rate:
                    best_success_rate = success_rate
                    best_threshold = low + 0.05  # Slightly above the lower bound
        
        # Update threshold with smoothing
        current_threshold = self.adaptive_thresholds[intent].current_threshold
        new_threshold = current_threshold * (1 - self.learning_rate) + best_threshold * self.learning_rate
        
        self.adaptive_thresholds[intent].current_threshold = new_threshold
        self.adaptive_thresholds[intent].success_rate = best_success_rate
        self.adaptive_thresholds[intent].last_updated = datetime.now()
        
        logger.info(f"Updated threshold for {intent}: {current_threshold:.2f} -> {new_threshold:.2f} (success_rate: {best_success_rate:.2f})")
    
    def _adjust_autonomy_level(self) -> None:
        """Adjust autonomy level based on overall performance."""
        if len(self.confidence_history) < 50:
            return  # Not enough data
        
        # Calculate overall performance metrics
        recent_records = self.confidence_history[-100:]
        overall_success_rate = sum(1 for r in recent_records if r.actual_success) / len(recent_records)
        average_confidence = sum(r.predicted_confidence for r in recent_records) / len(recent_records)
        
        # Calculate confidence calibration (how well predicted confidence matches actual success)
        calibration_error = 0.0
        for record in recent_records:
            calibration_error += abs(record.predicted_confidence - (1.0 if record.actual_success else 0.0))
        calibration_error /= len(recent_records)
        
        # Adjust autonomy based on performance
        current_level = self.autonomy_level
        
        if overall_success_rate > 0.9 and calibration_error < 0.2:
            # High performance and good calibration - can be more autonomous
            if current_level == AutonomyLevel.MANUAL:
                self.autonomy_level = AutonomyLevel.CONSERVATIVE
            elif current_level == AutonomyLevel.CONSERVATIVE:
                self.autonomy_level = AutonomyLevel.BALANCED
            elif current_level == AutonomyLevel.BALANCED:
                self.autonomy_level = AutonomyLevel.AGGRESSIVE
            elif current_level == AutonomyLevel.AGGRESSIVE:
                self.autonomy_level = AutonomyLevel.FULL
        
        elif overall_success_rate < 0.6 or calibration_error > 0.4:
            # Low performance or poor calibration - be more conservative
            if current_level == AutonomyLevel.FULL:
                self.autonomy_level = AutonomyLevel.AGGRESSIVE
            elif current_level == AutonomyLevel.AGGRESSIVE:
                self.autonomy_level = AutonomyLevel.BALANCED
            elif current_level == AutonomyLevel.BALANCED:
                self.autonomy_level = AutonomyLevel.CONSERVATIVE
            elif current_level == AutonomyLevel.CONSERVATIVE:
                self.autonomy_level = AutonomyLevel.MANUAL
        
        if self.autonomy_level != current_level:
            logger.info(f"Adjusted autonomy level: {current_level.value} -> {self.autonomy_level.value}")
    
    def predict_confidence(self, intent: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Predict confidence for a given intent and context."""
        # Base confidence on historical performance
        if intent in self.adaptive_thresholds:
            base_confidence = 1.0 - self.adaptive_thresholds[intent].current_threshold
        else:
            base_confidence = 0.5
        
        # Context adjustments
        if context:
            # User satisfaction adjustment
            satisfaction = context.get("user_satisfaction_score", 0.5)
            base_confidence *= (0.8 + 0.4 * satisfaction)  # Scale between 0.8 and 1.2
            
            # Session duration adjustment
            duration = context.get("session_duration", 0)
            if duration > 20:  # Long session - user is engaged
                base_confidence *= 1.1
            elif duration < 2:  # Very short session - might be confused
                base_confidence *= 0.9
            
            # Previous success rate
            prev_success = context.get("previous_success_rate", 1.0)
            base_confidence *= (0.7 + 0.3 * prev_success)
        
        return max(0.1, min(0.95, base_confidence))
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics and performance metrics."""
        if not self.confidence_history:
            return {
                "total_records": 0,
                "autonomy_level": self.autonomy_level.value,
                "adaptive_thresholds": len(self.adaptive_thresholds)
            }
        
        recent_records = self.confidence_history[-100:]
        
        stats = {
            "total_records": len(self.confidence_history),
            "recent_records": len(recent_records),
            "autonomy_level": self.autonomy_level.value,
            "overall_success_rate": sum(1 for r in recent_records if r.actual_success) / len(recent_records),
            "average_confidence": sum(r.predicted_confidence for r in recent_records) / len(recent_records),
            "calibration_error": self._calculate_calibration_error(recent_records),
            "adaptive_thresholds": {},
            "intent_performance": {}
        }
        
        # Adaptive thresholds
        for intent, threshold in self.adaptive_thresholds.items():
            stats["adaptive_thresholds"][intent] = {
                "current": threshold.current_threshold,
                "base": threshold.base_threshold,
                "success_rate": threshold.success_rate
            }
        
        # Intent-specific performance
        intent_stats = {}
        for intent in set(r.intent for r in recent_records):
            intent_records = [r for r in recent_records if r.intent == intent]
            if intent_records:
                intent_stats[intent] = {
                    "success_rate": sum(1 for r in intent_records if r.actual_success) / len(intent_records),
                    "avg_confidence": sum(r.predicted_confidence for r in intent_records) / len(intent_records),
                    "record_count": len(intent_records)
                }
        
        stats["intent_performance"] = intent_stats
        
        return stats
    
    def _calculate_calibration_error(self, records: List[ConfidenceRecord]) -> float:
        """Calculate calibration error (how well confidence predictions match reality)."""
        if not records:
            return 0.0
        
        total_error = 0.0
        for record in records:
            predicted = record.predicted_confidence
            actual = 1.0 if record.actual_success else 0.0
            total_error += abs(predicted - actual)
        
        return total_error / len(records)
    
    def reset_learning(self, intent: Optional[str] = None) -> None:
        """Reset learning for specific intent or all intents."""
        if intent:
            # Reset specific intent
            if intent in self.adaptive_thresholds:
                self.adaptive_thresholds[intent].current_threshold = self.adaptive_thresholds[intent].base_threshold
                self.adaptive_thresholds[intent].success_rate = 0.0
                self.adaptive_thresholds[intent].last_updated = datetime.now()
            
            # Remove confidence history for this intent
            self.confidence_history = [r for r in self.confidence_history if r.intent != intent]
        else:
            # Reset all learning
            self._initialize_adaptive_thresholds()
            self.confidence_history = []
            self.autonomy_level = AutonomyLevel.BALANCED
        
        logger.info(f"Reset learning for: {intent or 'all intents'}")
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for backup or analysis."""
        return {
            "autonomy_level": self.autonomy_level.value,
            "adaptive_thresholds": {
                intent: {
                    "base_threshold": thresh.base_threshold,
                    "current_threshold": thresh.current_threshold,
                    "success_rate": thresh.success_rate,
                    "adjustment_factor": thresh.adjustment_factor,
                    "last_updated": thresh.last_updated.isoformat()
                }
                for intent, thresh in self.adaptive_thresholds.items()
            },
            "confidence_history": [
                {
                    "predicted_confidence": record.predicted_confidence,
                    "actual_success": record.actual_success,
                    "intent": record.intent,
                    "context_features": record.context_features,
                    "timestamp": record.timestamp.isoformat(),
                    "user_feedback": record.user_feedback
                }
                for record in self.confidence_history[-100:]  # Last 100 records
            ],
            "learning_rate": self.learning_rate,
            "export_timestamp": datetime.now().isoformat()
        }


# Global confidence learner instance
confidence_learner = ConfidenceLearner()
