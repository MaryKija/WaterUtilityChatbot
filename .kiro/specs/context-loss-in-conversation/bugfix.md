# Bugfix Requirements Document

## Introduction

The Water Utility Assistant chatbot loses conversational context between turns during multi-step service flows. When the bot asks a follow-up question (e.g., "What is your full name?") and the user replies with the requested information (e.g., "Mary Kija"), the bot ignores the reply and responds with a generic greeting-like message ("How can I assist you?"), as if the conversation had just started. This breaks all multi-step flows — leak reports, fault reports, billing inquiries, and new connection requests — leaving users stuck and unable to complete their service requests.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user initiates a service flow (e.g., "I want to report a leak") and the bot asks for their name or address, AND the user replies with a plain name or address in the next turn, THEN the system ignores the reply and responds with a generic "How can I assist you?" message, resetting the conversation.

1.2 WHEN a user is mid-flow (active_agent and flow_started are set in context) and sends a short reply that does not contain service keywords (e.g., a name like "Mary Kija"), THEN the system fails to recognize the reply as a continuation of the active flow and re-classifies it as a new, unrelated intent (general_chat or out_of_scope).

1.3 WHEN the orchestrator evaluates `_is_flow_locked` and the context has `active_agent = "complaint_agent"` and `flow_started = True`, but the context was not correctly persisted or reloaded between turns, THEN the system treats the turn as a new conversation and routes to `_handle_new_intent` instead of `_handle_active_flow`.

1.4 WHEN `ComplaintAgent._capture_step_reply` is called with a plain name reply (e.g., "Mary Kija") and the `step` field in context is not set to `"collect_name"`, THEN the system does not capture the name into `entities["name"]`, causing the agent to re-ask for the name indefinitely.

### Expected Behavior (Correct)

2.1 WHEN a user is mid-flow and replies with information the bot explicitly asked for (e.g., their name after being asked "What is your full name?"), THEN the system SHALL recognize the reply as a flow continuation, capture the provided value into the correct entity field, and advance the flow to the next step.

2.2 WHEN a user sends a short reply (1–6 words, no service keywords) during an active flow where `active_agent` is a service agent and `flow_started` is True, THEN the system SHALL route the message to `_handle_active_flow` without re-classifying intent.

2.3 WHEN the orchestrator loads context for a user who is mid-flow, THEN the system SHALL correctly restore `active_agent`, `flow_started`, `step`, and `entities` from persistent storage so that `_is_flow_locked` returns True for that turn.

2.4 WHEN `ComplaintAgent._capture_step_reply` is called with a plain name reply and the current step is `"collect_name"` (or the name field is the next missing field), THEN the system SHALL extract and store the name in `entities["name"]` and proceed to ask for the next missing field.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user sends a greeting (e.g., "Hi", "Hello") without any active flow, THEN the system SHALL CONTINUE TO respond with a general welcome message and not start any service flow.

3.2 WHEN a user starts a new service request after a previous flow has been completed and context has been reset, THEN the system SHALL CONTINUE TO correctly classify the new intent and start the appropriate flow from the beginning.

3.3 WHEN a user provides a valid account number during a billing inquiry flow, THEN the system SHALL CONTINUE TO look up the bill and return the balance with payment methods.

3.4 WHEN a user explicitly requests a human agent at any point, THEN the system SHALL CONTINUE TO escalate the conversation and stop routing to service agents.

3.5 WHEN a user sends an out-of-scope message (unrelated to water utility services) with no active flow, THEN the system SHALL CONTINUE TO politely decline and explain the bot's scope.

3.6 WHEN a user is in the escalation form flow and provides their name and phone number, THEN the system SHALL CONTINUE TO collect those details and complete the escalation record.

---

## Bug Condition Pseudocode

**Bug Condition Function** — identifies the inputs that trigger the context loss:

```pascal
FUNCTION isBugCondition(turn)
  INPUT: turn = { message, context }
  OUTPUT: boolean

  // The bug fires when the user is replying to a direct question
  // inside an active flow, but the system fails to treat it as such.
  RETURN (
    context.active_agent IN {"complaint_agent", "billing_agent", "connection_agent"}
    AND context.flow_started = TRUE
    AND turn.message does NOT contain service-domain keywords
    AND turn.message length <= 6 words
  )
END FUNCTION
```

**Property: Fix Checking**

```pascal
FOR ALL turn WHERE isBugCondition(turn) DO
  reply ← Orchestrator.process'(turn.message, turn.user_id)
  ASSERT reply does NOT contain generic greeting phrases
         ("how can I assist", "how can I help you today")
  ASSERT context.active_agent is UNCHANGED after the turn
  ASSERT context.flow_started = TRUE after the turn
  ASSERT the entity field being collected is now populated
         OR the bot asks for the NEXT missing field
END FOR
```

**Property: Preservation Checking**

```pascal
FOR ALL turn WHERE NOT isBugCondition(turn) DO
  ASSERT Orchestrator.process(turn) = Orchestrator.process'(turn)
END FOR
```
