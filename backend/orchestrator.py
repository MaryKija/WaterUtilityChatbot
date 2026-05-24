
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
from abc import abstractmethod

if __name__ == "__main__" and __package__ is None:
    __package__ = "backend"

import sys
import os
if __name__ == "__main__":
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import ollama

from .context_engine import context_manager
from .llm.groq_client import generate_response
from .agent import run_agent  # Only needed for BillingAgent
from .decision_engine import decision_engine, DecisionContext
from .learning.confidence_learner import confidence_learner

import re
from typing import Any, Dict, Optional, cast
from datetime import datetime


from .context_engine import ContextManager, context_manager, extract_entities
from .intent_pipeline import IntentPipeline, intent_pipeline
from .logger import logger
from .tool_executor import ToolExecutor, tool_executor
from .validators import is_valid_name
from .metrics_collector import metrics_collector
from .emergency_detector import emergency_detector
from .tools import _fmt_datetime

class BaseAgent:
    """Base agent class."""

    @abstractmethod
    async def handle(self, message: str, context: dict) -> dict:
        """Handle message and return decision."""
        raise NotImplementedError

    @abstractmethod
    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
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

    _TICKET_ID_RE = re.compile(r"\b(WC-[A-Z0-9]{6})\b", re.IGNORECASE)

    def _ticket_id_from_message(self, message: str) -> Optional[str]:
        m = self._TICKET_ID_RE.search(message or "")
        return m.group(1).upper() if m else None

    def _capture_step_reply(self, message: str, context: dict, entities: dict) -> None:
        """Capture direct replies for the field we are actively collecting."""
        step = str(context.get("step") or "")
        raw = (message or "").strip()
        if not raw:
            return

        # Always try to infer issue from any message — user may repeat their problem
        if not entities.get("issue"):
            inferred_issue = self._infer_issue(raw, context)
            if inferred_issue:
                entities["issue"] = inferred_issue

        # Snapshot which fields were already present BEFORE this call so that
        # "next missing field" fallbacks don't cascade within a single turn.
        had_name = bool(entities.get("name"))
        had_area = bool(entities.get("area"))

        # Capture name: accept when step matches OR when name is the next missing field
        # (name comes first in the sequence: name → area → issue)
        name_is_next = not had_name and not had_area
        if not had_name and (step == "collect_name" or name_is_next):
            maybe_name = self._extract_name_reply(raw)
            if maybe_name:
                entities["name"] = maybe_name

        if not had_area:
            if entities.get("address"):
                entities["area"] = entities["address"]
            elif step == "collect_area" or (had_name and not had_area):
                # Accept any non-trivial reply as the area
                if len(raw) >= 3:
                    entities["area"] = raw

        if not entities.get("issue") and (step == "collect_issue" or
                (had_name and had_area and not entities.get("issue"))):
            # Accept any reply as the issue description
            if len(raw) >= 2:
                entities["issue"] = raw

    def _extract_name_reply(self, raw: str) -> Optional[str]:
        if any(ch.isdigit() for ch in raw) or len(raw) > 100:
            return None

        patterns = [
            r"(?:my\s+name\s+is|i\s+am|i'm|call\s+me|name\s*[:=-]?)\s*([A-Za-z][A-Za-z\s'\-\.]{1,58})",
            r"^([A-Za-z][A-Za-z\s'\-\.]{1,58})$"  # Direct name
        ]

        for pattern in patterns:
            match = re.search(pattern, raw, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                tokens = re.findall(r"[A-Za-z][A-Za-z'\-\.]+", candidate)

                # Accept 1-3 tokens, no stopwords, reasonable length
                if (1 <= len(tokens) <= 3 and
                    all(len(token) >= 2 for token in tokens) and
                    not any(token.lower() in self._NAME_STOPWORDS for token in tokens)):

                    normalized = " ".join(tokens)
                    return normalized if is_valid_name(normalized) else None

        return None

        

    def _infer_issue(self, message: str, context: dict) -> Optional[str]:
        lowered = (message or "").lower()
        intent = str(context.get("intent") or "")

        # Check most specific patterns first to avoid misclassification
        if any(term in lowered for term in ["dirty", "contaminated", "water quality", "smelly",
                                             "bad taste", "unsafe", "quality issue", "quality problem",
                                             "colour", "color", "brown water", "yellow water",
                                             "cloudy water", "turbid"]):
            return "Dirty/contaminated water"
        if "leak" in lowered:
            return "Water leak"
        if any(p in lowered for p in ["outage", "no water", "no supply", "i have no water",
                                       "without water", "water is out", "water cut", "water off"]):
            return "Water outage"
        if "low pressure" in lowered or "low water pressure" in lowered:
            return "Low water pressure"
        if "burst" in lowered or "pipe" in lowered:
            return "Pipe fault"
        if "meter" in lowered or "reading" in lowered:
            return "Meter issue"
        if intent in {"report_fault", "leak_report"}:
            return "Water leak" if intent == "leak_report" else "Water supply issue"
        if intent == "meter_problem":
            return "Meter issue"
        return None

    async def handle(self, message: str, context: dict) -> dict:
        entities = context.setdefault("entities", {})
        intent = str(context.get("intent") or "")

        # Follow-up: status / tracking — do not restart full complaint intake
        if intent == "complaint_followup":
            ticket = (
                entities.get("ticket_id")
                or entities.get("ticket")
                or self._ticket_id_from_message(message)
            )
            if ticket:
                return {
                    "reply": "Checking your complaint status…",
                    "requires_tool": True,
                    "tool_name": "get_complaint_status",
                    "parameters": {"ticket_id": ticket},
                }
            return {
                "reply": (
                    "To check your complaint status, please send your reference number "
                    "(for example WC-ABC123). If you just logged a complaint, use the reference shown in the confirmation."
                ),
                "requires_tool": False,
            }

        # Handle outage information requests (vs. reporting new outages)
        if intent == "water_outage" or (
            intent == "report_fault"
            and entities.get("fault_type") == "outage"
            and entities.get("request_type") == "info"
        ):
            area = entities.get("area")
            
            # Try to extract area from message if not in entities
            if not area:
                message_lower = message.lower()
                # LgWSC service areas — Central Province, Zambia
                lgwsc_areas = [
                    "kabwe", "kapiri mposhi", "mkushi", "serenje", "chibombo",
                    "chisamba", "mumbwa", "shibuyunji", "itezhi-tezhi", "itezhi tezhi",
                    "chitambo", "luano", "ngabwe",
                ]
                for location in lgwsc_areas:
                    if location in message_lower:
                        area = location.title()
                        entities["area"] = area
                        break
            
            if area:
                return {
                    "reply": f"Checking outage status for {area}...",
                    "requires_tool": True,
                    "tool_name": "check_area_outage",
                    "parameters": {"area": area}
                }
            else:
                return {
                    "reply": "I can help with outage information. What area would you like me to check?",
                    "requires_tool": False
                }

        self._capture_step_reply(message, context, entities)

        # Pre-fill issue from intent if not yet captured
        if not entities.get("issue"):
            intent = str(context.get("intent") or "")
            issue_map = {
                "leak_report": "Water leak",
                "report_fault": "Water supply issue",
                "meter_problem": "Meter issue",
            }
            if entities.get("fault_type") == "water_quality":
                issue_map["report_fault"] = "Dirty/contaminated water"
            elif entities.get("fault_type") == "outage":
                issue_map["report_fault"] = "Water outage"
            elif entities.get("fault_type") == "low_pressure":
                issue_map["report_fault"] = "Low water pressure"
            if intent in issue_map:
                entities["issue"] = issue_map[intent]

        current_field = next((field for field in self._COMPLAINT_FIELDS if not entities.get(field)), None)

        if current_field == "name":
            context_manager.update_context_with_step(context, "collect_name")
            # Clear stale complaint entities from any previous session so they
            # don't bleed into this new complaint (e.g. old issue="Water leak"
            # overwriting a new "water quality" report).
            # Preserve issue/fault_type that were just inferred from THIS message.
            just_inferred_issue = entities.get("issue")
            just_inferred_fault = entities.get("fault_type")
            entities.pop("name", None)
            entities.pop("area", None)
            entities.pop("issue", None)
            entities.pop("fault_type", None)
            # Re-apply issue/fault_type inferred from the current message so they
            # survive into the next turn (prevents the test assertion failure where
            # issue is set then immediately cleared).
            if just_inferred_issue:
                entities["issue"] = just_inferred_issue
            if just_inferred_fault:
                entities["fault_type"] = just_inferred_fault
            context["entities"] = entities
            context_manager.save_context(context.get("user_id", "unknown"), context)
            return {
                "reply": "I can help report this issue. What is your full name?",
                "requires_tool": False
            }

        if current_field == "area":
            context_manager.update_context_with_step(context, "collect_area")
            context_manager.save_context(context.get("user_id", "unknown"), context)
            return {
                "reply": "What area or address is the issue occurring at? (e.g. 'Mulungushi Road, House 434')",
                "requires_tool": False
            }

        if current_field == "issue":
            context_manager.update_context_with_step(context, "collect_issue")
            context_manager.save_context(context.get("user_id", "unknown"), context)
            return {
                "reply": "Please describe the water issue (e.g. no water, low pressure, leak).",
                "requires_tool": False
            }

        # All info collected — log the complaint
        context_manager.update_context_with_step(context, "log_complaint")
        context_manager.save_context(context.get("user_id", "unknown"), context)
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

    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        # Do not call reset_context here — it wiped ticket_id and forced users back into
        # intake. Flow flags are cleared in ToolExecutor after log_complaint / status.
        
        # Handle outage information results
        if context.get("tool_name") == "check_area_outage":
            if tool_result:
                return {
                    "reply": (
                        f"Water Outage Update\n\n"
                        f"Area: {tool_result.area}\n"
                        f"Status: {tool_result.status}\n"
                        f"Details: {tool_result.description}\n"
                        f"Estimated Restoration: {_fmt_datetime(tool_result.estimated_restore_at)}\n"
                        f"Last Updated: {_fmt_datetime(tool_result.last_updated)}\n\n"
                        f"Type 'report outage' if you are experiencing a new issue."
                    ),
                    "requires_tool": False
                }
            else:
                return {
                    "reply": (
                        "I could not find any outage information for that area. "
                        "This could mean there are no active outages reported, "
                        "the area name may be different, or the outage has been resolved.\n\n"
                        "Type 'report outage' if you are experiencing a new water issue."
                    ),
                    "requires_tool": False
                }
        
        return {"reply": tool_result or "Your complaint has been logged. Our team will investigate within 24 hours."}


class BillingAgent(BaseAgent):
    """Agent for handling billing inquiries - integrated with agent.py logic."""

    _GRATITUDE_OR_CLOSE = re.compile(
        r"^(thanks?|thank\s+you|thx|thanx|much\s+appreciated|cheers|ok\s*,?\s*thanks|ta)[\s!.]*$",
        re.IGNORECASE,
    )

    async def handle(self, message: str, context: dict) -> dict:
        from .agent import run_agent
        from .intent_pipeline import intent_pipeline
        from .context_engine import extract_entities

        raw = (message or "").strip()
        # Billing stays flow-locked on billing_agent; short thanks must not re-run bill + payment blocks.
        entities_existing = context.get("entities") or {}
        if raw and entities_existing.get("account_number") and self._GRATITUDE_OR_CLOSE.match(raw.strip()):
            context["active_agent"] = None
            context["flow_started"] = False
            context.pop("flow", None)
            context.pop("billing_case", None)
            return {
                "reply": "You're welcome! If you need anything else—billing, faults, or connections—just ask.",
                "requires_tool": False,
            }

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

    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        return {"reply": tool_result or "Billing check complete."}


class ConnectionAgent(BaseAgent):
    """Agent for handling new connections."""

    async def handle(self, message: str, context: dict) -> dict:
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
            context_manager.save_context(context.get("user_id", "unknown"), context)
            return {
                "reply": prompts[current_field],
                "requires_tool": False
            }

        # All fields collected, create connection request
        context_manager.update_context_with_step(context, "create_connection")
        context_manager.save_context(context.get("user_id", "unknown"), context)
        return {
            "reply": "Processing your new connection request...",
            "requires_tool": True,
            "tool_name": "create_connection_request",
            "parameters": entities
        }

    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)
        return {"reply": tool_result}


class InfoAgent(BaseAgent):
    """Agent for handling information requests."""

    async def handle(self, message: str, context: dict) -> dict:
        return {
            "reply": "Getting office information...",
            "requires_tool": True,
            "tool_name": "get_office_info",
            "parameters": {}
        }

    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        context_manager.reset_context(context)
        return {"reply": tool_result}


class GeneralAgent(BaseAgent):
    """Agent for general chat and out-of-scope requests."""

    async def handle(self, message: str, context: dict) -> dict:
        from .llm.groq_client import generate_response

        # Use empty session — never pass conversation history to avoid hallucination
        try:
            response = generate_response(
                message,
                {},
                intent="general_chat",
                max_tokens=140
            )
        except Exception as exc:
            logger.warning(f"LLM unavailable for general agent; using deterministic fallback err={exc}")
            response = (
                "I'm an AI assistant that can help with water utility services such as billing, faults, "
                "complaints, payments, office information, and new connections. "
                "Type 'human agent' at any time to speak with a customer service representative."
            )

        # Only reset context if we're not mid-flow
        if not context.get("flow_started") and not context.get("active_agent"):
            context_manager.reset_context(context)
        return {"reply": response}

    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        return {"reply": "I apologize, but I encountered an error."}


class HumanAgent(BaseAgent):
    """Agent for escalated conversations."""

    async def handle(self, message: str, context: dict) -> dict:
        return {
            "reply": "Your message has been sent to customer service. They will respond shortly.",
            "requires_tool": False
        }

    async def handle_with_tool_result(self, message: str, context: dict, tool_result: Any) -> dict:
        return {"reply": "Your message has been sent to customer service."}



class Orchestrator:
    """Central orchestrator for conversation requests."""
    def __init__(self, config, context_manager, intent_pipeline, tool_executor):
        self.config = config
        self.context_manager = context_manager
        self.intent_pipeline = intent_pipeline
        self.tool_executor = tool_executor

        # Initialize agents
        self.agents = {
            "complaint_agent": ComplaintAgent(),
            "billing_agent": BillingAgent(),
            "connection_agent": ConnectionAgent(),
            "info_agent": InfoAgent(),
            "general_agent": GeneralAgent(),
            "human_agent": HumanAgent(),
        }

    async def process(self, message: str, user_id: str, **kwargs) -> dict:
        """
        Unified entry point for FastAPI. 
        Handles context, intent classification, and agent routing.
        """
        import time
        start_time = time.time()
        
        try:
            # 1. Load context and ensure session tracking
            context = self.context_manager.load_context(user_id)
            session_id = context.get("session_id")
            
            # Start new session if needed
            if not session_id or not metrics_collector.get_active_session(session_id):
                session_id = metrics_collector.start_session(user_id)
                context["session_id"] = session_id
            
            # 1. Handle reset commands FIRST
            if self._is_reset_command(message):
                context = self.context_manager.reset_context(context)
                self.context_manager.save_context(user_id, context)
                return self._format_response("Conversation reset. I'm an AI assistant for water utility services. How can I help you today?", context)
        
            # 2. Check for emergencies first
            emergency_alert = emergency_detector.detect_emergency(message, context)
            if emergency_alert:
                # Mark session as escalated for emergency
                metrics_collector.mark_escalated(session_id)
                context["escalated"] = True
                context["emergency"] = True
                
                emergency_response = emergency_detector.get_emergency_response(emergency_alert)
                context = self.context_manager.update_context_with_history(context, "user", message)
                context = self.context_manager.update_context_with_history(context, "bot", emergency_response)
                self.context_manager.save_context(user_id, context)
                
                return self._format_response(emergency_response, context)
        
            # 3. Update context with message
            context = self.context_manager.update_context_with_history(context, "user", message)
        
            # 4. Extract entities early
            entities = extract_entities(message)
            if entities:
                current_entities = context.get("entities", {})
                current_entities.update(entities)
                context["entities"] = current_entities

            # A persisted service flow can survive a browser refresh or server
            # restart. If the user clearly starts a different service request,
            # release the old agent lock before routing this turn.
            self._release_stale_flow_for_new_request(message, context)
        
            # 4. Route to appropriate handler
            if self._is_flow_locked(context):
                reply_text = await self._handle_active_flow(message, context)
            elif self.context_manager.should_classify_intent(context):
                reply_text = await self._handle_new_intent(message, context)
            else:
                reply_text = await self._get_llm_fallback(message, context)
        
            # 5. Calculate response time and record metrics
            response_time_ms = (time.time() - start_time) * 1000
            
            # Get intent and confidence for metrics
            intent_result = context.get("last_intent_result", {})
            intent = intent_result.get("intent", "general_chat")
            confidence = intent_result.get("confidence", 0.0)
            failed = intent_result.get("failed", False)
            
            # Record turn metrics
            metrics_collector.record_turn(session_id, response_time_ms, intent, confidence, failed)
            
            # Check for escalation or resolution
            if "escalated" in context and context["escalated"]:
                metrics_collector.mark_escalated(session_id)
            if "resolved" in context and context["resolved"]:
                metrics_collector.mark_resolved(session_id)
        
            # 6. Save updated context — always use the request's user_id as the key
            #    and stamp it into context so it survives any in-flow reset.
            context["user_id"] = user_id
            context["session_id"] = session_id
            # Always persist flow state immediately after the agent sets it,
            # before history is appended (history append must not race with flow flags).
            self.context_manager.save_context(user_id, context)          # ← unconditional, early
            context = self.context_manager.update_context_with_history(context, "bot", reply_text)
            logger.info(f"Saving context: active_agent={context.get('active_agent')} flow_started={context.get('flow_started')}")
            self.context_manager.save_context(user_id, context)          # ← final save with history
        
            return self._format_response(reply_text, context)
        
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return self._format_response(
                "I'm sorry, I'm having trouble. Please try again.", 
                {}
            )
        
    async def _handle_active_flow(self, message: str, context: dict) -> str:
        """Handle ongoing agent flow."""
        active_agent: str = context.get("active_agent") or "general_agent"
        agent = self.agents.get(active_agent, self.agents["general_agent"])
        return await self._handle_with_agent(agent, message, context)
    
    async def _handle_new_intent(self, message: str, context: dict) -> str:
        """Handle new intent classification with agentic decision-making."""
        # Guard: if context already has a service agent set (stale load race),
        # treat this as a flow continuation rather than a new intent.
        _service_agents = {"complaint_agent", "billing_agent", "connection_agent", "info_agent"}
        if context.get("active_agent") in _service_agents:
            return await self._handle_active_flow(message, context)

        intent_result = self.intent_pipeline.classify(message, context)
        context = self.context_manager.update_context_with_intent(context, intent_result)
        # Store intent result for metrics collection
        context["last_intent_result"] = intent_result

        if intent_result.get("intent") == "out_of_scope":
            return await self._get_out_of_scope_response(message)

        # Create decision context for agentic behavior
        user_id = context.get("user_id", "unknown")
        conversation_history = context.get("history", [])
        previous_decisions = context.get("decisions", [])
        
        decision_context = DecisionContext(
            user_id=user_id,
            intent=intent_result.get("intent", "general_chat"),
            entities=context.get("entities", {}),
            conversation_history=conversation_history,
            previous_decisions=previous_decisions,
            user_satisfaction_score=context.get("satisfaction_score", 0.5),
            session_duration=self._calculate_session_duration(context)
        )

        # Check if we should act autonomously based on confidence learning
        confidence = intent_result.get("confidence", 0.0)
        intent = intent_result.get("intent", "general_chat")
        
        # Create context for confidence learner
        confidence_context = {
            "user_satisfaction_score": context.get("satisfaction_score", 0.5),
            "session_duration": self._calculate_session_duration(context),
            "previous_success_rate": self._calculate_user_success_rate(context)
        }
        
        # Use agentic decision engine
        decision = decision_engine.make_decision(decision_context)
        
        # Structured flows (billing, etc.) must not fall through to raw LLM when intent is clear.
        # The learner threshold + calibration can block autonomy; Groq then invents wrong steps (e.g. "name on account").
        src = str(intent_result.get("source") or "")
        conf_f = float(confidence or 0.0)
        force_structured_route = src in (
            "rule_billing_priority",
            "rule_billing_continuation",
        ) or (intent == "billing_inquiry" and conf_f >= 0.88)

        should_be_autonomous = force_structured_route or confidence_learner.should_be_autonomous(
            confidence, intent, confidence_context
        )

        if should_be_autonomous:
            # Execute the agentic decision
            response = await self._execute_agentic_decision(decision, message, context, intent_result)
            
            # Record confidence outcome for learning
            # We'll update this later when we know if the response was successful
            context["confidence_learning"] = {
                "intent": intent,
                "predicted_confidence": confidence,
                "context": confidence_context,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Fall back to standard response with lower autonomy
            logger.info(f"Confidence too low for autonomous action: {confidence:.2f} < threshold for {intent}")
            response = await self._get_llm_fallback(message, context)
        
        # Store decision for learning
        context["decisions"] = previous_decisions + [{
            "action": decision.action,
            "confidence": decision.confidence,
            "timestamp": datetime.now().isoformat()
        }]
        
        return response
    
    async def _execute_agentic_decision(self, decision, message: str, context: dict, intent_result: dict) -> str:
        """Execute the decision made by the agentic decision engine."""
        action = decision.action
        
        try:
            if action == "collect_name_first":
                context["active_agent"] = "complaint_agent"
                context["flow_started"] = True
                context["step"] = "collect_name"
                agent = self.agents["complaint_agent"]
                return await self._handle_with_agent(agent, message, context)
            
            elif action == "collect_location_first":
                context["active_agent"] = "complaint_agent"
                context["flow_started"] = True
                context["step"] = "collect_area"
                agent = self.agents["complaint_agent"]
                return await self._handle_with_agent(agent, message, context)
            
            elif action == "escalate_immediately":
                context = self.context_manager.escalate_context(context, "urgent_escalation")
                agent = self.agents["human_agent"]
                return await self._handle_with_agent(agent, message, context)
            
            elif action == "request_account_number":
                context["active_agent"] = "billing_agent"
                context["step"] = "collect_account"
                agent = self.agents["billing_agent"]
                return await self._handle_with_agent(agent, message, context)
            
            elif action == "provide_general_billing_info":
                context["active_agent"] = "billing_agent"
                context["step"] = "general_info"
                agent = self.agents["billing_agent"]
                return await self._handle_with_agent(agent, message, context)
            
            elif action == "offer_payment_assistance":
                context["active_agent"] = "billing_agent"
                context["step"] = "payment_assistance"
                agent = self.agents["billing_agent"]
                return await self._handle_with_agent(agent, message, context)
            
            elif action == "provide_help_menu":
                return await self._get_llm_fallback(message, context)
            
            elif action == "engage_small_talk":
                # Use LLM for small talk
                return await self._get_llm_fallback(message, context)
            
            elif action == "direct_to_specific_service":
                # Try to infer specific service and route accordingly
                inferred_intent = self._infer_specific_intent(message)
                if inferred_intent:
                    intent_result["intent"] = inferred_intent
                    return await self._handle_new_intent(message, context)
                else:
                    return await self._get_llm_fallback(message, context)
            
            elif action == "proactive_assistance":
                return await self._provide_proactive_assistance(context)
            
            elif action == "complex_problem_solving":
                return await self._handle_complex_problem(message, context)
            
            elif action == "standard_response":
                # Fallback to standard flow
                confidence: float = cast(float, intent_result.get("confidence") or 0.0)
                if self.context_manager.should_escalate(context, confidence, 0):
                    context = self.context_manager.escalate_context(context, "low_confidence")
                    agent = self.agents["human_agent"]
                else:
                    active_agent: str = context.get("active_agent") or "general_agent"
                    agent = self.agents.get(active_agent, self.agents["general_agent"])
                return await self._handle_with_agent(agent, message, context)
            
            else:
                # Unknown action, fallback to standard response
                logger.warning(f"Unknown agentic decision action: {action}, falling back to standard response")
                return await self._get_llm_fallback(message, context)
                
        except Exception as e:
            logger.error(f"Error executing agentic decision {action}: {e}")
            # Fallback to standard response
            return await self._get_llm_fallback(message, context)
    
    def _calculate_session_duration(self, context: dict) -> float:
        """Calculate the duration of the current session in minutes."""
        history = context.get("history", [])
        if not history:
            return 0.0
        
        # Get first and last message timestamps
        first_timestamp = history[0].get("timestamp")
        last_timestamp = history[-1].get("timestamp")
        
        if first_timestamp and last_timestamp:
            try:
                from datetime import datetime
                first_time = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                duration = (last_time - first_time).total_seconds() / 60  # Convert to minutes
                return max(0.0, duration)
            except:
                pass
        
        return 0.0
    
    def _calculate_user_success_rate(self, context: dict) -> float:
        """Calculate the success rate for this specific user."""
        # Get user's previous outcomes from context or storage
        user_id = context.get("user_id", "unknown")
        
        # For now, return a default value - this could be enhanced with actual user history
        # In a full implementation, this would query user-specific success data
        return context.get("user_success_rate", 1.0)
    
    def _infer_specific_intent(self, message: str) -> Optional[str]:
        """Infer a more specific intent from the message content."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["leak", "burst", "pipe", "water leaking"]):
            return "leak_report"
        elif any(word in message_lower for word in ["fault", "no water", "water cut", "low pressure", "water issue"]):
            return "report_fault"
        elif any(word in message_lower for word in ["bill", "payment", "charge", "cost"]):
            return "billing_inquiry"
        elif any(word in message_lower for word in ["new", "connect", "install", "setup"]):
            return "new_connection"
        elif any(word in message_lower for word in ["meter", "reading", "measurement"]):
            return "meter_problem"
        elif any(word in message_lower for word in ["office", "location", "hours", "contact"]):
            return "office_info"
        
        return None

    def _release_stale_flow_for_new_request(self, message: str, context: dict) -> None:
        """Unlock stale persisted context when the user explicitly changes task."""
        active_agent = str(context.get("active_agent") or "")
        if active_agent not in {"complaint_agent", "billing_agent", "connection_agent", "info_agent"}:
            return

        inferred_intent = self._infer_specific_intent(message)
        if not inferred_intent:
            return

        target_agent = self.context_manager._map_intent_to_agent(inferred_intent)
        if not target_agent or target_agent == active_agent:
            return

        logger.info(
            "context.unlock_for_new_request",
            extra={"extra_data": {
                "from_agent": active_agent,
                "to_agent": target_agent,
                "intent": inferred_intent,
            }},
        )

        context["active_agent"] = None
        context["flow_started"] = False
        context["flow"] = None
        context["step"] = None
        context["intent"] = None
        context["confidence"] = None
        context.pop("last_intent_result", None)

        stale_keys = (
            "account_number",
            "meter_number",
            "pin",
            "pin_verified",
            "billing_case",
            "bill_issue",
            "payment_details",
            "payment_reflection_messages",
            "payment_issue_confidence",
        )
        entities = context.get("entities")
        if isinstance(entities, dict):
            for key in stale_keys:
                entities.pop(key, None)
        for key in stale_keys:
            context.pop(key, None)
    
    async def _provide_proactive_assistance(self, context: dict) -> str:
        """Provide proactive assistance based on conversation patterns."""
        history = context.get("history", [])
        recent_messages = [msg.get("content", "") for msg in history[-5:]]
        
        # Analyze conversation patterns
        all_text = " ".join(recent_messages).lower()
        
        if "leak" in all_text and "name" not in str(context.get("entities", {})):
            return "I notice you're asking about a water issue. To help you better, could you please provide your full name so I can log this properly?"
        
        elif "bill" in all_text and "account" not in str(context.get("entities", {})):
            return "I see you're interested in billing information. Having your account number would help me provide you with specific details about your bill."
        
        elif any(word in all_text for word in ["help", "confused", "not sure"]):
            return "Based on our conversation, I can help you with: water leak reports, billing questions, new connections, or general information. What would you like to focus on?"
        
        return "I'm here to help! Based on our conversation, I can assist you with water utility services. What specific concern can I help you with today?"
    
    async def _handle_complex_problem(self, message: str, context: dict) -> str:
        """Handle complex problems with multi-step approach."""
        # Break down the problem and provide step-by-step guidance
        return "I understand this is a complex issue. Let me help you step by step:\n\n1. First, could you tell me the main problem you're experiencing?\n2. When did this issue start?\n3. Have you noticed any patterns or specific triggers?\n\nThis will help me provide you with the most appropriate solution."

    def _is_reset_command(self, message: str) -> bool:
        """Check for reset commands."""
        reset_phrases = {"clear", "reset", "start over", "restart", "new conversation"}
        words = message.strip().lower().split()
        return bool(words and words[0] in reset_phrases)

    def _is_flow_locked(self, context: dict) -> bool:
        """Check if user is mid-flow.

        A flow is locked when:
        - An active_agent is set to a service agent (not general_agent), OR
        - flow_started is explicitly True
        AND the conversation is not escalated.

        History-based recovery: if active_agent and flow_started are missing
        (stale context load) but the last bot message is a mid-flow prompt
        (asking for name, area, issue, PIN, account number, etc.), recover the
        flow so the user's reply is not misrouted as a new intent.
        """
        active_agent: str = cast(str, context.get("active_agent") or "")
        flow_started: bool = context.get("flow_started", False)
        escalated: bool = context.get("escalated", False)

        if escalated:
            return False

        # Service agents always lock the flow — general_agent does not
        service_agents = {"complaint_agent", "billing_agent", "connection_agent", "info_agent"}
        if active_agent in service_agents:
            return True

        if flow_started:
            return True

        # History-based recovery: detect stale context by inspecting the last
        # bot message. If it is a mid-flow prompt, restore the flow so the
        # next user reply is handled by the correct agent rather than being
        # re-classified as a new intent.
        history = context.get("history") or []
        last_bot_text = ""
        for entry in reversed(history):
            if isinstance(entry, dict) and str(entry.get("role") or "").lower() == "bot":
                last_bot_text = str(entry.get("text") or "").lower()
                break

        if last_bot_text:
            # Complaint flow prompts
            complaint_prompts = (
                "what is your full name",
                "i can help report this issue",
                "what area or address",
                "please describe the water issue",
                "logging your complaint",
            )
            if any(p in last_bot_text for p in complaint_prompts):
                context["active_agent"] = "complaint_agent"
                context["flow_started"] = True
                return True

            # Billing / PIN flow prompts
            billing_prompts = (
                "please enter your 4-digit pin",
                "please provide your account number",
                "please enter your account number",
                "incorrect pin",
                "your account is temporarily locked",
            )
            if any(p in last_bot_text for p in billing_prompts):
                context["active_agent"] = "billing_agent"
                context["flow_started"] = True
                return True

            # Connection flow prompts
            connection_prompts = (
                "please provide your full name",
                "please provide your full address",
                "please provide your phone number",
                "please provide your email",
                "new water connection",
            )
            if any(p in last_bot_text for p in connection_prompts):
                context["active_agent"] = "connection_agent"
                context["flow_started"] = True
                return True

        return False

    def _format_response(self, reply_text: str, context: dict) -> dict:
        """Standardize response format."""
        return {
            "response": reply_text,
            "intent": context.get("intent"),
            "confidence": context.get("confidence", 0.0),
            "entities": context.get("entities", {}),
            "active_agent": context.get("active_agent"),
            "escalated": context.get("escalated", False),
            "tool_used": context.get("last_tool_used"),
            "tool_reason": context.get("last_tool_reason"),
            "tool_trace": context.get("tool_trace", []),
        }


    async def _get_llm_fallback(self, message: str, context: dict = {}) -> str:
        """Direct LLM chat when no specific agent flow is active.

        When Groq is unreachable, uses the offline keyword classifier to detect
        intent and returns a structured deterministic response so the bot stays
        useful without internet.
        """
        import requests as _requests
        from .offline_classifier import classify_offline, is_groq_reachable, OFFLINE_RESPONSES

        try:
            return generate_response(message, {}, intent="general_chat", max_tokens=140)
        except _requests.Timeout:
            logger.warning("LLM timeout in _get_llm_fallback")
            return (
                "I'm taking a little longer than usual. Please try again in a moment."
            )
        except Exception as exc:
            logger.warning(f"LLM fallback unavailable; using offline keyword fallback err={exc}")

            # Use offline classifier to give a more relevant response
            offline_result = classify_offline(message)
            offline_intent = offline_result.get("intent", "general_chat")

            # For intents that have structured flows, route to the agent
            # (the agent will use local SQLite — no internet needed)
            structured_intents = {
                "report_fault", "leak_report", "complaint_followup",
                "billing_inquiry", "payment_info", "office_info",
                "new_connection", "meter_problem", "escalation",
            }
            if offline_intent in structured_intents:
                # Update context with the offline-detected intent so the agent
                # can handle it properly
                context["intent"] = offline_intent
                context["last_intent_result"] = offline_result
                try:
                    return await self._handle_new_intent(message, context)
                except Exception as inner_exc:
                    logger.warning(f"Offline agent routing failed err={inner_exc}")

            # Generic offline greeting / help menu
            return OFFLINE_RESPONSES.get(
                "general_chat",
                "I'm an AI assistant for water utility services. "
                "I can help with billing, faults, complaints, payments, and connections. "
                "Type 'human agent' to speak with a representative."
            )

    async def _get_out_of_scope_response(self, message: str) -> str:
        """Decline unrelated requests without relying on Groq."""

        try:
            return generate_response(
                message,
                {},
                intent="out_of_scope",
                additional_instructions=(
                    "Politely say you can only assist with water utility services. "
                    "Do not answer the unrelated request."
                ),
                max_tokens=100,
            )
        except Exception as exc:
            logger.warning(f"LLM unavailable for out-of-scope response; using deterministic fallback err={exc}")
            return (
                "I can only assist with water utility services such as billing, faults, "
                "complaints, payments, office information, and new connections."
            )


    async def _handle_with_agent(self, agent, message: str, context: dict) -> str:
        """Handle request with specific agent."""
        # Get agent decision
        decision = await agent.handle(message, context)

        # Check if tool execution is needed
        if decision.get("requires_tool"):
            tool_result = await self.tool_executor.execute(
                decision["tool_name"],
                decision.get("parameters", {}),
                context
            )

            # Pass tool result back to agent for final response
            final_decision = await agent.handle_with_tool_result(message, context, tool_result)
            return final_decision.get("reply", "I apologize, but I encountered an error.")

        # No tool needed, return direct response
        return decision.get("reply", "I apologize, but I encountered an error.")



# Global orchestrator instance
if __name__ == "__main__":
    from .context_engine import ContextManager
    from .intent_pipeline import IntentPipeline
    from .tool_executor import ToolExecutor
    from .config import Config

    config = Config()
    context_manager = ContextManager()
    intent_pipeline = IntentPipeline()
    tool_executor = ToolExecutor()

    orchestrator = Orchestrator(config, context_manager, intent_pipeline, tool_executor)
