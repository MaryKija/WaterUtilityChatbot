"""backend/agent_autonomy.py

Full agent autonomy framework enabling agents to:
1. Make independent decisions without orchestrator control
2. Request information needed for decisions
3. Execute tools and handle results
4. Manage their own conversation flow
5. Escalate when appropriate
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .logger import logger


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    WAITING_FOR_INFO = "waiting_for_info"
    EXECUTING_TOOL = "executing_tool"
    GENERATING_RESPONSE = "generating_response"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ERROR = "error"


class DecisionType(Enum):
    """Types of decisions agents can make."""
    RESPOND_DIRECT = "respond_direct"  # Send response directly
    REQUEST_INFO = "request_info"      # Ask user for more information
    EXECUTE_TOOL = "execute_tool"      # Execute a tool
    ESCALATE = "escalate"              # Escalate to human
    DELEGATE = "delegate"              # Delegate to another agent
    CLARIFY = "clarify"                # Ask for clarification


@dataclass
class AgentDecision:
    """Structured agent decision."""
    decision_type: DecisionType
    intent: str
    confidence: float
    explanation: str
    required_info: List[str] = field(default_factory=list)
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    response: Optional[str] = None
    escalation_reason: Optional[str] = None
    delegate_to_agent: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "decision_type": self.decision_type.value,
            "intent": self.intent,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "required_info": self.required_info,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "response": self.response,
            "escalation_reason": self.escalation_reason,
            "delegate_to_agent": self.delegate_to_agent,
            "timestamp": self.timestamp,
        }


class AutonomousAgent(ABC):
    """Base class for autonomous agents with independent decision-making."""

    def __init__(self, name: str):
        self.name = name
        self.state = AgentState.IDLE
        self.decision_history: List[AgentDecision] = []
        self.context_stack: List[Dict[str, Any]] = []

    @abstractmethod
    def evaluate_message(self, message: str, context: dict) -> AgentDecision:
        """
        Evaluate message and make autonomous decision.
        
        All agents implement this to determine what action to take.
        """
        pass

    def make_decision(self, message: str, context: dict) -> AgentDecision:
        """Execute agent's autonomous decision-making pipeline."""
        self.state = AgentState.THINKING
        logger.info(f"{self.name}: Evaluating message - '{message[:50]}...'")

        try:
            # Core decision logic (implemented by subclasses)
            decision = self.evaluate_message(message, context)

            # Post-decision hooks
            self._apply_confidence_calibration(decision, message, context)
            self._log_decision(decision)

            # Update state based on decision
            self.state = self._next_state(decision)

            return decision

        except Exception as e:
            logger.error(f"{self.name}: Decision-making error: {e}")
            self.state = AgentState.ERROR
            return AgentDecision(
                decision_type=DecisionType.ESCALATE,
                intent="error",
                confidence=0.0,
                explanation=f"Agent error: {str(e)}",
                escalation_reason=f"Internal error in {self.name}"
            )

    def _apply_confidence_calibration(self, decision: AgentDecision, message: str, context: dict):
        """Calibrate confidence based on context and message signals."""
        # Check for high-confidence signals
        if decision.confidence < 0.7:
            # Low confidence - check if we have enough context
            if len(context.get("conversation_history", [])) < 2:
                decision.confidence *= 0.85  # Lower confidence with less history

        # Check for conflicting signals
        if len(self.decision_history) > 0:
            last_decision = self.decision_history[-1]
            if last_decision.intent == decision.intent:
                decision.confidence *= 1.05  # Boost confidence if consistent with recent decision
            elif last_decision.intent != "out_of_scope":
                decision.confidence *= 0.9  # Penalize if conflicting with recent decision

    def _log_decision(self, decision: AgentDecision):
        """Log decision for audit trail and learning."""
        self.decision_history.append(decision)
        logger.info(
            f"{self.name}: Decision - {decision.decision_type.value} "
            f"(intent={decision.intent}, confidence={decision.confidence:.2f})"
        )

    def _next_state(self, decision: AgentDecision) -> AgentState:
        """Determine next state based on decision."""
        if decision.decision_type == DecisionType.RESPOND_DIRECT:
            return AgentState.GENERATING_RESPONSE
        elif decision.decision_type == DecisionType.REQUEST_INFO:
            return AgentState.WAITING_FOR_INFO
        elif decision.decision_type == DecisionType.EXECUTE_TOOL:
            return AgentState.EXECUTING_TOOL
        elif decision.decision_type == DecisionType.ESCALATE:
            return AgentState.ESCALATED
        elif decision.decision_type == DecisionType.DELEGATE:
            return AgentState.IDLE  # Reset for delegation
        elif decision.decision_type == DecisionType.CLARIFY:
            return AgentState.WAITING_FOR_INFO
        else:
            return AgentState.COMPLETED

    def handle_result(self, result: Any, decision: AgentDecision) -> AgentDecision:
        """Handle tool execution result and make follow-up decision."""
        logger.info(f"{self.name}: Processing result from {decision.tool_name}")

        # If tool succeeded, generate response
        if isinstance(result, dict) and result.get("status") == "success":
            return AgentDecision(
                decision_type=DecisionType.RESPOND_DIRECT,
                intent=decision.intent,
                confidence=decision.confidence,
                explanation="Tool executed successfully",
                response=result.get("message", "Action completed successfully")
            )

        # If tool failed, escalate
        return AgentDecision(
            decision_type=DecisionType.ESCALATE,
            intent=decision.intent,
            confidence=0.5,
            explanation="Tool execution failed",
            escalation_reason=str(result)
        )

    def get_agent_profile(self) -> dict:
        """Return agent profile and statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "decisions_made": len(self.decision_history),
            "decision_types": self._get_decision_distribution(),
            "recent_decisions": [d.to_dict() for d in self.decision_history[-5:]],
        }

    def _get_decision_distribution(self) -> dict:
        """Get distribution of decision types."""
        distribution = {}
        for decision in self.decision_history:
            dt = decision.decision_type.value
            distribution[dt] = distribution.get(dt, 0) + 1
        return distribution


class AutonomousAgentManager:
    """Manages multiple autonomous agents and coordinates their actions."""

    def __init__(self):
        self.agents: Dict[str, AutonomousAgent] = {}
        self.decision_log: List[AgentDecision] = []

    def register_agent(self, agent: AutonomousAgent):
        """Register a new agent."""
        self.agents[agent.name] = agent
        logger.info(f"Registered autonomous agent: {agent.name}")

    def evaluate_with_agents(self, message: str, context: dict) -> AgentDecision:
        """
        Evaluate message with multiple agents and combine decisions.
        Uses weighted voting based on agent confidence.
        """
        if not self.agents:
            logger.warning("No agents registered")
            return AgentDecision(
                decision_type=DecisionType.ESCALATE,
                intent="no_agents",
                confidence=0.0,
                explanation="No agents available",
                escalation_reason="System configuration error"
            )

        # Get decisions from all agents
        agent_decisions = {}
        for agent_name, agent in self.agents.items():
            try:
                decision = agent.make_decision(message, context)
                agent_decisions[agent_name] = decision
            except Exception as e:
                logger.warning(f"Agent {agent_name} failed: {e}")

        # Combine decisions (weighted by confidence)
        combined_decision = self._combine_decisions(agent_decisions)
        self.decision_log.append(combined_decision)

        return combined_decision

    def _combine_decisions(self, decisions: Dict[str, AgentDecision]) -> AgentDecision:
        """Combine multiple agent decisions via weighted voting."""
        if not decisions:
            return AgentDecision(
                decision_type=DecisionType.ESCALATE,
                intent="no_decisions",
                confidence=0.0,
                explanation="No agent decisions available",
                escalation_reason="Decision aggregation failed"
            )

        # Convert to list for sorting
        decision_list = list(decisions.values())

        # Sort by confidence
        sorted_decisions = sorted(decision_list, key=lambda d: d.confidence, reverse=True)
        top_decision = sorted_decisions[0]

        # Log the combination
        agent_names = ", ".join(decisions.keys())
        logger.info(
            f"Combined {len(decisions)} agent decisions: "
            f"Selected {decisions.keys().__iter__().__next__() if decisions else 'none'} "
            f"(confidence={top_decision.confidence:.2f})"
        )

        return top_decision

    def get_manager_stats(self) -> dict:
        """Get manager statistics and health."""
        return {
            "agents_count": len(self.agents),
            "total_decisions": len(self.decision_log),
            "agent_profiles": {name: agent.get_agent_profile() for name, agent in self.agents.items()},
            "recent_decisions": [d.to_dict() for d in self.decision_log[-10:]],
        }


# Global manager instance
autonomous_agent_manager = AutonomousAgentManager()
