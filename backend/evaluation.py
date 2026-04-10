"""backend/evaluation.py

Advanced evaluation metrics framework for:
1. Conversation quality scoring
2. System performance analytics
3. Agent effectiveness tracking
4. Business KPIs
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from .logger import logger


@dataclass
class TurnMetrics:
    """Metrics for a single conversation turn."""
    turn_id: int
    intent: str
    confidence: float
    response_time_ms: float
    user_sentiment: float  # -1 to 1
    tool_name: Optional[str] = None
    tool_success: bool = False
    escalated: bool = False
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class SessionScore:
    """Overall score for a conversation session."""
    session_id: str
    quality_score: float  # 0-1
    satisfaction_proxy: float  # Based on sentiment
    resolution_score: float  # 0-1
    efficiency_score: float  # 0-1 (lower turns = better)
    escalation_necessity: float  # 0-1 (was escalation necessary)
    final_score: float  # 0-1 weighted combination
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class EvaluationEngine:
    """Evaluate conversation quality and system performance."""

    def __init__(self):
        self.turn_history: List[TurnMetrics] = []
        self.session_scores: Dict[str, SessionScore] = {}

    def record_turn(self, metrics: TurnMetrics):
        """Record metrics for a conversation turn."""
        self.turn_history.append(metrics)

    def evaluate_session(self, session_id: str, turns: List[TurnMetrics], resolved: bool) -> SessionScore:
        """
        Evaluate overall quality of a conversation session.
        
        Returns score 0-1 where:
        - 1.0 = excellent (quick resolution, high confidence, no escalation)
        - 0.5 = acceptable (some issues but resolved)
        - 0.0 = poor (unresolved or escalated inappropriately)
        """
        if not turns:
            return SessionScore(
                session_id=session_id,
                quality_score=0.0,
                satisfaction_proxy=0.0,
                resolution_score=0.0,
                efficiency_score=0.0,
                escalation_necessity=0.0,
                final_score=0.0,
            )

        # Component scores
        quality_score = self._calculate_quality_score(turns)
        satisfaction_proxy = self._calculate_satisfaction_proxy(turns)
        resolution_score = 1.0 if resolved else 0.0
        efficiency_score = self._calculate_efficiency_score(turns)
        escalation_necessity = self._assess_escalation_necessity(turns)

        # Weighted combination (70% quality, 20% resolution, 10% efficiency)
        final_score = (
            quality_score * 0.40 +
            satisfaction_proxy * 0.30 +
            resolution_score * 0.20 +
            efficiency_score * 0.10
        )

        session_score = SessionScore(
            session_id=session_id,
            quality_score=quality_score,
            satisfaction_proxy=satisfaction_proxy,
            resolution_score=resolution_score,
            efficiency_score=efficiency_score,
            escalation_necessity=escalation_necessity,
            final_score=final_score,
            details={
                "turn_count": len(turns),
                "avg_confidence": statistics.mean([t.confidence for t in turns]),
                "escalation_count": len([t for t in turns if t.escalated]),
                "tool_calls": len([t for t in turns if t.tool_name]),
                "avg_sentiment": statistics.mean([t.user_sentiment for t in turns]),
            }
        )

        self.session_scores[session_id] = session_score
        return session_score

    def _calculate_quality_score(self, turns: List[TurnMetrics]) -> float:
        """
        Calculate conversation quality based on:
        - Intent classification confidence
        - Sentiment trend
        - Tool success rate
        """
        # Confidence component (higher = better)
        confidences = [t.confidence for t in turns]
        confidence_score = statistics.mean(confidences)

        # Sentiment component (positive trend = better)
        sentiments = [t.user_sentiment for t in turns]
        if len(sentiments) > 1:
            sentiment_trend = sentiments[-1] - sentiments[0]  # Improvement over time
            sentiment_score = max(0.0, min(1.0, 0.5 + sentiment_trend * 0.5))
        else:
            sentiment_score = max(0.0, sentiments[0] + 0.5)  # Normalize to 0-1

        # Tool success component
        tool_turns = [t for t in turns if t.tool_name]
        if tool_turns:
            tool_success_rate = len([t for t in tool_turns if t.tool_success]) / len(tool_turns)
        else:
            tool_success_rate = 1.0  # No tools called = no failures

        # Weighted quality score
        quality = (confidence_score * 0.5 + sentiment_score * 0.3 + tool_success_rate * 0.2)
        return min(1.0, quality)

    def _calculate_satisfaction_proxy(self, turns: List[TurnMetrics]) -> float:
        """
        Estimate user satisfaction based on:
        - User sentiment trajectory
        - Escalation requests
        - Message length (engagement indicator)
        """
        sentiments = [t.user_sentiment for t in turns]

        # Base on final sentiment
        final_sentiment = sentiments[-1] if sentiments else 0.0
        satisfaction = (final_sentiment + 1.0) / 2.0  # Normalize from -1,1 to 0,1

        # Penalize if escalations happened
        escalation_count = len([t for t in turns if t.escalated])
        if escalation_count > 0:
            satisfaction *= (1 - escalation_count * 0.15)  # 15% penalty per escalation

        return max(0.0, min(1.0, satisfaction))

    def _calculate_efficiency_score(self, turns: List[TurnMetrics]) -> float:
        """
        Calculate efficiency based on:
        - Number of turns (fewer = better, up to a limit)
        - Response time
        - First-turn resolution
        """
        turn_count = len(turns)

        # Ideal is 3-4 turns. Penalize heavily for >10 turns
        if turn_count <= 4:
            efficiency_from_turns = 1.0
        elif turn_count <= 8:
            efficiency_from_turns = 0.8 - (turn_count - 4) * 0.05
        else:
            efficiency_from_turns = max(0.1, 0.6 - (turn_count - 8) * 0.05)

        # Response time component (target <1000ms)
        avg_response_time = statistics.mean([t.response_time_ms for t in turns]) if turns else 1000
        if avg_response_time < 500:
            time_score = 1.0
        elif avg_response_time < 1000:
            time_score = 1.0 - (avg_response_time - 500) / 500 * 0.2
        else:
            time_score = 0.8 - min(0.7, (avg_response_time - 1000) / 2000)

        efficiency = efficiency_from_turns * 0.75 + time_score * 0.25
        return max(0.0, min(1.0, efficiency))

    def _assess_escalation_necessity(self, turns: List[TurnMetrics]) -> float:
        """
        Assess whether escalations that occurred were necessary.
        Returns 0-1 where 1.0 = all escalations were justified.
        """
        escalated_turns = [t for t in turns if t.escalated]
        if not escalated_turns:
            return 1.0  # No escalations = all justified (or not needed)

        # Low confidence escalations are justified
        low_conf_escalations = len([t for t in escalated_turns if t.confidence < 0.5])

        # High sentiment drop escalations are justified
        sentiment_drop_escalations = 0
        for i, turn in enumerate(escalated_turns):
            if i > 0 and turn.user_sentiment < turns[i-1].user_sentiment - 0.3:
                sentiment_drop_escalations += 1

        necessary_escalations = low_conf_escalations + sentiment_drop_escalations
        necessity_rate = necessary_escalations / len(escalated_turns) if escalated_turns else 0.0

        return min(1.0, necessity_rate)

    def get_cohort_analytics(self, intent: str = "") -> dict:
        """Analyze metrics for a cohort of sessions (all or by intent)."""
        if intent:
            relevant_sessions = [
                score for score in self.session_scores.values()
                if score.details.get("intent") == intent
            ]
        else:
            relevant_sessions = list(self.session_scores.values())

        if not relevant_sessions:
            return {"message": "No sessions to analyze"}

        scores = [s.final_score for s in relevant_sessions]
        qualities = [s.quality_score for s in relevant_sessions]
        satisfactions = [s.satisfaction_proxy for s in relevant_sessions]

        return {
            "session_count": len(relevant_sessions),
            "avg_final_score": statistics.mean(scores),
            "median_final_score": statistics.median(scores),
            "avg_quality_score": statistics.mean(qualities),
            "avg_satisfaction_proxy": statistics.mean(satisfactions),
            "score_distribution": self._get_score_distribution(scores),
            "sessions_above_80": len([s for s in scores if s > 0.8]),
            "sessions_below_50": len([s for s in scores if s < 0.5]),
        }

    def get_aggregate_ratings(self) -> dict:
        """Get overall system ratings."""
        all_scores = [s.final_score for s in self.session_scores.values()]
        if not all_scores:
            return {"message": "No sessions rated yet"}

        avg_score = statistics.mean(all_scores)
        letter_grade = self._score_to_letter(avg_score)

        return {
            "average_score": avg_score,
            "letter_grade": letter_grade,
            "percentile_90": sorted(all_scores)[int(len(all_scores) * 0.9)],
            "percentile_50": statistics.median(all_scores),
            "percentile_10": sorted(all_scores)[int(len(all_scores) * 0.1)],
            "excellent_sessions": len([s for s in all_scores if s >= 0.9]),
            "good_sessions": len([s for s in all_scores if 0.7 <= s < 0.9]),
            "fair_sessions": len([s for s in all_scores if 0.5 <= s < 0.7]),
            "poor_sessions": len([s for s in all_scores if s < 0.5]),
        }

    def _get_score_distribution(self, scores: List[float]) -> dict:
        """Get distribution of scores in buckets."""
        distribution = {
            "0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
            "0.6-0.8": 0, "0.8-1.0": 0
        }
        for score in scores:
            if score < 0.2:
                distribution["0.0-0.2"] += 1
            elif score < 0.4:
                distribution["0.2-0.4"] += 1
            elif score < 0.6:
                distribution["0.4-0.6"] += 1
            elif score < 0.8:
                distribution["0.6-0.8"] += 1
            else:
                distribution["0.8-1.0"] += 1
        return distribution

    def _score_to_letter(self, score: float) -> str:
        """Convert 0-1 score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"


# Global evaluation engine
evaluation_engine = EvaluationEngine()
