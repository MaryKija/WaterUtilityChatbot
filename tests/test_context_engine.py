from backend.context_engine import (
    initialize_context,
    update_context,
    resolve_pending_question,
    extract_entities,
    expire_flow_if_needed,
)


def test_initialize_context_schema():
    ctx = initialize_context("260970000000")
    assert ctx["user_id"] == "260970000000"
    assert "flow" in ctx
    assert "entities" in ctx
    assert "conversation_history_head" in ctx


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
    sess["flow"] = "billing"
    sess["last_updated"] = "2000-01-01T00:00:00+00:00"
    sess2 = expire_flow_if_needed(sess)
    assert sess2.get("flow") is None
    assert sess2.get("flow_expired_notice")

