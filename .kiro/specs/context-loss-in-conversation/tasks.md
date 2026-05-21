# Implementation Plan

## Overview

Fix the four root causes of context loss in multi-step conversation flows for the Water Utility Assistant chatbot. The workflow follows the exploratory bugfix methodology: write tests before the fix to confirm the bug, then implement the four targeted changes, then verify both fix and preservation properties hold.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2"] },
    { "wave": 2, "tasks": ["3"] },
    { "wave": 3, "tasks": ["4"] }
  ]
}
```

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Context Loss on Short Plain-Text Flow Reply
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate that a short plain-text reply during an active flow is misrouted as a new intent
  - **Scoped PBT Approach**: Scope the property to the concrete failing cases — messages of 1–6 words containing no service keywords, sent while `active_agent="complaint_agent"` and `flow_started=True`
  - Use `hypothesis` with a custom strategy that generates short alphabetic messages (2–40 chars, no service-domain keywords such as "leak", "bill", "water", "fault", "account", "meter", "connection", "report")
  - Simulate a two-turn conversation: Turn 1 starts the complaint flow ("I want to report a water leak"); Turn 2 sends the generated short message as the name reply
  - Assert that the reply from Turn 2 does NOT contain any of: `"how can I assist"`, `"how can I help you today"`, `"how may I assist"`
  - Assert that `context["active_agent"] == "complaint_agent"` after Turn 2
  - Assert that `context["flow_started"] is True` after Turn 2
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
  - Document counterexamples found (e.g., `"Mary Kija"` → reply is `"How can I assist you?"`, `active_agent` is `None`)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Bug-Condition Turns Produce Unchanged Responses
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for turns where `isBugCondition` returns `False`:
    - Observe: greeting "Hi" with no active flow → general welcome response
    - Observe: "I want to report a leak" with no active flow → name-collection prompt
    - Observe: "I need a human agent" at any point → escalation response
    - Observe: out-of-scope message "What is the weather today?" with no active flow → scope-decline response
  - Record the exact reply strings returned by the unfixed orchestrator for each observed case
  - Write property-based tests using `hypothesis` that generate turns where `isBugCondition` returns `False` (e.g., messages containing service keywords, messages with `active_agent=None`, messages with `flow_started=False`) and assert the fixed orchestrator returns the same reply as the original
  - Include concrete example-based tests for each of the six preservation cases (Requirements 3.1–3.6)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Fix context loss in multi-step conversation flows

  - [x] 3.1 Fix 1 — Remove conditional context save guard in `Orchestrator.process` (orchestrator.py)
    - Locate the block in `Orchestrator.process` (~line 388) that conditionally saves context only when `not active_agent and not flow_started`
    - Replace the conditional early save with an unconditional `save_context` call immediately after `_handle_new_intent` or `_handle_active_flow` returns, before `update_context_with_history` is called
    - Ensure `context["user_id"]` and `context["session_id"]` are stamped onto the dict before this early save
    - Keep the existing final `save_context` call after `update_context_with_history` (the second save persists the bot reply in history)
    - This guarantees that `active_agent` and `flow_started` are written to SQLite at the end of Turn N so that Turn N+1 reads them correctly
    - _Bug_Condition: `isBugCondition(turn)` where `context.active_agent IN {"complaint_agent","billing_agent","connection_agent"}` AND `context.flow_started = True`_
    - _Expected_Behavior: `_is_flow_locked` returns `True` on Turn N+1 because the persisted row contains `active_agent` and `flow_started`_
    - _Preservation: All turns where `isBugCondition` returns `False` are unaffected — the unconditional save is a no-op change for those paths_
    - _Requirements: 1.3, 2.2, 2.3_

  - [x] 3.2 Fix 2 — Add flow-continuation guard at the top of `_handle_new_intent` (orchestrator.py)
    - At the very start of `Orchestrator._handle_new_intent`, before any call to `intent_pipeline.classify`, add a guard that checks whether `context.get("active_agent")` is already in `{"complaint_agent", "billing_agent", "connection_agent", "info_agent"}`
    - If the guard fires, immediately delegate to `self._handle_active_flow(message, context)` and return its result without running the intent pipeline
    - This prevents a stale-load race (Root Cause 2) from allowing the intent pipeline to overwrite a service agent with `general_agent`
    - _Bug_Condition: `context.active_agent` is a service agent but `_is_flow_locked` returned `False` due to a stale context load_
    - _Expected_Behavior: The turn is routed to `_handle_active_flow` regardless of what the classifier would return_
    - _Preservation: The guard only fires when `active_agent` is already a service agent; all other paths (new intents, general chat) are unchanged_
    - _Requirements: 1.2, 1.3, 2.2_

  - [x] 3.3 Fix 3 — Persist `step` immediately after `update_context_with_step` in `ComplaintAgent.handle` and `ConnectionAgent.handle` (orchestrator.py)
    - In `ComplaintAgent.handle`, after each call to `context_manager.update_context_with_step(context, ...)` (for `"collect_name"`, `"collect_area"`, `"collect_issue"`, and `"log_complaint"`), add an immediate `context_manager.save_context(context.get("user_id", "unknown"), context)` call before the `return` statement
    - Apply the same pattern in `ConnectionAgent.handle` after each `update_context_with_step` call for each of the four connection fields
    - This ensures the `step` value is durably written to SQLite so that `_capture_step_reply` on the next turn reads the correct step
    - _Bug_Condition: `context["step"]` is not persisted between turns, so `_capture_step_reply` guard `step == "collect_name"` never matches_
    - _Expected_Behavior: `context["step"] == "collect_name"` is present in SQLite at the start of Turn N+1_
    - _Preservation: The extra `save_context` calls are additive; they do not alter any reply or routing logic_
    - _Requirements: 1.4, 2.1, 2.4_

  - [x] 3.4 Fix 4 — Relax `_capture_step_reply` to accept name when `step` is missing (orchestrator.py)
    - In `ComplaintAgent._capture_step_reply`, replace the strict guard `step == "collect_name"` with a compound condition: fire name extraction when `step == "collect_name"` OR when `name` is the next missing field (i.e., `not entities.get("name") and not entities.get("area")`)
    - Apply the same "next missing field" fallback for `area` capture: fire when `step == "collect_area"` OR when `entities.get("name")` is set but `entities.get("area")` is not
    - Apply the same fallback for `issue` capture: fire when `step == "collect_issue"` OR when both `name` and `area` are set but `issue` is not
    - This makes the capture logic resilient to a missing or stale `step` value (Root Cause 4)
    - _Bug_Condition: `context["step"]` is absent or stale, so the strict `step == "collect_name"` guard fails even though name is the next missing field_
    - _Expected_Behavior: `entities["name"]` is populated from the user's reply regardless of whether `step` was persisted_
    - _Preservation: The relaxed guard only fires when the entity is genuinely missing and is the next in sequence; it does not capture values out of order_
    - _Requirements: 1.4, 2.1, 2.4_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Context Loss on Short Plain-Text Flow Reply
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (flow continuation, no generic greeting, `active_agent` preserved, `flow_started` preserved)
    - Run the bug condition exploration test from step 1 against the fixed code
    - **EXPECTED OUTCOME**: Test PASSES (confirms the bug is fixed for all generated short plain-text messages)
    - If the test still fails, identify which of the four fixes is incomplete and revisit the relevant sub-task
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Bug-Condition Turns Produce Unchanged Responses
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run all preservation property tests from step 2 against the fixed code
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in greeting, new service request, account number, escalation, out-of-scope, and escalation-form flows)
    - Confirm all six preservation cases (Requirements 3.1–3.6) still pass after the fix
    - If any preservation test fails, the fix has introduced a regression — revert or narrow the change in the failing sub-task

- [x] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite (`pytest backend/tests/ -v`) and confirm zero failures
  - Confirm the bug condition exploration test (Property 1) passes
  - Confirm all preservation tests (Property 2) pass
  - Confirm all unit tests for `_is_flow_locked`, `_capture_step_reply`, and `context_engine` round-trip pass
  - Confirm integration tests for the full complaint flow (3 turns) and full connection flow (4 turns) pass
  - If any test fails, ask the user before proceeding — do not silently skip or delete failing tests

## Notes

- All property-based tests use the `hypothesis` library (already a dev dependency via `pytest`).
- The exploration test (task 1) is expected to **fail** on unfixed code — that failure is the proof the bug exists. Do not "fix" the test to make it pass; fix the code instead.
- The preservation tests (task 2) are expected to **pass** on unfixed code — they establish the baseline. If they fail on unfixed code, the test strategy needs revision before proceeding.
- The four implementation sub-tasks (3.1–3.4) are independent of each other and can be applied in any order, but all four must be applied before running the verification sub-tasks (3.5–3.6).
- `save_context` calls added in Fix 3 (task 3.3) are additive and do not alter any reply or routing logic; they only ensure durability.
- The relaxed guard in Fix 4 (task 3.4) must not capture entity values out of sequence — the "next missing field" fallback only fires when the entity is genuinely the next one in the `_COMPLAINT_FIELDS` order: `("name", "area", "issue")`.
