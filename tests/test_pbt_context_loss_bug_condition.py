"""
Property-Based Test — Bug Condition Exploration
================================================
Task 1: Write bug condition exploration test

**Validates: Requirements 1.1, 1.2, 1.3**

Property 1: Bug Condition — Context Loss on Short Plain-Text Flow Reply

This test MUST FAIL on unfixed code.
Failure confirms the bug exists: a short plain-text reply during an active
complaint flow is misrouted as a new intent when context is not correctly
persisted, causing the bot to respond with a generic greeting instead of
continuing the flow.

Root Cause Being Tested:
  - Root Cause 2: `_is_flow_locked` returns False when context was not persisted
  - Root Cause 3: Intent pipeline re-classifies short plain-text replies as
    `general_chat`, routing to GeneralAgent which returns "How can I assist you?"
  - Root Cause 4: `_capture_step_reply` guard `step == "collect_name"` fails
    when step is not persisted

Bug Condition Simulation:
  The test simulates the stale-context scenario by:
  1. Running Turn 1 to start the complaint flow (sets active_agent, flow_started, step)
  2. Simulating a stale context load by clearing active_agent and flow_started from
     SQLite (as would happen if context was not persisted between turns)
  3. Running Turn 2 with the generated short plain-text message
  4. Asserting that Turn 2 is handled as a flow continuation (not a new intent)

EXPECTED OUTCOME: FAIL on unfixed code (confirms the bug exists).
DO NOT fix the test or the code when it fails.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Service-domain keywords to exclude from generated messages
# (these would trigger intent classification rather than flow continuation)
# ---------------------------------------------------------------------------
SERVICE_KEYWORDS = {
    "leak",
    "bill",
    "water",
    "fault",
    "account",
    "meter",
    "connection",
    "report",
    "outage",
    "payment",
    "balance",
    "pipe",
    "supply",
    "pressure",
    "complaint",
    "service",
    "issue",
    "problem",
    "help",
    "assist",
    "human",
    "agent",
    "office",
    "repair",
    "fix",
    "broken",
}

# Generic greeting phrases that indicate the bug has fired
GENERIC_GREETING_PHRASES = [
    "how can i assist",
    "how can i help you today",
    "how may i assist",
    "how can i help",
    "how may i help",
]


def _contains_service_keyword(message: str) -> bool:
    """Return True if the message contains any service-domain keyword."""
    lowered = message.lower()
    return any(kw in lowered for kw in SERVICE_KEYWORDS)


def _contains_generic_greeting(reply: str) -> bool:
    """Return True if the reply contains a generic greeting phrase (bug indicator)."""
    lowered = (reply or "").lower()
    return any(phrase in lowered for phrase in GENERIC_GREETING_PHRASES)


# ---------------------------------------------------------------------------
# Hypothesis strategy: short alphabetic messages with no service keywords
# ---------------------------------------------------------------------------
short_plain_message_strategy = (
    st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Zs"),  # uppercase, lowercase, spaces
        ),
        min_size=2,
        max_size=40,
    )
    .map(str.strip)
    .filter(lambda m: len(m) >= 2)                          # at least 2 chars after strip
    .filter(lambda m: not _contains_service_keyword(m))     # no service keywords
    .filter(lambda m: len(m.split()) <= 6)                  # at most 6 words
    .filter(lambda m: any(c.isalpha() for c in m))          # must have at least one letter
)


# ---------------------------------------------------------------------------
# Helper: run the orchestrator's process() coroutine synchronously
# ---------------------------------------------------------------------------
def _run_process(orchestrator, message: str, user_id: str) -> dict:
    """Run orchestrator.process() and return the full response dict."""
    return asyncio.run(orchestrator.process(message, user_id))


def _simulate_stale_context(user_id: str) -> None:
    """
    Simulate the bug condition: clear active_agent and flow_started from SQLite.

    This replicates what happens when context is not correctly persisted between
    turns (Root Cause 1 from the design doc). In the real bug, the final save
    (which includes history) runs, but the early save (which persists active_agent
    and flow_started) was conditional and did NOT run. So history is preserved
    but active_agent and flow_started are absent.

    After this call, load_context will return a context with active_agent=None
    and flow_started=False, causing _is_flow_locked to fall back to history-based
    recovery.
    """
    from backend.storage import get_session_context, upsert_session_context
    # Load the current context (which has history from Turn 1)
    current = get_session_context(user_id)
    if not isinstance(current, dict):
        current = {}
    # Simulate the bug: wipe only the flow-state fields, preserve history
    # (in the real bug, history was saved by the final save_context call,
    # but active_agent/flow_started were not saved because the early save
    # was conditional)
    current["active_agent"] = None
    current["flow_started"] = False
    current["step"] = 0
    current["entities"] = {}
    current["escalated"] = False
    upsert_session_context(user_id, current)


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------
@given(name_reply=short_plain_message_strategy)
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_property1_bug_condition_context_loss_on_short_plain_reply(
    name_reply: str,
    isolated_sqlite_db,  # noqa: F811 — injected by conftest autouse fixture
) -> None:
    """
    **Validates: Requirements 1.1, 1.2, 1.3**

    Property 1: Bug Condition — Context Loss on Short Plain-Text Flow Reply

    Simulates a two-turn conversation with a stale context load between turns:
      Turn 1: "I want to report a water leak"  → starts complaint flow
      [Simulate stale context: clear active_agent and flow_started from SQLite]
      Turn 2: <generated short plain-text message>  → should be treated as name reply

    The stale context simulation replicates Root Cause 1 (context not persisted),
    which causes Root Cause 2 (_is_flow_locked returns False), which triggers
    Root Cause 3 (intent pipeline re-classifies as general_chat).

    Asserts (on FIXED code — expected to FAIL on unfixed code):
      - Turn 2 reply does NOT contain generic greeting phrases
      - context["active_agent"] == "complaint_agent" after Turn 2
      - context["flow_started"] is True after Turn 2

    EXPECTED OUTCOME: FAIL on unfixed code (confirms the bug exists).
    """
    from backend.orchestrator import Orchestrator
    from backend.context_engine import context_manager
    from backend.intent_pipeline import intent_pipeline
    from backend.tool_executor import tool_executor
    from backend.config import config

    # Use a unique user_id per example to avoid cross-contamination
    user_id = f"pbt-bug-{uuid4().hex}"

    orchestrator = Orchestrator(
        config=config,
        context_manager=context_manager,
        intent_pipeline=intent_pipeline,
        tool_executor=tool_executor,
    )

    # ------------------------------------------------------------------
    # Turn 1: Start the complaint flow
    # ------------------------------------------------------------------
    turn1_response = _run_process(orchestrator, "I want to report a water leak", user_id)
    # The orchestrator returns {"response": ..., "intent": ..., ...}
    turn1_reply = turn1_response.get("response", "") or turn1_response.get("reply", "")

    # Sanity check: Turn 1 should ask for the user's name
    # (If this fails, the test environment itself is broken — not the bug under test)
    assert "full name" in turn1_reply.lower() or "name" in turn1_reply.lower(), (
        f"Turn 1 sanity check failed: expected name prompt, got: {turn1_reply!r}\n"
        f"Full response: {turn1_response!r}"
    )

    # ------------------------------------------------------------------
    # Simulate the bug condition: stale context load
    # This replicates Root Cause 1 — context not persisted between turns.
    # After this, _is_flow_locked will return False for Turn 2, routing it
    # to _handle_new_intent instead of _handle_active_flow.
    # ------------------------------------------------------------------
    _simulate_stale_context(user_id)

    # ------------------------------------------------------------------
    # Turn 2: Send the generated short plain-text message as the name reply
    # The bug fires here: _is_flow_locked returns False (stale context),
    # _handle_new_intent classifies "Mary Kija" as general_chat,
    # GeneralAgent returns "How can I assist you?"
    # ------------------------------------------------------------------
    turn2_response = _run_process(orchestrator, name_reply, user_id)
    turn2_reply = turn2_response.get("response", "") or turn2_response.get("reply", "")

    # Load context after Turn 2 to inspect state
    ctx_after = context_manager.load_context(user_id)

    # ------------------------------------------------------------------
    # Assertions (encode the EXPECTED / CORRECT behavior)
    # These will FAIL on unfixed code — that is the intended outcome.
    # ------------------------------------------------------------------

    # 1. The reply must NOT be a generic greeting (bug indicator)
    assert not _contains_generic_greeting(turn2_reply), (
        f"BUG CONFIRMED: Turn 2 reply is a generic greeting.\n"
        f"  name_reply={name_reply!r}\n"
        f"  turn2_reply={turn2_reply!r}\n"
        f"  active_agent after Turn 2: {ctx_after.get('active_agent')!r}\n"
        f"  flow_started after Turn 2: {ctx_after.get('flow_started')!r}"
    )

    # 2. active_agent must still be "complaint_agent" (not reset to None or general_agent)
    assert ctx_after.get("active_agent") == "complaint_agent", (
        f"BUG CONFIRMED: active_agent was reset.\n"
        f"  name_reply={name_reply!r}\n"
        f"  turn2_reply={turn2_reply!r}\n"
        f"  active_agent after Turn 2: {ctx_after.get('active_agent')!r}\n"
        f"  flow_started after Turn 2: {ctx_after.get('flow_started')!r}"
    )

    # 3. flow_started must still be True (not cleared)
    assert ctx_after.get("flow_started") is True, (
        f"BUG CONFIRMED: flow_started was cleared.\n"
        f"  name_reply={name_reply!r}\n"
        f"  turn2_reply={turn2_reply!r}\n"
        f"  active_agent after Turn 2: {ctx_after.get('active_agent')!r}\n"
        f"  flow_started after Turn 2: {ctx_after.get('flow_started')!r}"
    )
