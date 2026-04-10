
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

import re
from typing import Any, Dict, Optional
from datetime import datetime

from .agent import run_agent
from .context_engine import context_manager, extract_entities
from .intent_pipeline import intent_pipeline
from .logger import logger
from .tool_executor import tool_executor
from .validators import is_valid_name


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

        # Clear context when user explicitly asks to reset
        command = message.strip().lower()
        if command in ("clear", "reset", "start over", "new conversation", "restart"):
            context = context_manager.reset_context(context)
            context_manager.save_context(user_id, context)
            return {
                "reply": "Conversation reset. How can I help you today?",
                "intent": None,
                "confidence": 1.0,
                "entities": {},
                "active_agent": None,
                "escalated": False,
            }

        # Update context with user message
        context = context_manager.update_context_with_history(context, "user", message)


        extracted = extract_entities(message)
        if extracted:
            entities = context.get("entities", {})
            entities.update(extracted)
            context["entities"] = entities
            logger.info(f"Extracted entities: {extracted}")

        # Clear context when user explicitly asks to reset
        command = message.strip().lower()
        if command in ("clear", "reset", "start over", "new conversation", "restart"):
            context = context_manager.reset_context(context)
            context_manager.save_context(user_id, context)
            return {
                "reply": "Conversation reset. How can I help you today?",
                "intent": None,
                "confidence": 1.0,
                "entities": {},
                "active_agent": None,
                "escalated": False,
            }

        # FLOW LOCK: If active_agent AND flow_started, BYPASS classification
        if (context.get("active_agent") and context.get("flow_started", False)):
            logger.info(f"Flow locked: {context['active_agent']}")
            agent_name = context["active_agent"]
            agent = self.agents.get(agent_name, self.agents["general_agent"])
            response = self._handle_with_agent(agent, message, context)
        elif context_manager.should_classify_intent(context):
            # Classify + route
            intent_result = intent_pipeline.classify(message, context)
            logger.info(f"Classified: {intent_result['intent']} ({intent_result['confidence']:.2f})")
            
            context = context_manager.update_context_with_intent(context, intent_result)
            
            # Check escalation first
            if context_manager.should_escalate(context, intent_result.get("confidence", 0), 0):
                context = context_manager.escalate_context(context, "low_confidence")
                agent = self.agents["human_agent"]
            else:
                agent_name = context.get("active_agent", "general_agent")
                agent = self.agents.get(agent_name, self.agents["general_agent"])

            response = self._handle_with_agent(agent, message, context)
        else:
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

    _COMPLAINT_FIELDS = ("name", "area", "issue")
    _NAME_STOPWORDS = {
        "account",
        "address",
        "agent",
        "area",
        "bill",
        "complaint",
        "experiencing",
        "hello",
        "help",
        "hi",
        "issue",
        "leak",
        "meter",
        "name",
        "outage",
        "please",
        "pressure",
        "problem",
        "report",
        "road",
        "service",
        "still",
        "street",
        "supply",
        "the",
        "water",
    }

    def _capture_step_reply(self, message: str, context: dict, entities: dict) -> None:
        """Capture direct replies for the field we are actively collecting."""
        step = str(context.get("step") or "")
        raw = (message or "").strip()
        if not raw:
            return

        if not entities.get("name") and step == "collect_name":
            maybe_name = self._extract_name_reply(raw)
            if maybe_name:
                entities["name"] = maybe_name

        if not entities.get("area"):
            if entities.get("address"):
                entities["area"] = entities["address"]
            elif step == "collect_area":
                entities["area"] = raw

        if not entities.get("issue"):
            inferred_issue = self._infer_issue(raw, context)
            if inferred_issue:
                entities["issue"] = inferred_issue
            elif step == "collect_issue":
                entities["issue"] = raw

    def _extract_name_reply(self, raw: str) -> Optional[str]:
        if any(ch.isdigit() for ch in raw):
            return None

        explicit_match = re.search(
            r"(?:my\s+name\s+is|i\s+am|i'm|name\s*[:=-]?)\s*([A-Za-z][A-Za-z\s'\-\.]{1,58})$",
            raw,
            flags=re.IGNORECASE,
        )
        candidate = explicit_match.group(1).strip() if explicit_match else raw.strip()
        tokens = re.findall(r"[A-Za-z][A-Za-z'\-\.]*", candidate)
        if not 2 <= len(tokens) <= 4:
            return None
        if any(token.lower() in self._NAME_STOPWORDS for token in tokens):
            return None

        normalized = " ".join(tokens)
        return normalized if is_valid_name(normalized) else None

    def _infer_issue(self, message: str, context: dict) -> Optional[str]:
        lowered = (message or "").lower()
        intent = str(context.get("intent") or "")

        if "leak" in lowered:
            return "Water leak"
        if "outage" in lowered or "no water" in lowered or "no supply" in lowered:
            return "Water outage"
        if "low pressure" in lowered:
            return "Low water pressure"
        if "burst" in lowered or "pipe" in lowered:
            return "Pipe fault"
        if intent == "leak_report":
            return "Water leak"
        return None

    def handle(self, message: str, context: dict) -> dict:
        entities = context.setdefault("entities", {})
        self._capture_step_reply(message, context, entities)

        current_field = next((field for field in self._COMPLAINT_FIELDS if not entities.get(field)), None)

        if current_field == "name":
            context_manager.update_context_with_step(context, "collect_name")
            return {
                "reply": "I can help report this issue. Please provide your full name.",
                "requires_tool": False
            }

        if current_field == "area":
            context_manager.update_context_with_step(context, "collect_area")
            return {
                "reply": "Please provide the area or address where the issue is occurring (e.g., 'Mulungushi Road House 434').",
                "requires_tool": False
            }

        if current_field == "issue":
            context_manager.update_context_with_step(context, "collect_issue")
            return {
                "reply": "Please describe the water issue (no water, low pressure, leak, etc.).",
                "requires_tool": False
            }

        # All info collected or meter provided, log complaint
        context_manager.update_context_with_step(context, "log_complaint")
        return {
            "reply": "Logging your complaint now...",
            "requires_tool": True,
            "tool_name": "log_complaint",
            "parameters": {
                "name": entities.get("name", "Customer"),
                "area": entities.get("area", "Unknown"),
                "issue": entities.get("issue", "Water supply issue"),
                "meter_number": entities.get("meter_number", entities.get("account_number"))
            }
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)
        return {"reply": tool_result or "Your complaint WC-XXXXXX has been logged. Our team will investigate within 24 hours."}


class BillingAgent(BaseAgent):
    """Agent for handling billing inquiries - integrated with agent.py logic."""

    def handle(self, message: str, context: dict) -> dict:
        from .agent import run_agent
        from .intent_pipeline import intent_pipeline
        from .context_engine import extract_entities

        # Extract intent (billing_inquiry)
        intent_data = {
            "intent": "billing_inquiry",
            "confidence": 0.95,
            "entities": extract_entities(message)
        }
        
        # Merge with context entities
        entities = context.get("entities", {})
        entities.update(intent_data["entities"])
        context["entities"] = entities

        # Use proven agent.py billing logic
        reply = run_agent(message, intent_data, context)

        # Save updated context (agent.py may update session)
        from .context_engine import context_manager
        context_manager.save_context(context.get("user_id", "unknown"), context)

        return {"reply": reply, "requires_tool": False}

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        return {"reply": tool_result or "Billing check complete."}


class ConnectionAgent(BaseAgent):
    """Agent for handling new connections."""

    def handle(self, message: str, context: dict) -> dict:
        entities = context.get("entities", {})
        step_str = str(context.get("step", "0"))
        step = int(step_str)

        required_fields = ["name", "address", "phone", "email"]
        current_field = required_fields[step] if step < len(required_fields) else None

        if current_field and not entities.get(current_field):
            prompts = {
                "name": "Please provide your full name.",
                "address": "Please provide your full address where connection is needed.",
                "phone": "Please provide your phone number.",
                "email": "Please provide your email (optional)."
            }
            context_manager.update_context_with_step(context, str(step + 1))
            return {
                "reply": prompts[current_field],
                "requires_tool": False
            }

        # All fields collected, create connection request
        context_manager.update_context_with_step(context, "create_connection")
        return {
            "reply": "Processing your new connection request...",
            "requires_tool": True,
            "tool_name": "create_connection_request",
            "parameters": entities
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)
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
        context_manager.reset_context(context)
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

        context_manager.reset_context(context)
        return {"reply": response}

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        return {"reply": "I apologize, but I encountered an error."}


class HumanAgent(BaseAgent):
    """Agent for escalated conversations."""

    def handle(self, message: str, context: dict) -> dict:
        return {
            "reply": "Your message has been sent to customer service. They will respond shortly.",
            "requires_tool": False
        }

    def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        return {"reply": "Your message has been sent to customer service."}


# Global orchestrator instance
orchestrator = Orchestrator()

