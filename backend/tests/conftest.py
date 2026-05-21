"""backend/tests/conftest.py

Pytest configuration for backend/tests/ package.

Provides:
- Groq stub (no real API calls)
- Isolated SQLite DB per test
- Orchestrator factory fixture
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Groq stubs — deterministic, offline replacements for all Groq calls
# ---------------------------------------------------------------------------

def _stub_classify_intent(message: str, session: dict) -> dict:
    """Deterministic intent classifier — no network calls."""
    lowered = (message or "").lower()
    if any(word in lowered for word in ("football", "sports", "homework", "coding",
                                         "politics", "weather", "recipe", "movie")):
        return {"intent": "out_of_scope", "confidence": 1.0, "entities": {}}
    if any(word in lowered for word in ("agent", "human", "representative", "operator",
                                         "speak to", "talk to")):
        return {"intent": "escalation", "confidence": 0.95, "entities": {}}
    if any(word in lowered for word in ("bill", "balance", "account", "payment", "owe", "due")):
        return {"intent": "billing_inquiry", "confidence": 0.95, "entities": {}}
    if any(word in lowered for word in ("leak", "outage", "no water", "fault", "report",
                                         "burst", "pipe", "pressure")):
        return {"intent": "report_fault", "confidence": 0.9, "entities": {}}
    if "connection" in lowered and "new" in lowered:
        return {"intent": "new_connection", "confidence": 0.9, "entities": {}}
    if "office" in lowered:
        return {"intent": "office_info", "confidence": 0.9, "entities": {}}
    return {"intent": "general_chat", "confidence": 0.8, "entities": {}}


def _stub_generate_response(message: str, session: dict = None, **kwargs) -> str:
    """Deterministic response generator — no network calls."""
    intent = kwargs.get("intent") or "general_chat"
    return f"Stubbed {intent} response."


def _stub_detect_human_request(message: str, session: dict = None) -> dict:
    lowered = (message or "").lower()
    return {
        "request_human": any(
            word in lowered for word in ("agent", "human", "representative", "operator")
        )
    }


def _stub_classify_billing_subintent(message: str, session: dict = None) -> dict:
    lowered = (message or "").lower()
    if "paid" in lowered or "not reflected" in lowered:
        return {"case": "payment_not_reflected"}
    if "wrong" in lowered or "too high" in lowered:
        return {"case": "wrong_bill"}
    return {"case": "bill_check"}


def pytest_runtest_setup(item):
    """Replace all Groq calls with deterministic stubs before each test."""
    from backend.llm import groq_client
    import backend.agent as agent_mod
    import backend.intent_pipeline as ip_mod
    import backend.orchestrator as orch_mod

    groq_client.classify_intent = _stub_classify_intent
    groq_client.generate_response = _stub_generate_response
    groq_client.detect_human_request = _stub_detect_human_request
    groq_client.classify_billing_subintent = _stub_classify_billing_subintent

    ip_mod.groq_classify_intent = _stub_classify_intent

    agent_mod.generate_response = _stub_generate_response
    agent_mod.detect_human_request = _stub_detect_human_request
    agent_mod.classify_billing_subintent = _stub_classify_billing_subintent

    orch_mod.generate_response = _stub_generate_response


# ---------------------------------------------------------------------------
# Isolated SQLite DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_sqlite_db(monkeypatch):
    """Use a fresh seeded SQLite database for every test."""
    from backend import storage

    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")

    db_dir = Path(__file__).resolve().parents[2] / ".test_dbs"
    db_dir.mkdir(exist_ok=True)
    test_db = db_dir / f"test_water_utility_{uuid4().hex}.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    monkeypatch.setattr(storage, "_LEGACY_DB_PATH", db_dir / "legacy_missing.db")
    storage.init_db()
    try:
        yield
    finally:
        try:
            test_db.unlink(missing_ok=True)
        except PermissionError:
            pass


# ---------------------------------------------------------------------------
# Orchestrator factory fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_orchestrator():
    """Return a factory that creates a fresh Orchestrator with isolated state."""
    from backend.config import config
    from backend.context_engine import ContextManager
    from backend.intent_pipeline import IntentPipeline
    from backend.tool_executor import ToolExecutor
    from backend.orchestrator import Orchestrator

    def _factory():
        return Orchestrator(config, ContextManager(), IntentPipeline(), ToolExecutor())

    return _factory
