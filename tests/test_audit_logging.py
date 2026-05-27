import json
import sqlite3
from fastapi.testclient import TestClient

from backend.storage import create_complaint
from backend import storage
from main import app

ADMIN_HEADERS = {"Authorization": "Bearer test-admin-token"}


def test_admin_actions_logging_to_audit_logs():
    """Verify that administrative actions log before/after states to the audit_logs table."""
    client = TestClient(app)
    
    # 1. Create a mock ticket in the seeded DB
    ticket_id = create_complaint(name="Audit Test User", area="Kabwe Central", issue="Low water pressure")
    assert ticket_id is not None

    # Verify initial status in DB is "OPEN"
    with sqlite3.connect(storage.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ticket = conn.execute("SELECT * FROM water_complaints WHERE ticket_id = ?", (ticket_id,)).fetchone()
        assert ticket["status"] == "OPEN"
        assert ticket["assigned_to"] is None
        assert ticket["priority"] == "NORMAL"

    # 2. Update Status
    status_response = client.post(
        f"/admin/complaints/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=ADMIN_HEADERS,
    )
    assert status_response.status_code == 200
    assert status_response.json()["success"] is True

    # 3. Add a Complaint Note
    note_response = client.post(
        f"/admin/complaints/{ticket_id}/note",
        json={"note": "Assigned technician to inspect local booster pump"},
        headers=ADMIN_HEADERS,
    )
    assert note_response.status_code == 200
    assert note_response.json()["success"] is True

    # 4. Assign Complaint to an Agent
    assign_response = client.post(
        f"/admin/complaints/{ticket_id}/assign",
        json={"assigned_to": "technician_mwansa"},
        headers=ADMIN_HEADERS,
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["success"] is True

    # 5. Update Priority
    priority_response = client.post(
        f"/admin/complaints/{ticket_id}/priority",
        json={"priority": "HIGH"},
        headers=ADMIN_HEADERS,
    )
    assert priority_response.status_code == 200
    assert priority_response.json()["success"] is True

    # 6. Verify audit logs in SQLite DB
    with sqlite3.connect(storage.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        logs = conn.execute(
            "SELECT * FROM audit_logs WHERE user_id = ? ORDER BY timestamp ASC",
            ("static_admin",)
        ).fetchall()
        
        # We expect at least 4 logs corresponding to our 4 admin actions above
        assert len(logs) >= 4
        
        # Validate status change log
        status_log = next(log for log in logs if log["action"] == "UPDATE_COMPLAINT_STATUS")
        assert status_log["resource"] == ticket_id
        status_details = json.loads(status_log["details"])
        assert status_details["before"]["status"] == "OPEN"
        assert status_details["after"]["status"] == "IN_PROGRESS"

        # Validate add note log
        note_log = next(log for log in logs if log["action"] == "ADD_COMPLAINT_NOTE")
        assert note_log["resource"] == ticket_id
        note_details = json.loads(note_log["details"])
        assert len(note_details["before"]["notes"]) == 0
        assert len(note_details["after"]["notes"]) == 1
        assert "technician to inspect" in note_details["after"]["notes"][0]["note"]

        # Validate assign log
        assign_log = next(log for log in logs if log["action"] == "ASSIGN_COMPLAINT")
        assert assign_log["resource"] == ticket_id
        assign_details = json.loads(assign_log["details"])
        assert assign_details["before"]["assigned_to"] is None
        assert assign_details["after"]["assigned_to"] == "technician_mwansa"

        # Validate priority change log
        priority_log = next(log for log in logs if log["action"] == "UPDATE_COMPLAINT_PRIORITY")
        assert priority_log["resource"] == ticket_id
        priority_details = json.loads(priority_log["details"])
        assert priority_details["before"]["priority"] == "NORMAL"
        assert priority_details["after"]["priority"] == "HIGH"
