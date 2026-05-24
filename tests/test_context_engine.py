import asyncio

from backend.context_engine import (
    context_manager,
    initialize_context,
    update_context,
    resolve_pending_question,
    extract_entities,
    expire_flow_if_needed,
)
from main import app
from backend.orchestrator import ComplaintAgent
from fastapi.testclient import TestClient


def test_initialize_context_schema():
    ctx = initialize_context("260970000000")
    assert ctx["user_id"] == "260970000000"
    assert "entities" in ctx
    assert "history" in ctx
    assert ctx["flow_started"] is False


def test_extract_entities_account_phone_ticket():
    e = extract_entities("account 123456 my phone is +260970000000 ref WC-ABC123")
    assert e.get("account_number") == "123456"
    assert e.get("ticket_id") == "WC-ABC123"
    assert e.get("phone")


def test_pending_question_resolves_and_clears():
    sess = initialize_context("u1")
    sess["pending_question"] = "account_number"
    sess["entities"] = {}
    sess2, ok = resolve_pending_question(sess, "my account is 123456")
    assert ok is True
    assert sess2["pending_question"] is None
    assert sess2["entities"]["account_number"] == "123456"


def test_update_context_sets_reply_override_on_failed_pending():
    sess = initialize_context("u1")
    sess["pending_question"] = "account_number"
    sess = update_context("u1", "user", "no", sess)
    ah = sess.get("action_hint")
    assert isinstance(ah, dict)
    assert "reply_override" in ah


def test_flow_expiry_clears_flow():
    sess = initialize_context("u1")
    sess["flow_started"] = True
    sess["flow"] = "billing"
    sess["last_updated"] = "2000-01-01T00:00:00+00:00"
    sess2 = expire_flow_if_needed(sess)
    assert sess2.get("flow") is None
    assert sess2.get("flow_expired_notice")


def test_reset_context_clears_state():
    sess = initialize_context("u4")
    sess["entities"] = {"account_number": "123456"}
    sess["history"] = [{"role": "user", "text": "hello", "timestamp": "now"}]
    sess["flow_started"] = True

    cleared = context_manager.reset_context(sess)
    assert cleared["entities"] == {}
    assert cleared["history"] == []
    assert cleared["flow_started"] is False
    assert cleared["intent"] is None


def test_reset_context_removes_stale_fields():
    stale = {
        "user_id": "u7",
        "intent": "report_fault",
        "active_agent": "complaint_agent",
        "ticket_id": "WC-XXXXXX",
        "name": "Wesley",
        "conversation_history_head": [{"role": "user", "text": "legacy"}],
    }

    cleared = context_manager.reset_context(stale)
    assert cleared.get("user_id") == "u7"
    assert cleared.get("intent") is None
    assert cleared.get("active_agent") is None
    assert "ticket_id" not in cleared
    assert "name" not in cleared
    assert cleared.get("conversation_history_head") in (None, [])


def test_reset_context_mutates_original_dict():
    sess = initialize_context("u8")
    original_id = id(sess)
    sess["active_agent"] = "general_agent"
    sess["intent"] = "general_chat"
    sess["entities"] = {"account_number": "123456"}

    cleared = context_manager.reset_context(sess)

    assert id(cleared) == original_id
    assert sess["active_agent"] is None
    assert sess["intent"] is None
    assert sess["entities"] == {}


def test_initialize_context_does_not_share_mutable_defaults():
    left = initialize_context("left-user")
    right = initialize_context("right-user")

    left["entities"]["name"] = "shared?"
    left["history"].append({"role": "user", "text": "hello", "timestamp": "now"})

    assert right["entities"] == {}
    assert right["history"] == []


def test_general_agent_handle_clears_stale_state(monkeypatch):
    from backend.orchestrator import GeneralAgent
    from backend.llm import groq_client

    monkeypatch.setattr(groq_client, "generate_response", lambda *args, **kwargs: "Stub reply")

    # Idle general chat with stale entities — no active specialist flow
    context = initialize_context("u9")
    context["intent"] = "general_chat"
    context["entities"] = {"account_number": "123456"}

    async def run() -> None:
        out = await GeneralAgent().handle("hello", context)
        assert out["reply"] == "Stub reply"
        assert context["active_agent"] is None
        assert context["intent"] is None
        assert context["entities"] == {}

    asyncio.run(run())


def test_clear_chat_endpoint():
    client = TestClient(app)
    response = client.post("/chat/clear", json={"user_id": "u5"})
    assert response.status_code == 200
    assert response.json().get("status") == "cleared"


def test_flow_restart_explicit_reset_after_billing_flow():
    """Explicit reset clears locked billing flow so a new intent can classify."""
    client = TestClient(app)

    client.post("/chat/clear", json={"user_id": "u6"})

    r1 = client.post("/chat", json={"user_id": "u6", "message": "I want to check my bill balance"})
    assert r1.status_code == 200
    assert r1.json().get("intent") == "billing_inquiry"

    r_clear = client.post("/chat/clear", json={"user_id": "u6"})
    assert r_clear.status_code == 200
    assert r_clear.json().get("status") == "cleared"

    r3 = client.post("/chat", json={"user_id": "u6", "message": "water outage"})
    assert r3.status_code == 200
    assert r3.json().get("intent") in {"report_fault", "leak_report", "general_chat"}


def test_complaint_agent_advances_after_plain_name_reply():
    agent = ComplaintAgent()
    context = initialize_context("complaint-user")
    context["intent"] = "report_fault"
    context["active_agent"] = "complaint_agent"
    context["flow_started"] = True

    async def run() -> None:
        first = await agent.handle("I want to report a water outage", context)
        assert "full name" in first["reply"].lower()
        assert context["entities"].get("issue") == "Water outage"

        second = await agent.handle("mary kija", context)
        assert "area or address" in second["reply"].lower()
        assert context["entities"].get("name") == "mary kija"

    asyncio.run(run())


def test_complaint_followup_requests_status_tool_when_ticket_present():
    agent = ComplaintAgent()
    context = initialize_context("cfu-1")
    context["intent"] = "complaint_followup"
    context["entities"] = {"ticket_id": "WC-O2YEQJ"}

    async def run() -> None:
        decision = await agent.handle("complaint status", context)
        assert decision.get("requires_tool") is True
        assert decision.get("tool_name") == "get_complaint_status"
        assert decision.get("parameters", {}).get("ticket_id") == "WC-O2YEQJ"

    asyncio.run(run())


def test_complaint_agent_rejects_non_name_when_waiting_for_name():
    agent = ComplaintAgent()
    context = initialize_context("complaint-user-2")
    context["intent"] = "report_fault"
    context["active_agent"] = "complaint_agent"
    context["flow_started"] = True
    context["step"] = "collect_name"

    async def run() -> None:
        response = await agent.handle("still experiencing the issue", context)
        assert "full name" in response["reply"].lower()
        assert "name" not in context["entities"]

    asyncio.run(run())


def test_tool_executor_calls_dict_based_complaint_tool(monkeypatch):
    from backend import tools
    from backend.tool_executor import ToolExecutor

    monkeypatch.setattr(tools, "create_complaint", lambda **kwargs: "WC-ABC123")

    executor = ToolExecutor()
    context = initialize_context("tool-user")

    async def run() -> None:
        result = await executor.execute(
            "log_complaint",
            {"name": "mary kija", "area": "Matero East", "issue": "Water outage"},
            context,
        )
        assert "WC-ABC123" in result
        assert context["entities"]["ticket_id"] == "WC-ABC123"

    asyncio.run(run())

