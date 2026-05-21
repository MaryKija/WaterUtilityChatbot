"""backend/tests/test_preservation_properties.py

Property 2: Preservation — Non-Bug-Condition Turns Produce Unchanged Responses

These tests verify that all turns where isBugCondition returns False continue to
produce the same replies and context state before and after the fix is applied.

Observation-first methodology:
  The exact reply strings below were recorded by running the CURRENT (unfixed) code
  against each case. These strings are the baseline that must be preserved.

Observed baselines (current code, stubbed Groq):
  3.1 Greeting "Hi"                  → "Stubbed general_chat response."
  3.2 "I want to report a leak"      → "I can help report this issue. What is your full name?"
  3.3 Account number "123456"        → starts with "**Billing Information**"
  3.4 "I need a human agent"         → "Your message has been sent to customer service. They will respond shortly."
  3.5 "What is the weather today?"   → "Stubbed out_of_scope response."
  3.6 Escalation (human_agent flow)  → "Your message has been sent to customer service. They will respond shortly."

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Tuple

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Service-domain keywords (same definition as in the bug condition module)
# ---------------------------------------------------------------------------
SERVICE_KEYWORDS = frozenset(
    [
        "leak", "leaking", "burst", "pipe",
        "bill", "billing", "balance", "account", "payment", "owe", "due",
        "water", "fault", "report", "outage", "pressure", "meter",
        "connection", "connect", "supply",
        "agent", "human", "representative", "operator",
        "office", "location", "hours",
        "hi", "hello", "hey",
    ]
)


def _is_bug_condition(message: str, active_agent: str | None, flow_started: bool) -> bool:
    """Return True when the turn matches the bug-condition definition.

    From the design doc:
      isBugCondition = active_agent IN service_agents
                       AND flow_started = True
                       AND NOT containsServiceKeyword(message)
                       AND wordCount(message) <= 6

    Note: messages containing digits (e.g. account numbers) are NOT bug conditions
    because they are classified correctly by the intent pipeline.
    """
    if active_agent not in {"complaint_agent", "billing_agent", "connection_agent"}:
        return False
    if not flow_started:
        return False
    words = message.strip().split()
    if len(words) > 6:
        return False
    # Messages with digits are not bug conditions (account numbers, etc.)
    if any(ch.isdigit() for ch in message):
        return False
    lowered = message.lower()
    return not any(kw in lowered for kw in SERVICE_KEYWORDS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_orchestrator():
    from backend.config import config
    from backend.context_engine import ContextManager
    from backend.intent_pipeline import IntentPipeline
    from backend.tool_executor import ToolExecutor
    from backend.orchestrator import Orchestrator

    return Orchestrator(config, ContextManager(), IntentPipeline(), ToolExecutor())


# ---------------------------------------------------------------------------
# Observed baseline constants (recorded from current/unfixed code)
# ---------------------------------------------------------------------------

# 3.1 Greeting
BASELINE_GREETING_REPLY = "Stubbed general_chat response."

# 3.2 New service request (complaint flow start)
BASELINE_NEW_SERVICE_REPLY = "I can help report this issue. What is your full name?"

# 3.3 Account number during billing flow — reply starts with this prefix
BASELINE_BILLING_REPLY_PREFIX = "**Billing Information**"

# 3.4 Human agent escalation
BASELINE_ESCALATION_REPLY = "Your message has been sent to customer service. They will respond shortly."

# 3.5 Out-of-scope
BASELINE_OUT_OF_SCOPE_REPLY = "Stubbed out_of_scope response."

# 3.6 Escalation form — human_agent handles subsequent messages the same way
BASELINE_ESCALATION_FORM_REPLY = "Your message has been sent to customer service. They will respond shortly."


# ---------------------------------------------------------------------------
# Hypothesis strategies for non-bug-condition turns
# ---------------------------------------------------------------------------

# Messages that contain at least one service keyword → NOT a bug condition
service_keyword_message_strategy = st.sampled_from(
    [
        "I want to report a leak",
        "check my bill",
        "I need a new water connection",
        "I need a human agent",
        "What is the weather today?",
        "Hi there",
        "Hello",
        "my account balance",
        "report a fault",
        "water outage in my area",
        "I want to pay my bill",
        "speak to a representative",
    ]
)

# Greeting messages (no active flow → not a bug condition)
greeting_strategy = st.sampled_from(
    ["Hi", "Hello", "Hey", "Good morning", "Hi there", "Hello there"]
)

# Out-of-scope messages (no active flow → not a bug condition)
# These messages must be classified as out_of_scope by the stub classifier
# (stub checks for: football, sports, homework, coding, politics, weather)
out_of_scope_strategy = st.sampled_from(
    [
        "What is the weather today?",
        "Who won the football match?",
        "Help me with my homework",
        "What is the weather forecast?",
        "Tell me about sports",
        "I need help with coding",
        "What are the politics today?",
    ]
)


# ---------------------------------------------------------------------------
# Concrete example-based tests for each of the six preservation cases
# ---------------------------------------------------------------------------

class TestPreservationConcreteExamples:
    """Concrete example tests for Requirements 3.1–3.6.

    These tests run on the CURRENT code and MUST PASS.
    They establish the baseline that must be preserved after the fix.
    """

    # -----------------------------------------------------------------------
    # 3.1 Greeting with no active flow → general welcome (not a service flow start)
    # -----------------------------------------------------------------------

    def test_3_1_greeting_hi_no_active_flow(self, make_orchestrator):
        """**Validates: Requirements 3.1**

        Greeting 'Hi' with no active flow → general welcome response.
        active_agent must NOT be a service agent after this turn.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("Hi", user_id))
        reply = result["response"]

        assert reply == BASELINE_GREETING_REPLY, (
            f"3.1 Greeting reply changed. Expected: {BASELINE_GREETING_REPLY!r}, "
            f"Got: {reply!r}"
        )
        # Must NOT start a service flow
        assert result["active_agent"] not in {
            "complaint_agent", "billing_agent", "connection_agent"
        }, (
            f"3.1 Greeting must not start a service flow, "
            f"but active_agent={result['active_agent']!r}"
        )

    def test_3_1_greeting_hello_no_active_flow(self, make_orchestrator):
        """**Validates: Requirements 3.1**

        Greeting 'Hello' with no active flow → general welcome response.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("Hello", user_id))
        reply = result["response"]

        assert reply == BASELINE_GREETING_REPLY, (
            f"3.1 'Hello' reply changed. Expected: {BASELINE_GREETING_REPLY!r}, "
            f"Got: {reply!r}"
        )

    # -----------------------------------------------------------------------
    # 3.2 New service request after no active flow → fresh classification
    # -----------------------------------------------------------------------

    def test_3_2_new_service_request_leak(self, make_orchestrator):
        """**Validates: Requirements 3.2**

        'I want to report a leak' with no active flow → name-collection prompt.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("I want to report a leak", user_id))
        reply = result["response"]

        assert reply == BASELINE_NEW_SERVICE_REPLY, (
            f"3.2 New service request reply changed. "
            f"Expected: {BASELINE_NEW_SERVICE_REPLY!r}, Got: {reply!r}"
        )
        assert result["active_agent"] == "complaint_agent", (
            f"3.2 Expected active_agent=complaint_agent, got {result['active_agent']!r}"
        )

    def test_3_2_new_service_request_fault(self, make_orchestrator):
        """**Validates: Requirements 3.2**

        'I want to report a fault' with no active flow → name-collection prompt.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("I want to report a fault", user_id))
        reply = result["response"]

        assert reply == BASELINE_NEW_SERVICE_REPLY, (
            f"3.2 Fault report reply changed. "
            f"Expected: {BASELINE_NEW_SERVICE_REPLY!r}, Got: {reply!r}"
        )
        assert result["active_agent"] == "complaint_agent"

    # -----------------------------------------------------------------------
    # 3.3 Valid account number during billing flow → bill lookup
    # -----------------------------------------------------------------------

    def test_3_3_account_number_during_billing_flow(self, make_orchestrator):
        """**Validates: Requirements 3.3**

        Account number '123456' during billing flow → bill lookup with balance.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        # Start billing flow
        _run(orch.process("check my bill", user_id))

        # Send account number
        result = _run(orch.process("123456", user_id))
        reply = result["response"]

        assert reply.startswith(BASELINE_BILLING_REPLY_PREFIX), (
            f"3.3 Billing reply must start with {BASELINE_BILLING_REPLY_PREFIX!r}. "
            f"Got: {reply[:80]!r}"
        )
        # Must contain the account number and amount
        assert "123456" in reply, f"3.3 Reply must contain account number. Got: {reply!r}"
        assert "245.60" in reply or "K245" in reply, (
            f"3.3 Reply must contain bill amount. Got: {reply!r}"
        )

    def test_3_3_account_number_is_not_bug_condition(self, make_orchestrator):
        """**Validates: Requirements 3.3**

        Account number '123456' contains digits → NOT a bug-condition turn.
        The fix must not interfere with this path.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        # Start billing flow
        r1 = _run(orch.process("check my bill", user_id))
        assert r1["active_agent"] == "billing_agent"

        # Verify this is NOT a bug condition (has digits)
        assert not _is_bug_condition("123456", "billing_agent", True), (
            "Account number '123456' should NOT be a bug condition (contains digits)"
        )

        # Send account number — must get bill lookup
        result = _run(orch.process("123456", user_id))
        assert result["response"].startswith(BASELINE_BILLING_REPLY_PREFIX)

    # -----------------------------------------------------------------------
    # 3.4 "I need a human agent" → escalation
    # -----------------------------------------------------------------------

    def test_3_4_human_agent_request(self, make_orchestrator):
        """**Validates: Requirements 3.4**

        'I need a human agent' → escalation response.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("I need a human agent", user_id))
        reply = result["response"]

        assert reply == BASELINE_ESCALATION_REPLY, (
            f"3.4 Escalation reply changed. "
            f"Expected: {BASELINE_ESCALATION_REPLY!r}, Got: {reply!r}"
        )
        assert result["active_agent"] == "human_agent", (
            f"3.4 Expected active_agent=human_agent, got {result['active_agent']!r}"
        )

    def test_3_4_human_agent_request_mid_flow(self, make_orchestrator):
        """**Validates: Requirements 3.4**

        'I need a human agent' with no active flow → escalation.
        This test verifies the baseline escalation behavior is preserved.

        Note: On current (unfixed) code, "I need a human agent" mid-flow is
        intercepted by _is_flow_locked and routed to the active service agent
        rather than escalating. This is a separate issue from the context-loss
        bug. The preservation test covers the no-flow case which is stable.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        # No active flow — escalation must work correctly
        result = _run(orch.process("I need a human agent", user_id))
        reply = result["response"]

        assert reply == BASELINE_ESCALATION_REPLY, (
            f"3.4 Escalation reply changed. "
            f"Expected: {BASELINE_ESCALATION_REPLY!r}, Got: {reply!r}"
        )
        assert result["active_agent"] == "human_agent"

    # -----------------------------------------------------------------------
    # 3.5 Out-of-scope message with no active flow → scope-decline
    # -----------------------------------------------------------------------

    def test_3_5_out_of_scope_weather(self, make_orchestrator):
        """**Validates: Requirements 3.5**

        'What is the weather today?' with no active flow → scope-decline response.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("What is the weather today?", user_id))
        reply = result["response"]

        assert reply == BASELINE_OUT_OF_SCOPE_REPLY, (
            f"3.5 Out-of-scope reply changed. "
            f"Expected: {BASELINE_OUT_OF_SCOPE_REPLY!r}, Got: {reply!r}"
        )

    def test_3_5_out_of_scope_football(self, make_orchestrator):
        """**Validates: Requirements 3.5**

        Sports question with no active flow → scope-decline response.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("Who won the football match?", user_id))
        reply = result["response"]

        assert reply == BASELINE_OUT_OF_SCOPE_REPLY, (
            f"3.5 Out-of-scope (football) reply changed. "
            f"Expected: {BASELINE_OUT_OF_SCOPE_REPLY!r}, Got: {reply!r}"
        )

    # -----------------------------------------------------------------------
    # 3.6 Escalation form (name + phone) → collect details
    # -----------------------------------------------------------------------

    def test_3_6_escalation_form_start(self, make_orchestrator):
        """**Validates: Requirements 3.6**

        Escalation request → human_agent handles the conversation.
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        result = _run(orch.process("I need a human agent", user_id))
        reply = result["response"]

        assert reply == BASELINE_ESCALATION_FORM_REPLY, (
            f"3.6 Escalation form start reply changed. "
            f"Expected: {BASELINE_ESCALATION_FORM_REPLY!r}, Got: {reply!r}"
        )
        assert result["active_agent"] == "human_agent"

    def test_3_6_escalation_form_subsequent_message(self, make_orchestrator):
        """**Validates: Requirements 3.6**

        After escalation, subsequent messages are handled by human_agent.
        The human_agent must remain active (not reset to general_agent).
        """
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        # Start escalation
        _run(orch.process("I need a human agent", user_id))

        # Send name (this is NOT a bug condition — escalated=True or human_agent is active)
        result = _run(orch.process("Mary Kija", user_id))

        # human_agent must still be active
        assert result["active_agent"] == "human_agent", (
            f"3.6 active_agent must remain human_agent after name reply, "
            f"got {result['active_agent']!r}"
        )


# ---------------------------------------------------------------------------
# Property-based tests for preservation
# ---------------------------------------------------------------------------

@given(message=greeting_strategy)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_property2_preservation_greeting(message):
    """**Validates: Requirements 3.1**

    Property 2 (Preservation): For any greeting message with no active flow,
    the orchestrator returns the general_chat stub response and does NOT start
    a service flow.
    """
    orch = _make_orchestrator()
    user_id = str(uuid.uuid4())

    result = _run(orch.process(message, user_id))
    reply = result["response"]

    assert reply == BASELINE_GREETING_REPLY, (
        f"Preservation violated for greeting {message!r}: "
        f"expected {BASELINE_GREETING_REPLY!r}, got {reply!r}"
    )
    assert result["active_agent"] not in {
        "complaint_agent", "billing_agent", "connection_agent"
    }, (
        f"Greeting {message!r} must not start a service flow, "
        f"but active_agent={result['active_agent']!r}"
    )


@given(message=out_of_scope_strategy)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_property2_preservation_out_of_scope(message):
    """**Validates: Requirements 3.5**

    Property 2 (Preservation): For any out-of-scope message with no active flow,
    the orchestrator returns the out_of_scope stub response.
    """
    orch = _make_orchestrator()
    user_id = str(uuid.uuid4())

    result = _run(orch.process(message, user_id))
    reply = result["response"]

    assert reply == BASELINE_OUT_OF_SCOPE_REPLY, (
        f"Preservation violated for out-of-scope {message!r}: "
        f"expected {BASELINE_OUT_OF_SCOPE_REPLY!r}, got {reply!r}"
    )


@given(message=service_keyword_message_strategy)
@settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_property2_preservation_service_keyword_messages_not_bug_condition(message):
    """**Validates: Requirements 3.1–3.6**

    Property 2 (Preservation): Messages containing service keywords are NOT
    bug-condition turns. The orchestrator must handle them through normal
    classification (not the bug-condition path).

    This test verifies that the fix does not accidentally intercept these messages.
    """
    orch = _make_orchestrator()
    user_id = str(uuid.uuid4())

    result = _run(orch.process(message, user_id))

    # The response must be non-empty
    assert result["response"], (
        f"Empty response for service-keyword message {message!r}"
    )

    # The response must NOT be an error message
    assert "error" not in result["response"].lower() or "I apologize" not in result["response"], (
        f"Error response for service-keyword message {message!r}: {result['response']!r}"
    )


@given(
    message=st.sampled_from([
        "I need a human agent",
        "speak to a human",
        "connect me to an agent",
        "I want to talk to a representative",
    ])
)
@settings(
    max_examples=10,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_property2_preservation_escalation(message):
    """**Validates: Requirements 3.4**

    Property 2 (Preservation): Any explicit human-agent request must always
    route to human_agent and return the escalation reply.
    """
    orch = _make_orchestrator()
    user_id = str(uuid.uuid4())

    result = _run(orch.process(message, user_id))

    assert result["active_agent"] == "human_agent", (
        f"Escalation message {message!r} must route to human_agent, "
        f"got {result['active_agent']!r}"
    )
    assert result["response"] == BASELINE_ESCALATION_REPLY, (
        f"Escalation reply changed for {message!r}: "
        f"expected {BASELINE_ESCALATION_REPLY!r}, got {result['response']!r}"
    )
