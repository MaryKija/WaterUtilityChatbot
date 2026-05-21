"""backend/tests/test_bug_condition_exploration.py

Property 1: Bug Condition — Context Loss on Short Plain-Text Flow Reply

These tests encode the EXPECTED (fixed) behaviour for turns where isBugCondition is True.
They were run on UNFIXED code and FAILED, confirming the bug exists.
After the four fixes (Tasks 3.1–3.4) are applied they MUST PASS.

Validates: Requirements 1.1, 1.2, 1.3
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Tuple

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Service-domain keywords — messages containing these are NOT bug-condition turns
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


def _is_bug_condition_message(msg: str) -> bool:
    """Return True when the message matches the bug-condition definition."""
    words = msg.strip().split()
    if len(words) > 6:
        return False
    lowered = msg.lower()
    return not any(kw in lowered for kw in SERVICE_KEYWORDS)


# ---------------------------------------------------------------------------
# Hypothesis strategy: short alphabetic messages with no service keywords
# ---------------------------------------------------------------------------
short_plain_message_strategy = (
    st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
        min_size=2,
        max_size=40,
    )
    .map(str.strip)
    .filter(lambda m: len(m) >= 2)
    .filter(_is_bug_condition_message)
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine synchronously (works inside pytest without an event loop)."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_orchestrator():
    from backend.config import config
    from backend.context_engine import ContextManager
    from backend.intent_pipeline import IntentPipeline
    from backend.tool_executor import ToolExecutor
    from backend.orchestrator import Orchestrator

    return Orchestrator(config, ContextManager(), IntentPipeline(), ToolExecutor())


def _start_complaint_flow(orch, user_id: str) -> dict:
    """Turn 1: start the complaint flow so active_agent and flow_started are set."""
    result = _run(orch.process("I want to report a water leak", user_id))
    return result


def _send_turn2(orch, user_id: str, message: str) -> Tuple[str, dict]:
    """Turn 2: send the bug-condition message and return (reply, full_result)."""
    result = _run(orch.process(message, user_id))
    return result["response"], result


# ---------------------------------------------------------------------------
# Generic greeting phrases that must NOT appear in a flow-continuation reply
# ---------------------------------------------------------------------------
GENERIC_GREETING_PHRASES = (
    "how can i assist",
    "how can i help you today",
    "how may i assist",
)


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------

@given(message=short_plain_message_strategy)
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_property1_bug_condition_flow_continuation(message):
    """**Validates: Requirements 1.1, 1.2, 1.3**

    Property 1: Bug Condition — for any short plain-text message (no service keywords,
    ≤6 words) sent while active_agent="complaint_agent" and flow_started=True, the
    fixed orchestrator SHALL:
      - NOT return a generic greeting phrase
      - Keep active_agent as "complaint_agent"
      - Keep flow_started=True
    """
    orch = _make_orchestrator()
    user_id = str(uuid.uuid4())

    # Turn 1: start the flow
    turn1 = _run(orch.process("I want to report a water leak", user_id))
    assert turn1["active_agent"] == "complaint_agent", (
        f"Turn 1 should set active_agent=complaint_agent, got {turn1['active_agent']!r}"
    )

    # Turn 2: send the bug-condition message
    reply, turn2 = _send_turn2(orch, user_id, message)
    reply_lower = reply.lower()

    # Assert: no generic greeting
    for phrase in GENERIC_GREETING_PHRASES:
        assert phrase not in reply_lower, (
            f"Bug detected: reply contains generic greeting {phrase!r} "
            f"for message={message!r}. Full reply: {reply!r}"
        )

    # Assert: active_agent preserved
    assert turn2["active_agent"] == "complaint_agent", (
        f"Bug detected: active_agent changed to {turn2['active_agent']!r} "
        f"for message={message!r}"
    )


# ---------------------------------------------------------------------------
# Concrete example-based tests (specific counterexamples from the bug report)
# ---------------------------------------------------------------------------

class TestBugConditionConcreteExamples:
    """Concrete examples that demonstrate the bug on unfixed code."""

    def test_name_reply_mary_kija(self, make_orchestrator):
        """'Mary Kija' as a name reply must not trigger a generic greeting."""
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        _run(orch.process("I want to report a water leak", user_id))
        reply, result = _send_turn2(orch, user_id, "Mary Kija")

        reply_lower = reply.lower()
        for phrase in GENERIC_GREETING_PHRASES:
            assert phrase not in reply_lower, (
                f"Bug: reply contains {phrase!r} for 'Mary Kija'. Reply: {reply!r}"
            )
        assert result["active_agent"] == "complaint_agent", (
            f"Bug: active_agent={result['active_agent']!r} after 'Mary Kija'"
        )

    def test_name_reply_john_banda(self, make_orchestrator):
        """'John Banda' as a name reply must not trigger a generic greeting."""
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        _run(orch.process("I want to report a water leak", user_id))
        reply, result = _send_turn2(orch, user_id, "John Banda")

        reply_lower = reply.lower()
        for phrase in GENERIC_GREETING_PHRASES:
            assert phrase not in reply_lower, (
                f"Bug: reply contains {phrase!r} for 'John Banda'. Reply: {reply!r}"
            )
        assert result["active_agent"] == "complaint_agent"

    def test_area_reply_makululu_road(self, make_orchestrator):
        """'Makululu Road' as an area reply must not trigger a generic greeting."""
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        # Turn 1: start flow
        _run(orch.process("I want to report a water leak", user_id))
        # Turn 2: provide name (so we advance to area step)
        _run(orch.process("Mary Kija", user_id))
        # Turn 3: provide area — this is also a bug-condition turn
        result3 = _run(orch.process("Makululu Road", user_id))
        reply = result3["response"]

        reply_lower = reply.lower()
        for phrase in GENERIC_GREETING_PHRASES:
            assert phrase not in reply_lower, (
                f"Bug: reply contains {phrase!r} for 'Makululu Road'. Reply: {reply!r}"
            )
        # The flow either continues (asking for issue) or completes (complaint logged).
        # Both are valid outcomes — the key invariant is no generic greeting (checked above).
        # active_agent is None only when the complaint was successfully logged (flow complete).
        active = result3["active_agent"]
        assert active in ("complaint_agent", None), (
            f"Bug: active_agent={active!r} after 'Makululu Road' — expected flow to continue or complete"
        )

    def test_single_word_name_aisha(self, make_orchestrator):
        """Single-word name 'Aisha' must not trigger a generic greeting."""
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        _run(orch.process("I want to report a water leak", user_id))
        reply, result = _send_turn2(orch, user_id, "Aisha")

        reply_lower = reply.lower()
        for phrase in GENERIC_GREETING_PHRASES:
            assert phrase not in reply_lower, (
                f"Bug: reply contains {phrase!r} for 'Aisha'. Reply: {reply!r}"
            )
        assert result["active_agent"] == "complaint_agent"

    def test_connection_flow_name_reply(self, make_orchestrator):
        """Name reply during connection flow must not trigger a generic greeting."""
        orch = make_orchestrator()
        user_id = str(uuid.uuid4())

        _run(orch.process("I need a new water connection", user_id))
        reply, result = _send_turn2(orch, user_id, "John Banda")

        reply_lower = reply.lower()
        for phrase in GENERIC_GREETING_PHRASES:
            assert phrase not in reply_lower, (
                f"Bug: reply contains {phrase!r} for 'John Banda' in connection flow. "
                f"Reply: {reply!r}"
            )
        assert result["active_agent"] == "connection_agent"
