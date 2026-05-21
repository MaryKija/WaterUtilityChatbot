"""Billing intent must stay on structured flow, not LLM fallback."""

from backend.intent_pipeline import IntentPipeline
from backend.agent import run_agent
from backend.offline_classifier import classify_offline


def test_rule_billing_priority_on_check_balance():
    pipe = IntentPipeline()
    r = pipe.classify("I want to check my bill balance", {})
    assert r["intent"] == "billing_inquiry"
    assert r.get("source") == "rule_billing_priority"


def test_payment_question_routes_to_payment_info_not_billing_lookup():
    pipe = IntentPipeline()
    r = pipe.classify("How do I pay my water bill?", {})
    assert r["intent"] == "payment_info"
    assert r.get("source") == "rule_payment_info_priority"


def test_offline_payment_question_routes_to_payment_info():
    r = classify_offline("How do I pay my water bill?")
    assert r["intent"] == "payment_info"


def test_billing_continuation_after_bot_billing_cue():
    pipe = IntentPipeline()
    ctx = {
        "history": [
            {"role": "user", "text": "balance?"},
            {
                "role": "bot",
                "text": "I'm happy to help. To check your bill balance, I'll need your account number.",
            },
        ]
    }
    r = pipe.classify("kwanjiwa", ctx)
    assert r["intent"] == "billing_inquiry"
    assert r.get("source") == "rule_billing_continuation"


def test_run_agent_name_only_replies_with_numeric_account_hint(monkeypatch):
    monkeypatch.setattr(
        "backend.agent.classify_billing_subintent",
        lambda message, session: {"case": "bill_check"},
    )
    ctx = {
        "user_id": "u1",
        "entities": {},
    }
    text = run_agent(
        "kwanjiwa",
        {"intent": "billing_inquiry", "confidence": 0.95, "entities": {}},
        ctx,
    )
    assert "numeric account number" in text.lower()
    assert "6" in text or "digit" in text.lower()
