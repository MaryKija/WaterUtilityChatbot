"""Public API coverage for the demo-critical customer-service flows."""

from fastapi.testclient import TestClient

from backend.storage import create_complaint, get_complaint
from main import app

ADMIN_HEADERS = {"Authorization": "Bearer test-admin-token"}


def test_api_route_contract_chat_clear_updates_and_admin_lists():
    client = TestClient(app)

    chat = client.post("/chat", json={"user_id": "contract-user", "message": "hello"})
    assert chat.status_code == 200
    payload = chat.json()
    assert "response" in payload
    assert "reply" not in payload
    assert {"intent", "confidence", "entities", "escalated", "tool_used", "tool_trace"} <= set(payload)

    clear = client.post("/chat/clear", json={"user_id": "contract-user"})
    assert clear.status_code == 200
    assert clear.json()["status"] == "cleared"

    updates = client.get("/chat/updates", params={"user_id": "contract-user", "after": 0})
    assert updates.status_code == 200
    assert {"status", "messages", "next_after"} <= set(updates.json())

    assert client.get("/admin/complaints", headers=ADMIN_HEADERS).status_code == 200
    assert client.get("/admin/escalations", headers=ADMIN_HEADERS).status_code == 200


def test_billing_lookup_flow_uses_seeded_database_and_tool_metadata():
    from backend.customer_auth import customer_auth_service

    client = TestClient(app)
    user_id = "billing-user"
    client.post("/chat/clear", json={"user_id": user_id})

    # Seed the demo PIN for account 000001 so the PIN gate can verify it.
    customer_auth_service.set_pin("000001", "1234")

    first = client.post("/chat", json={"user_id": user_id, "message": "I want to check my bill balance"})
    assert first.status_code == 200
    assert first.json()["intent"] == "billing_inquiry"
    assert "account number" in first.json()["response"].lower()

    second = client.post("/chat", json={"user_id": user_id, "message": "000001"})
    assert second.status_code == 200
    # PIN gate: bot should now ask for the 4-digit PIN
    assert "pin" in second.json()["response"].lower()

    # Provide the demo PIN for account 000001 (seeded as "1234")
    third = client.post("/chat", json={"user_id": user_id, "message": "1234"})
    body = third.json()
    assert third.status_code == 200
    assert "Mary Kija" in body["response"]
    assert "K245.60" in body["response"]
    assert body["tool_used"] in {"get_bill", "get_payment_methods"}
    assert any(t["tool"] == "get_bill" for t in body["tool_trace"])


def test_complaint_logging_and_followup_flow():
    client = TestClient(app)
    user_id = "complaint-user"
    client.post("/chat/clear", json={"user_id": user_id})

    client.post("/chat", json={"user_id": user_id, "message": "I want to report no water"})
    client.post("/chat", json={"user_id": user_id, "message": "Mary Kija"})
    logged = client.post("/chat", json={"user_id": user_id, "message": "Kabwe"})
    body = logged.json()

    assert logged.status_code == 200
    assert "reference number" in body["response"].lower()
    assert any(t["tool"] == "log_complaint" for t in body["tool_trace"])
    ticket_id = body["entities"]["ticket_id"]

    client.post("/chat/clear", json={"user_id": user_id})
    followup = client.post("/chat", json={"user_id": user_id, "message": f"Check complaint {ticket_id}"})
    followup_body = followup.json()
    assert followup.status_code == 200
    assert ticket_id in followup_body["response"]
    assert followup_body["tool_used"] == "get_complaint_status"


def test_payment_not_reflected_flow_escalates_without_live_llm():
    client = TestClient(app)
    user_id = "payment-user"
    client.post("/chat/clear", json={"user_id": user_id})

    first = client.post(
        "/chat",
        json={"user_id": user_id, "message": "I paid but my payment is not reflected"},
    )
    assert first.status_code == 200
    assert "payment method" in first.json()["response"].lower()

    second = client.post(
        "/chat",
        json={"user_id": user_id, "message": "account 123456 MTN today K245.60"},
    )
    body = second.json()
    assert second.status_code == 200
    assert body["escalated"] is True
    assert "agent will verify" in body["response"].lower()

    escalations = client.get("/admin/escalations", headers=ADMIN_HEADERS).json()
    assert any(e["user_id"] == user_id and e["reason"] == "payment_issue" for e in escalations)


def test_escalation_flow_for_explicit_human_request_skips_llm_detector(monkeypatch):
    import backend.agent as agent

    def fail_if_called(message, session):
        raise AssertionError("Groq human detector should not be called for explicit human request")

    monkeypatch.setattr(agent, "detect_human_request", fail_if_called)

    client = TestClient(app)
    user_id = "human-user"
    client.post("/chat/clear", json={"user_id": user_id})

    response = client.post("/chat", json={"user_id": user_id, "message": "I need a human agent"})
    body = response.json()
    assert response.status_code == 200
    assert body["intent"] == "escalation"
    assert "customer service" in body["response"].lower()


def test_out_of_scope_refusal_uses_clear_fallback_when_llm_is_down(monkeypatch):
    import backend.orchestrator as orchestrator

    def llm_down(*args, **kwargs):
        raise RuntimeError("simulated Groq outage")

    monkeypatch.setattr(orchestrator, "generate_response", llm_down)

    client = TestClient(app)
    response = client.post("/chat", json={"user_id": "scope-user", "message": "football scores"})
    body = response.json()
    assert response.status_code == 200
    assert body["intent"] == "out_of_scope"
    assert "water utility services" in body["response"].lower()


def test_admin_complaint_status_update():
    client = TestClient(app)
    ticket_id = create_complaint(name="Admin Test", area="Kabwe", issue="No water")

    response = client.post(
        f"/admin/complaints/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ADMIN_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert get_complaint(ticket_id).status == "IN_PROGRESS"
