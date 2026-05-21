"""backend/metrics_collector.py

Real-time metrics collection for conversation evaluation.

This module automatically tracks:
- Response times
- Turn counts
- Resolution rates
- Escalation rates
- Failed intent rates
- Session completion metrics
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .logger import logger
from .storage import create_session_metrics, SessionMetrics


@dataclass
class SessionTracker:
    """Tracks metrics for an active conversation session."""
    session_id: str
    user_id: str
    start_time: float
    turn_count: int = 0
    response_times: List[float] = field(default_factory=list)
    intents: List[str] = field(default_factory=list)
    confidences: List[float] = field(default_factory=list)
    failed_intents: int = 0
    escalated: bool = False
    resolved: bool = False
    last_intent: Optional[str] = None

    def record_turn(self, response_time_ms: float, intent: str, confidence: float, failed: bool = False):
        """Record metrics for a conversation turn."""
        self.turn_count += 1
        self.response_times.append(response_time_ms)
        self.intents.append(intent)
        self.confidences.append(confidence)
        self.last_intent = intent
        
        if failed:
            self.failed_intents += 1

    def mark_escalated(self):
        """Mark session as escalated."""
        self.escalated = True

    def mark_resolved(self):
        """Mark session as resolved."""
        self.resolved = True

    def finalize_session(self) -> SessionMetrics:
        """Create final session metrics."""
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        avg_confidence = sum(self.confidences) / len(self.confidences) if self.confidences else 0
        
        # Calculate completion rate (simplified - resolved or >3 turns)
        completion_rate = 1.0 if self.resolved else min(1.0, self.turn_count / 5.0)
        
        # Calculate escalation rate (0 or 1 for individual session)
        escalation_rate = 1.0 if self.escalated else 0.0
        
        return SessionMetrics(
            session_id=self.session_id,
            user_id=self.user_id,
            start_time=datetime.fromtimestamp(self.start_time, timezone.utc).isoformat(),
            end_time=datetime.fromtimestamp(end_time, timezone.utc).isoformat(),
            total_turns=self.turn_count,
            avg_response_time_ms=avg_response_time,
            resolved=self.resolved,
            escalated=self.escalated,
            failed_intent_count=self.failed_intents,
            intent_confidence_avg=avg_confidence,
            completion_rate=completion_rate,
            escalation_rate=escalation_rate,
        )


class MetricsCollector:
    """Collects and manages conversation metrics."""
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionTracker] = {}

    def start_session(self, user_id: str) -> str:
        """Start tracking a new conversation session."""
        session_id = f"SES-{uuid.uuid4().hex[:12].upper()}"
        start_time = time.time()
        
        tracker = SessionTracker(
            session_id=session_id,
            user_id=user_id,
            start_time=start_time
        )
        
        self.active_sessions[session_id] = tracker
        logger.info(
            "metrics.session_started",
            extra={"extra_data": {"session_id": session_id, "user_id": user_id}}
        )
        
        return session_id

    def record_turn(self, session_id: str, response_time_ms: float, intent: str, confidence: float, failed: bool = False):
        """Record metrics for a conversation turn."""
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found in active sessions")
            return
        
        self.active_sessions[session_id].record_turn(response_time_ms, intent, confidence, failed)
        
        logger.debug(
            "metrics.turn_recorded",
            extra={"extra_data": {
                "session_id": session_id,
                "response_time_ms": response_time_ms,
                "intent": intent,
                "confidence": confidence,
                "failed": failed
            }}
        )

    def mark_escalated(self, session_id: str):
        """Mark a session as escalated."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].mark_escalated()
            logger.info(
                "metrics.session_escalated",
                extra={"extra_data": {"session_id": session_id}}
            )

    def mark_resolved(self, session_id: str):
        """Mark a session as resolved."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].mark_resolved()
            logger.info(
                "metrics.session_resolved",
                extra={"extra_data": {"session_id": session_id}}
            )

    def end_session(self, session_id: str) -> Optional[SessionMetrics]:
        """End a session and store its metrics."""
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found in active sessions")
            return None
        
        tracker = self.active_sessions[session_id]
        metrics = tracker.finalize_session()
        
        # Store metrics in database
        create_session_metrics(metrics)
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        logger.info(
            "metrics.session_ended",
            extra={"extra_data": {
                "session_id": session_id,
                "total_turns": metrics.total_turns,
                "avg_response_time_ms": metrics.avg_response_time_ms,
                "resolved": metrics.resolved,
                "escalated": metrics.escalated
            }}
        )
        
        return metrics

    def get_active_session(self, session_id: str) -> Optional[SessionTracker]:
        """Get an active session tracker."""
        return self.active_sessions.get(session_id)

    def cleanup_stale_sessions(self, max_age_hours: float = 24.0):
        """Clean up sessions older than max_age_hours."""
        current_time = time.time()
        stale_sessions = []
        
        for session_id, tracker in self.active_sessions.items():
            age_hours = (current_time - tracker.start_time) / 3600
            if age_hours > max_age_hours:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            self.end_session(session_id)
            logger.info(
                "metrics.stale_session_cleaned",
                extra={"extra_data": {"session_id": session_id}}
            )


# Global metrics collector instance
metrics_collector = MetricsCollector()
