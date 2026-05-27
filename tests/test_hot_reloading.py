"""Unit tests for Intent Candidate database registration and Hot-Reloading cache invalidation."""

import sqlite3
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from main import app
from backend import storage
from backend.intent_pipeline import intent_pipeline
from backend.storage import INTENT_CANDIDATES_TABLE

client = TestClient(app)
ADMIN_HEADERS = {"Authorization": "Bearer test-admin-token"}

def test_intent_hot_reloading_flow():
    # 1. Pipeline should not recognize "new_service_campaign" initially
    result_before = intent_pipeline.classify("Tell me about the new service campaign", {})
    assert result_before["intent"] != "new_service_campaign"

    # 2. Seed an active candidate intent in the database
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(storage.DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT INTO {INTENT_CANDIDATES_TABLE} (
                candidate_id, source_suggestion_id, label, handler, active, approvals_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "CAND-1234",
                "SUGG-1234",
                "new_service_campaign",
                "new_service_handler",
                1,  # Active
                json.dumps([{"approved_by": "admin", "at": now}]),
                now,
                now
            )
        )
        conn.commit()

    # 3. Trigger manual invalidation via endpoint
    response = client.post("/admin/intent_cache/invalidate", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # 4. Pipeline should now recognize the new active candidate intent!
    # Let's test the backend's intent_pipeline reload_cache explicitly too
    intent_pipeline.reload_cache()
    result_after = intent_pipeline.classify("Tell me about the new service campaign", {})
    assert result_after["intent"] == "new_service_campaign"
    assert result_after["source"] == "dynamic_active_candidate"
