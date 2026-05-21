from fastapi.testclient import TestClient

from backend.storage import create_complaint, get_complaint
from backend.tools import get_bill
from main import app


ADMIN_HEADERS = {"Authorization": "Bearer test-admin-token"}


def test_billing_lookup_uses_seeded_customer_schema_and_unknown_fallback():
    # Account numbers were migrated: "123456" → "000001" (Mary Kija)
    known = get_bill("000001")
    unknown = get_bill("999999")

    assert "Mary Kija" in known
    assert "K94.02" in known  # LgWSC tariff: 12.84 m³ domestic metered
    assert "could not find that account number" in unknown.lower()


def test_complaint_category_priority_and_sla_are_inferred():
    quality_ticket = create_complaint(
        name="Quality Customer",
        area="Kabwe",
        issue="Smelly dirty water with a bad taste",
    )
    leak_ticket = create_complaint(
        name="Leak Customer",
        area="Kapiri Mposhi",
        issue="Burst pipe leak near the road",
    )

    quality = get_complaint(quality_ticket)
    leak = get_complaint(leak_ticket)

    assert quality is not None
    assert leak is not None
    assert quality.category == "WATER_QUALITY"
    assert quality.priority == "HIGH"
    assert quality.sla_due_at
    assert leak.category == "LEAK"
    assert leak.priority == "HIGH"
    assert leak.sla_due_at


def test_admin_assignment_priority_dashboard_and_feedback_endpoints():
    client = TestClient(app)
    ticket_id = create_complaint(name="Admin Survey", area="Kabwe", issue="Dirty water")

    assign = client.post(
        f"/admin/complaints/{ticket_id}/assign",
        json={"assigned_to": "Field Team A"},
        headers=ADMIN_HEADERS,
    )
    priority = client.post(
        f"/admin/complaints/{ticket_id}/priority",
        json={"priority": "URGENT"},
        headers=ADMIN_HEADERS,
    )
    feedback = client.post(
        "/feedback",
        json={
            "session_id": "survey-session",
            "user_id": "demo-user",
            "rating": 2,
            "text_feedback": "The response was not clear",
            "helpful": False,
        },
    )
    feedback_list = client.get("/admin/feedback", headers=ADMIN_HEADERS)
    dashboard = client.get("/admin/dashboard", headers=ADMIN_HEADERS)

    assert assign.status_code == 200
    assert assign.json()["complaint"]["assigned_to"] == "Field Team A"
    assert priority.status_code == 200
    assert priority.json()["complaint"]["priority"] == "URGENT"
    assert feedback.status_code == 200
    assert feedback_list.status_code == 200
    assert any(item["rating"] == 2 for item in feedback_list.json())
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["urgent_cases"] >= 1
    assert any(item["category"] == "WATER_QUALITY" for item in body["cases_by_category"])
    assert body["needs_attention"]
