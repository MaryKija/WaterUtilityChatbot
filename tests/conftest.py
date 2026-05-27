"""Pytest configuration for the tests/ package."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

# These files match test_*.py but are legacy scripts / evaluation harnesses written
# against an old in-memory `sessions` API and sync `chat`. They are not pytest tests.
collect_ignore = [
    "test_agent_flow.py",
    "test_conversation_flows.py",
    "test_intents.py",
]


def _stub_classify_intent(message, session):
    lowered = (message or "").lower()
    if any(word in lowered for word in ("football", "sports", "homework", "coding", "politics")):
        return {"intent": "out_of_scope", "confidence": 1.0, "entities": {}}
    if any(word in lowered for word in ("agent", "human", "representative", "operator")):
        return {"intent": "escalation", "confidence": 0.95, "entities": {}}
    if any(word in lowered for word in ("bill", "balance", "account", "payment")):
        return {"intent": "billing_inquiry", "confidence": 0.95, "entities": {}}
    if any(word in lowered for word in ("leak", "outage", "no water", "fault")):
        return {"intent": "report_fault", "confidence": 0.9, "entities": {}}
    if "office" in lowered:
        return {"intent": "office_info", "confidence": 0.9, "entities": {}}
    return {"intent": "general_chat", "confidence": 0.8, "entities": {}}


def _stub_generate_response(message, session=None, **kwargs):
    intent = kwargs.get("intent") or "general_chat"
    return f"Stubbed {intent} response."


def _stub_detect_human_request(message, session=None):
    lowered = (message or "").lower()
    return {"request_human": any(word in lowered for word in ("agent", "human", "representative"))}


def _stub_classify_billing_subintent(message, session=None):
    lowered = (message or "").lower()
    if "paid" in lowered or "not reflected" in lowered:
        return {"case": "payment_not_reflected"}
    if "wrong" in lowered or "too high" in lowered:
        return {"case": "wrong_bill"}
    return {"case": "bill_check"}


def pytest_runtest_setup(item):
    """Keep unit tests deterministic and offline by replacing Groq calls."""

    from backend.llm import groq_client
    import backend.agent as agent
    import backend.intent_pipeline as intent_pipeline
    import backend.orchestrator as orchestrator

    groq_client.classify_intent = _stub_classify_intent
    groq_client.generate_response = _stub_generate_response
    groq_client.detect_human_request = _stub_detect_human_request
    groq_client.classify_billing_subintent = _stub_classify_billing_subintent

    intent_pipeline.groq_classify_intent = _stub_classify_intent

    agent.generate_response = _stub_generate_response
    agent.detect_human_request = _stub_detect_human_request
    agent.classify_billing_subintent = _stub_classify_billing_subintent

    orchestrator.generate_response = _stub_generate_response


@pytest.fixture(autouse=True)
def isolated_sqlite_db(monkeypatch):
    """Use a fresh seeded SQLite database for every test.

    This keeps the suite independent from local demo data in `water_utility.db`
    and lets tests prove behavior from the seeded mock utility systems.
    """

    from backend import storage
    from backend.customer_auth import customer_auth_service

    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "False")

    db_dir = Path(__file__).resolve().parents[1] / ".test_dbs"
    db_dir.mkdir(exist_ok=True)
    test_db = db_dir / f"test_water_utility_{uuid4().hex}.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    monkeypatch.setattr(storage, "_LEGACY_DB_PATH", db_dir / "legacy_missing.db")
    # Redirect the customer_auth_service singleton to the same isolated DB.
    monkeypatch.setattr(customer_auth_service, "_db_path", test_db)
    storage.init_db()
    try:
        yield
    finally:
        try:
            test_db.unlink(missing_ok=True)
        except PermissionError:
            pass
