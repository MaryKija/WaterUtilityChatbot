"""backend/orchestrator.py

Orchestrator for handling conversation requests.

Coordinates:
- Context loading/saving
- Intent classification decisions
- Agent routing
- Tool execution
- Response generation
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .agent import run_agent
from .context_engine import context_manager
from .intent_pipeline import intent_pipeline
from .logger import logger
from .tool_executor import tool_executor


class Orchestrator:
    """Central orchestrator for conversation requests."""

    def __init__(self):
        self.agents = {
            "complaint_agent": ComplaintAgent(),
            "billing_agent": BillingAgent(),
            "connection_agent": ConnectionAgent(),
            "info_agent": InfoAgent(),
            "general_agent": GeneralAgent(),
            "human_agent": HumanAgent(),
        }

    def handle_request(self, user_id: str, message: str) -> dict:
        """Handle a conversation request."""
        # Load context
        context = context_manager.load_context(user_id)

        # Update context with user message
        context = context_manager.update_context_with_history(context, "user", message)

        # Decide next action
        if context_manager.should_continue_workflow(context):
            # Continue existing workflow
            agent_name = context.get("active_agent", "general_agent")
            agent = self.agents.get(agent_name, self.agents["general_agent"])

            response = self._handle_with_agent(agent, message, context)

        elif context_manager.should_classify_intent(context):
            # Run intent classification
            intent_result = intent_pipeline.classify(message, context)

            # Update context with intent
            context = context_manager.update_context_with_intent(context, intent_result)

            # Check for escalation
            if context_manager.should_escalate(context, intent_result.get("confidence", 0), 0):
                context = context_manager.escalate_context(context, "low_confidence")
                agent = self.agents["human_agent"]
            else:
                agent_name = context.get("active_agent", "general_agent")
                agent = self.agents.get(agent_name, self.agents["general_agent"])

            response = self._handle_with_agent(agent, message, context)

        else:
            # Default to general agent
            agent = self.agents["general_agent"]
            response = self._handle_with_agent(agent, message, context)

        # Update context with bot response
        context = context_manager.update_context_with_history(context, "bot", response)

        # Save context
        context_manager.save_context(user_id, context)

        return {
            "reply": response,
            "intent": context.get("intent"),
            "confidence": context.get("confidence"),
            "entities": context.get("entities", {}),
            "active_agent": context.get("active_agent"),
            "escalated": context.get("escalated", False),
        }

    def _handle_with_agent(self, agent, message: str, context: dict) -> str:
        """Handle request with specific agent."""
        # Get agent decision
        decision = agent.handle(message, context)

        # Check if tool execution is needed
        if decision.get("requires_tool"):
            tool_result = tool_executor.execute(
                decision["tool_name"],
                decision.get("parameters", {}),
                context
            )

            # Pass tool result back to agent for final response
            final_decision = agent.handle_with_tool_result(message, context, tool_result)
            return final_decision.get("reply", "I apologize, but I encountered an error.")

        # No tool needed, return direct response
        return decision.get("reply", "I apologize, but I encountered an error.")


class BaseAgent:
    """Base agent class."""

    def handle(self, message: str, context: dict) -> dict:
        """Handle message and return decision."""
        raise NotImplementedError

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        """Handle message with tool result."""
        raise NotImplementedError


class ComplaintAgent(BaseAgent):
    """Agent for handling complaints."""

    def handle(self, message: str, context: dict) -> dict:
        entities = context.get("entities", {})
        step = context.get("step")

        if not entities.get("name"):
            context_manager.update_context_with_step(context, "collect_name")
            return {
                "reply": "I can help report this issue. Please provide your full name.",
                "requires_tool": False
            }

        if not entities.get("area"):
            context_manager.update_context_with_step(context, "collect_area")
            return {
                "reply": "Please provide the area where the issue is occurring.",
                "requires_tool": False
            }

        if not entities.get("issue"):
            context_manager.update_context_with_step(context, "collect_issue")
            return {
                "reply": "Please describe the issue you're experiencing.",
                "requires_tool": False
            }

        # All info collected, log complaint
        context_manager.update_context_with_step(context, "log_complaint")
        return {
            "reply": "Logging your complaint...",
            "requires_tool": True,
            "tool_name": "log_complaint",
            "parameters": {
                "name": entities["name"],
                "area": entities["area"],
                "issue": entities["issue"]
            }
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        # Tool result is the complaint response
        context_manager.reset_context(context)  # End workflow
        return {"reply": tool_result}


class BillingAgent(BaseAgent):
    """Agent for handling billing inquiries."""

    def handle(self, message: str, context: dict) -> dict:
        entities = context.get("entities", {})

        if not entities.get("account_number"):
            context_manager.update_context_with_step(context, "collect_account")
            return {
                "reply": "Please provide your account number to check your billing information.",
                "requires_tool": False
            }

        # Get bill information
        context_manager.update_context_with_step(context, "get_bill")
        return {
            "reply": "Checking your bill...",
            "requires_tool": True,
            "tool_name": "get_bill",
            "parameters": {"account_number": entities["account_number"]}
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)  # End workflow
        return {"reply": tool_result}


class ConnectionAgent(BaseAgent):
    """Agent for handling new connections."""

    def handle(self, message: str, context: dict) -> dict:
        entities = context.get("entities", {})
        step = context.get("step", 0)

        required_fields = ["name", "address", "phone", "email"]
        current_field = required_fields[step] if step < len(required_fields) else None

        if current_field and not entities.get(current_field):
            prompts = {
                "name": "Please provide your full name.",
                "address": "Please provide your full address.",
                "phone": "Please provide your phone number.",
                "email": "Please provide your email address."
            }
            context_manager.update_context_with_step(context, step + 1)
            return {
                "reply": prompts[current_field],
                "requires_tool": False
            }

        # All fields collected, create connection request
        context_manager.update_context_with_step(context, "create_connection")
        return {
            "reply": "Creating your connection request...",
            "requires_tool": True,
            "tool_name": "create_connection_request",
            "parameters": entities
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)  # End workflow
        return {"reply": tool_result}


class InfoAgent(BaseAgent):
    """Agent for handling information requests."""

    def handle(self, message: str, context: dict) -> dict:
        return {
            "reply": "Getting office information...",
            "requires_tool": True,
            "tool_name": "get_office_info",
            "parameters": {}
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)  # End workflow
        return {"reply": tool_result}


class GeneralAgent(BaseAgent):
    """Agent for general chat and out-of-scope requests."""

    def handle(self, message: str, context: dict) -> dict:
        from .llm.groq_client import generate_response

        response = generate_response(
            message,
            context,
            intent="general_chat",
            max_tokens=140
        )

        context_manager.reset_context(context)  # End workflow
        return {"reply": response}

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        # Should not reach here for general agent
        return {"reply": "I apologize, but I encountered an error."}


class HumanAgent(BaseAgent):
    """Agent for escalated conversations."""

    def handle(self, message: str, context: dict) -> dict:
        return {
            "reply": "Your message has been sent to a customer service agent. They will assist you shortly.",
            "requires_tool": False
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        # Should not reach here for human agent
        return {"reply": "Your message has been sent to a customer service agent."}


# Global orchestrator instance
orchestrator = Orchestrator()