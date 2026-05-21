# Context Loss in Conversation — Bugfix Design

## Overview

The Water Utility Assistant loses conversational context between turns during multi-step service
flows. When the bot asks "What is your full name?" and the user replies "Mary Kija", the system
ignores the reply and responds with a generic "How can I assist you?" message, effectively
restarting the conversation. This breaks every multi-step flow: leak reports, fault reports,
billing inquiries, and new connection requests.

The fix targets four distinct failure points across three components:

1. **`orchestrator.py` — `_is_flow_locked`**: the guard that should prevent re-classification
   during an active flow is bypassed when context is not correctly persisted or reloaded.
2. **`context_engine.py` — `load_context` / `save_context`**: `active_agent` and `flow_started`
   are not always written back to SQLite before the next turn reads them.
3. **`orchestrator.py` — `_handle_new_intent`**: even when `_is_flow_locked` returns `False`
   incorrectly, the intent pipeline re-classifies a short plain-text reply as `general_chat` or
   `out_of_scope`, routing it to `GeneralAgent` which calls `session.clear()`.
4. **`orchestrator.py` — `ComplaintAgent._capture_step_reply`**: the step-aware name capture
   only fires when `context["step"] == "collect_name"`, but the step value is sometimes not
   persisted, so the guard never matches and the name is never stored.

---

## Glossary

- **Bug_Condition (C)**: The condition that triggers context loss — a user turn arrives while
  `active_agent` is a service agent and `flow_started` is `True`, but the system fails to
  recognise it as a flow continuation.
- **Property (P)**: The desired post-fix behaviour for turns where C holds — the reply must
  advance the flow (capture the entity or ask for the next one) and must not contain generic
  greeting phrases.
- **Preservation**: All behaviours for turns where C does NOT hold must remain byte-for-byte
  identical to the pre-fix behaviour.
- **`_is_flow_locked`**: Method in `Orchestrator` (`orchestrator.py:_is_flow_locked`) that
  returns `True` when the conversation is mid-flow and should bypass intent classification.
- **`flow_started`**: Boolean field in the persisted context dict that marks an active service
  flow. Set to `True` by `update_context_with_intent` for service intents; cleared by
  `reset_context`.
- **`active_agent`**: String field in the persisted context dict naming the agent currently
  handling the flow (e.g. `"complaint_agent"`).
- **`step`**: String field in the persisted context dict naming the current collection step
  (e.g. `"collect_name"`, `"collect_area"`).
- **`entities`**: Dict field in the persisted context dict accumulating extracted values
  (name, area, issue, account_number, etc.).
- **`upsert_session_context`**: Function in `storage.py` that writes the context dict to the
  `session_context` SQLite table.
- **`get_session_context`**: Function in `storage.py` that reads the context dict from SQLite.

---

## Bug Details

### Bug Condition

The bug manifests when a user is mid-flow (the bot has asked for a specific piece of
information) and sends a short reply that contains no service-domain keywords. The system
fails to recognise the reply as a flow continuation and re-routes it as a new intent.

**Formal Specification:**

```
FUNCTION isBugCondition(turn)
  INPUT: turn = { message: str, user_id: str, context: dict }
  OUTPUT: boolean

  RETURN (
    turn.context.active_agent IN {"complaint_agent", "billing_agent", "connection_agent"}
    AND turn.context.flow_started = TRUE
    AND NOT containsServiceKeyword(turn.message)
    AND wordCount(turn.message) <= 6
  )

WHERE:
  containsServiceKeyword(msg) = any word in msg matches domain keywords
    (leak, bill, water, fault, account, meter, connection, report, etc.)
  wordCount(msg) = len(msg.strip().split())
END FUNCTION
```

### Examples

| Turn | User message | `active_agent` | `flow_started` | `step` | Bug fires? |
|------|-------------|----------------|----------------|--------|-----------|
| 2 | "Mary Kija" | complaint_agent | True | collect_name | **Yes** — name ignored, bot resets |
| 3 | "Makululu Road" | complaint_agent | True | collect_area | **Yes** — area ignored, bot resets |
| 2 | "123456" | billing_agent | True | collect_account | No — contains digits, classified correctly |
| 1 | "I want to report a leak" | None | False | None | No — new intent, classified correctly |
| 2 | "I need a human agent" | complaint_agent | True | collect_name | No — escalation keyword present |

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- Greeting messages ("Hi", "Hello") with no active flow MUST continue to receive a general
  welcome response and MUST NOT start any service flow.
- New service requests after a completed flow MUST continue to be classified fresh and start
  the appropriate flow from the beginning.
- Valid account numbers during a billing inquiry MUST continue to trigger a bill lookup and
  return the balance with payment methods.
- Explicit human-agent requests at any point MUST continue to escalate the conversation.
- Out-of-scope messages with no active flow MUST continue to receive a polite scope-decline
  response.
- Escalation form collection (name + phone) MUST continue to work correctly.

**Scope:**

All turns where `isBugCondition` returns `False` — including greetings, new service requests,
account number replies, escalation requests, and out-of-scope messages — MUST be completely
unaffected by this fix.

---

## Hypothesized Root Cause

Based on reading the source code, there are four distinct root causes, each independently
sufficient to produce the observed symptom.

### Root Cause 1 — Context Not Saved Before the Next Turn Reads It

**File:** `backend/orchestrator.py`, `Orchestrator.process`

**Code path:**

```python
# orchestrator.py ~line 390
if not context.get("active_agent") and not context.get("flow_started"):
    self.context_manager.save_context(user_id, context)          # ← saved only here
context = self.context_manager.update_context_with_history(...)
self.context_manager.save_context(user_id, context)              # ← also saved here
```

The first `save_context` call is guarded by `not active_agent and not flow_started`. This
means that when a flow *starts* (Turn 1: "I want to report a leak"), the context with
`active_agent = "complaint_agent"` and `flow_started = True` is saved only by the second
unconditional call. However, if an exception occurs between the two saves, or if the
`update_context_with_history` call mutates the dict in a way that clears `active_agent`
before the second save, the persisted row will not contain the flow flags.

More critically: `update_context_with_intent` (called inside `_handle_new_intent`) sets
`active_agent` and `flow_started`, but the context is only saved *after* the agent reply is
generated. If the agent's `handle` method calls `context_manager.reset_context(context)` or
`session.clear()` internally (as `GeneralAgent.handle` does for non-flow turns), those flags
are wiped before the final `save_context` call.

### Root Cause 2 — `_is_flow_locked` Returns False When Context Was Not Persisted

**File:** `backend/orchestrator.py`, `Orchestrator._is_flow_locked`

```python
def _is_flow_locked(self, context: dict) -> bool:
    active_agent = cast(str, context.get("active_agent") or "")
    flow_started = context.get("flow_started", False)
    escalated = context.get("escalated", False)
    if escalated:
        return False
    service_agents = {"complaint_agent", "billing_agent", "connection_agent", "info_agent"}
    if active_agent in service_agents:
        return True
    return bool(flow_started)
```

This logic is correct *in isolation*, but it depends entirely on `load_context` returning a
dict with `active_agent` and `flow_started` correctly populated. If Root Cause 1 caused those
fields to be absent from the SQLite row, `load_context` returns a fresh shell with
`active_agent = None` and `flow_started = False`, so `_is_flow_locked` returns `False` and
the turn is routed to `_handle_new_intent`.

### Root Cause 3 — Intent Pipeline Re-classifies Short Plain-Text Replies as `general_chat`

**File:** `backend/intent_pipeline.py`, `IntentPipeline.classify`

When `_is_flow_locked` returns `False` (due to Root Cause 2), the turn enters
`_handle_new_intent`, which calls `intent_pipeline.classify`. For a message like "Mary Kija":

- `_billing_inquiry_priority` → False (no billing keywords)
- `_billing_conversation_continuation` → False (no prior bot billing prompt in history)
- `_rule_based_classify` → matches `general_chat` rule pattern `\b(hi|hello|hey|...)\b`?
  No. Falls through to `out_of_scope` with confidence 0.1.
- `_lightweight_classify` → no keyword match → `out_of_scope` with confidence 0.3.
- `_llm_classify` → Groq may return `general_chat` for a bare name.
- Ensemble result: `general_chat` or `out_of_scope` at low confidence.

`update_context_with_intent` then sets `active_agent = "general_agent"` (via
`_map_intent_to_agent`), and `GeneralAgent.handle` calls `context_manager.reset_context`,
wiping all flow state and returning "How can I assist you?".

There is no guard in `_handle_new_intent` that checks whether the *incoming* context already
had a service agent set before classification ran.

### Root Cause 4 — `_capture_step_reply` Requires `step == "collect_name"` But Step Is Not Always Persisted

**File:** `backend/orchestrator.py`, `ComplaintAgent._capture_step_reply`

```python
def _capture_step_reply(self, message: str, context: dict, entities: dict) -> None:
    step = str(context.get("step") or "")
    ...
    if not entities.get("name") and step == "collect_name":   # ← guard
        maybe_name = self._extract_name_reply(raw)
        if maybe_name:
            entities["name"] = maybe_name
```

`update_context_with_step` sets `context["step"] = step` in memory, but if the context is
not saved to SQLite before the next turn (Root Cause 1), the loaded context will have
`step = 0` (the schema default) instead of `"collect_name"`. The guard `step == "collect_name"`
then fails, and the name is never captured even if the flow lock were somehow restored.

---

## Correctness Properties

Property 1: Bug Condition — Flow Continuation Routing

_For any_ turn where `isBugCondition(turn)` returns `True` (user is mid-flow, message is
short and contains no service keywords), the fixed `Orchestrator.process` SHALL:

- Route the turn to `_handle_active_flow` (not `_handle_new_intent`).
- Return a reply that does NOT contain any of the generic greeting phrases:
  "how can I assist", "how can I help you today", "how may I assist".
- Leave `context.active_agent` unchanged after the turn.
- Leave `context.flow_started = True` after the turn.
- Either populate the entity field being collected (e.g. `entities["name"]`), OR ask for
  the next missing field in the flow sequence.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation — Non-Bug-Condition Turns

_For any_ turn where `isBugCondition(turn)` returns `False` (greeting, new service request,
account number reply, escalation request, out-of-scope message), the fixed
`Orchestrator.process` SHALL produce the same reply and the same resulting context state as
the original (unfixed) `Orchestrator.process`, preserving all existing routing and response
behaviour.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

---

## Fix Implementation

### Changes Required

The fix is minimal and surgical. No new abstractions are introduced. Each change targets
exactly one root cause.

---

#### Fix 1 — Guarantee Context Is Saved Immediately After Flow Flags Are Set

**File:** `backend/orchestrator.py`

**Function:** `Orchestrator.process`

**Problem:** The conditional early save (`if not active_agent and not flow_started`) means
that when a flow *starts*, the context with the new `active_agent` and `flow_started = True`
is only saved by the later unconditional call — which may be preceded by a `reset_context`
call inside the agent.

**Change:** Remove the conditional guard and always save context immediately after
`_handle_new_intent` or `_handle_active_flow` returns, before `update_context_with_history`.

```python
# BEFORE (orchestrator.py ~line 388)
if not context.get("active_agent") and not context.get("flow_started"):
    self.context_manager.save_context(user_id, context)
context = self.context_manager.update_context_with_history(context, "bot", reply_text)
self.context_manager.save_context(user_id, context)

# AFTER
# Always persist flow state immediately after the agent sets it,
# before history is appended (history append must not race with flow flags).
context["user_id"] = user_id
context["session_id"] = session_id
self.context_manager.save_context(user_id, context)          # ← unconditional, early
context = self.context_manager.update_context_with_history(context, "bot", reply_text)
self.context_manager.save_context(user_id, context)          # ← final save with history
```

---

#### Fix 2 — Add a Flow-Continuation Guard in `_handle_new_intent`

**File:** `backend/orchestrator.py`

**Function:** `Orchestrator._handle_new_intent`

**Problem:** Even if `_is_flow_locked` returns `False` due to a stale context load, the
intent pipeline should not be allowed to overwrite a service agent with `general_agent` when
the *pre-classification* context already had a service agent set.

**Change:** Before running the intent pipeline, check whether the context already has a
service agent. If it does, treat the turn as a flow continuation regardless of what the
classifier returns.

```python
async def _handle_new_intent(self, message: str, context: dict) -> str:
    # Guard: if context already has a service agent set (stale load race),
    # treat this as a flow continuation rather than a new intent.
    _service_agents = {"complaint_agent", "billing_agent", "connection_agent", "info_agent"}
    if context.get("active_agent") in _service_agents:
        return await self._handle_active_flow(message, context)

    # ... existing classification logic unchanged ...
```

---

#### Fix 3 — Persist `step` Immediately When It Is Set

**File:** `backend/orchestrator.py`

**Function:** `ComplaintAgent.handle` (and `ConnectionAgent.handle`)

**Problem:** `context_manager.update_context_with_step(context, "collect_name")` updates the
in-memory dict but the context is not saved to SQLite until the end of `Orchestrator.process`.
If the process exits abnormally, or if the save is skipped due to the conditional guard
(Root Cause 1), the step is lost.

**Change:** After `update_context_with_step`, call `save_context` immediately.

```python
# In ComplaintAgent.handle, before returning the "What is your full name?" reply:
if current_field == "name":
    context_manager.update_context_with_step(context, "collect_name")
    context_manager.save_context(context.get("user_id", "unknown"), context)  # ← add this
    return {
        "reply": "I can help report this issue. What is your full name?",
        "requires_tool": False
    }
```

Apply the same pattern for `collect_area`, `collect_issue`, and in `ConnectionAgent.handle`
for each step.

---

#### Fix 4 — Relax `_capture_step_reply` to Accept Name When Step Is Missing

**File:** `backend/orchestrator.py`

**Function:** `ComplaintAgent._capture_step_reply`

**Problem:** The name-capture guard `step == "collect_name"` is too strict. If `step` was
not persisted (Root Cause 1 + 4), the guard fails even though `name` is the next missing
field.

**Change:** Fall back to "next missing field" logic when `step` is absent or stale.

```python
def _capture_step_reply(self, message: str, context: dict, entities: dict) -> None:
    step = str(context.get("step") or "")
    raw = (message or "").strip()
    if not raw:
        return

    # Always try to infer issue from any message
    if not entities.get("issue"):
        inferred_issue = self._infer_issue(raw, context)
        if inferred_issue:
            entities["issue"] = inferred_issue

    # Capture name: accept when step matches OR when name is the next missing field
    name_is_next = not entities.get("name") and not entities.get("area")  # name comes first
    if not entities.get("name") and (step == "collect_name" or name_is_next):
        maybe_name = self._extract_name_reply(raw)
        if maybe_name:
            entities["name"] = maybe_name

    if not entities.get("area"):
        if entities.get("address"):
            entities["area"] = entities["address"]
        elif step == "collect_area" or (entities.get("name") and not entities.get("area")):
            if len(raw) >= 3:
                entities["area"] = raw

    if not entities.get("issue") and (step == "collect_issue" or
            (entities.get("name") and entities.get("area") and not entities.get("issue"))):
        if len(raw) >= 2:
            entities["issue"] = raw
```

---

### Data Flow: Corrected Turn Routing

```
Turn N (user sends "Mary Kija")
│
├─ Orchestrator.process(message="Mary Kija", user_id="260970000000")
│   │
│   ├─ load_context(user_id)
│   │   └─ SQLite: active_agent="complaint_agent", flow_started=True, step="collect_name"
│   │      (guaranteed by Fix 1 + Fix 3 from Turn N-1)
│   │
│   ├─ _is_flow_locked(context)
│   │   └─ active_agent="complaint_agent" ∈ service_agents → returns True  ✓
│   │
│   ├─ _handle_active_flow(message, context)
│   │   └─ agent = agents["complaint_agent"]
│   │       └─ ComplaintAgent.handle(message, context)
│   │           ├─ _capture_step_reply("Mary Kija", context, entities)
│   │           │   └─ step="collect_name" → _extract_name_reply("Mary Kija")
│   │           │       └─ entities["name"] = "Mary Kija"  ✓
│   │           └─ current_field = "area"  (name now filled)
│   │               └─ update_context_with_step(context, "collect_area")
│   │               └─ save_context(user_id, context)  ← Fix 3
│   │               └─ reply = "What area or address is the issue occurring at?"
│   │
│   ├─ save_context(user_id, context)  ← Fix 1 (unconditional early save)
│   ├─ update_context_with_history(context, "bot", reply)
│   └─ save_context(user_id, context)  ← final save
│
└─ Response: "What area or address is the issue occurring at?"
```

**Contrast with the buggy path (pre-fix):**

```
Turn N (user sends "Mary Kija") — BUGGY
│
├─ load_context → active_agent=None, flow_started=False  (not persisted from Turn N-1)
├─ _is_flow_locked → False
├─ _handle_new_intent
│   ├─ intent_pipeline.classify("Mary Kija") → general_chat (0.55)
│   ├─ update_context_with_intent → active_agent="general_agent"
│   └─ GeneralAgent.handle → reset_context() → "How can I assist you?"
└─ Response: "How can I assist you?"  ← BUG
```

---

## Testing Strategy

### Validation Approach

Testing follows a two-phase approach:

1. **Exploratory (pre-fix):** Run tests against the *unfixed* code to confirm the bug
   manifests and to identify which root cause is active.
2. **Fix + Preservation checking (post-fix):** Run the same tests against the *fixed* code
   to verify Property 1 (bug is gone) and Property 2 (no regressions).

---

### Exploratory Bug Condition Checking

**Goal:** Surface counterexamples that demonstrate the bug on unfixed code. Confirm or refute
the root cause analysis. If refuted, re-hypothesize.

**Test Plan:** Simulate a two-turn conversation for each service flow. Turn 1 starts the flow;
Turn 2 sends a short plain-text reply (the bug condition). Assert that Turn 2 is handled as a
flow continuation on unfixed code — expect these assertions to *fail*, confirming the bug.

**Test Cases:**

1. **Complaint flow — name reply:** Turn 1: "I want to report a water leak". Turn 2: "Mary Kija".
   Assert `entities["name"] == "Mary Kija"` and reply contains "area" prompt. (Will fail on unfixed code.)

2. **Complaint flow — area reply:** Turn 1: "report a fault". Turn 2 (after name collected):
   "Makululu Road". Assert `entities["area"] == "Makululu Road"`. (Will fail on unfixed code.)

3. **Connection flow — name reply:** Turn 1: "I need a new water connection". Turn 2: "John Banda".
   Assert `entities["name"] == "John Banda"`. (Will fail on unfixed code.)

4. **Billing flow — name-only reply to account prompt:** Turn 1: "check my bill". Turn 2: "Mary Kija".
   Assert reply asks for account number (not a generic greeting). (Will fail on unfixed code.)

5. **Edge case — single-word name:** Turn 1: "report a leak". Turn 2: "Aisha".
   Assert reply does not contain "how can I assist". (May fail on unfixed code.)

**Expected Counterexamples:**

- `context["active_agent"]` is `None` at the start of Turn 2 (Root Cause 1 confirmed).
- Reply contains "How can I assist you?" (Root Cause 3 confirmed).
- `entities["name"]` is absent after Turn 2 (Root Cause 4 confirmed).

---

### Fix Checking

**Goal:** Verify that for all turns where `isBugCondition` holds, the fixed function produces
the expected behaviour (Property 1).

**Pseudocode:**

```
FOR ALL turn WHERE isBugCondition(turn) DO
  reply, context_after ← Orchestrator_fixed.process(turn.message, turn.user_id)

  ASSERT "how can I assist" NOT IN reply.lower()
  ASSERT "how can I help you today" NOT IN reply.lower()
  ASSERT context_after.active_agent = turn.context.active_agent
  ASSERT context_after.flow_started = TRUE
  ASSERT (
    entity_being_collected(turn.context) IN context_after.entities
    OR reply asks for NEXT missing field
  )
END FOR
```

---

### Preservation Checking

**Goal:** Verify that for all turns where `isBugCondition` does NOT hold, the fixed function
produces the same result as the original function (Property 2).

**Pseudocode:**

```
FOR ALL turn WHERE NOT isBugCondition(turn) DO
  reply_original ← Orchestrator_original.process(turn.message, turn.user_id)
  reply_fixed    ← Orchestrator_fixed.process(turn.message, turn.user_id)

  ASSERT reply_original = reply_fixed
  ASSERT context_after_original.active_agent = context_after_fixed.active_agent
  ASSERT context_after_original.flow_started = context_after_fixed.flow_started
END FOR
```

**Testing Approach:** Property-based testing is recommended for preservation checking because:

- It generates many test cases automatically across the input domain.
- It catches edge cases that manual unit tests might miss.
- It provides strong guarantees that behaviour is unchanged for all non-buggy inputs.

**Test Cases:**

1. **Greeting preservation:** "Hi", "Hello", "Good morning" with no active flow → same
   general welcome response before and after fix.
2. **New service request preservation:** "I want to report a leak" with no active flow →
   same "What is your full name?" prompt before and after fix.
3. **Account number reply preservation:** "123456" during billing flow → same bill lookup
   result before and after fix.
4. **Escalation preservation:** "I need a human agent" at any point → same escalation
   response before and after fix.
5. **Out-of-scope preservation:** "What is the weather today?" with no active flow → same
   scope-decline response before and after fix.

---

### Unit Tests

- Test `_is_flow_locked` with all combinations of `active_agent`, `flow_started`, and
  `escalated` values, including `None` and missing keys.
- Test `ComplaintAgent._capture_step_reply` with `step = "collect_name"`, `step = ""`,
  and `step = None` — all three must capture a valid name when name is the next missing field.
- Test `ComplaintAgent._capture_step_reply` with stopword-only inputs ("hello", "water",
  "issue") — must NOT capture these as names.
- Test `context_engine.load_context` / `save_context` round-trip: save a context with
  `active_agent = "complaint_agent"`, `flow_started = True`, `step = "collect_name"`, then
  load it and assert all three fields are present and correct.
- Test `Orchestrator._handle_new_intent` with a context that already has
  `active_agent = "complaint_agent"` — must route to `_handle_active_flow` (Fix 2).

### Property-Based Tests

Using `hypothesis` (Python):

```python
from hypothesis import given, settings
from hypothesis import strategies as st

# Strategy: generate short messages with no service keywords
short_plain_messages = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
    min_size=2, max_size=40
).filter(lambda m: not any(kw in m.lower() for kw in SERVICE_KEYWORDS))

@given(message=short_plain_messages)
@settings(max_examples=200)
def test_property1_flow_continuation(message):
    """Property 1: Bug Condition — flow continuation routing."""
    context = make_mid_flow_context(active_agent="complaint_agent",
                                    flow_started=True, step="collect_name")
    reply, ctx_after = run_fixed_orchestrator(message, context)

    assert "how can I assist" not in reply.lower()
    assert "how can I help you today" not in reply.lower()
    assert ctx_after["active_agent"] == "complaint_agent"
    assert ctx_after["flow_started"] is True


@given(message=st.text(min_size=1, max_size=200))
@settings(max_examples=500)
def test_property2_preservation_greeting(message):
    """Property 2: Preservation — greeting turns unchanged."""
    context = make_empty_context()  # no active flow
    reply_orig = run_original_orchestrator(message, context)
    reply_fixed = run_fixed_orchestrator(message, context)
    assert reply_orig == reply_fixed
```

- Generate random game states (active_agent, step, entities combinations) and verify that
  `_is_flow_locked` returns `True` for all service-agent contexts.
- Generate random short messages (1–6 words, no service keywords) and verify that the fixed
  orchestrator never returns a generic greeting when a flow is active.
- Generate random non-bug-condition turns and verify reply equality between original and fixed.

### Integration Tests

- **Full complaint flow:** Simulate all three turns (start → name → area → issue → log) via
  the HTTP API. Assert each turn returns the correct prompt and the final turn returns a
  ticket ID.
- **Full connection flow:** Simulate four turns (start → name → address → phone → email →
  create). Assert each turn advances the step and the final turn returns a connection
  reference.
- **Context persistence across process restart:** Start a flow, simulate a process restart
  (reload context from SQLite), then send the next turn. Assert the flow continues correctly.
- **Concurrent users:** Simulate two users in different flow states sending messages
  simultaneously. Assert each user's context is isolated and correct.
- **Flow timeout:** Start a flow, advance `last_updated` beyond `FLOW_TIMEOUT_HOURS`, then
  send a turn. Assert the flow is expired and the user receives a fresh start message.
