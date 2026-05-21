"""Regression: session history shape and entity extraction merge."""

from backend.llm import groq_client
from backend.intent_pipeline import IntentPipeline


def test_history_turn_text_prefers_text_then_content():
    assert groq_client._history_turn_text({}) == ""
    assert groq_client._history_turn_text({"text": " hello "}) == "hello"
    assert groq_client._history_turn_text({"content": "x"}) == "x"
    assert groq_client._history_turn_text({"text": "a", "content": "b"}) == "a"


def test_extract_entities_billing_returns_flat_dict_not_classification_blob():
    pipe = IntentPipeline()
    entities = pipe._extract_entities("I need to check my bill balance", {})
    assert isinstance(entities, dict)
    assert "intent" not in entities
    assert "confidence" not in entities
    assert "source" not in entities


def test_extract_entities_billing_adds_account_when_present():
    pipe = IntentPipeline()
    entities = pipe._extract_entities("bill balance for account 123456", {})
    assert entities.get("account_number") == "123456"
