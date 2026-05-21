"""Regression: tool invocation must match Python signatures (kwargs vs single payload dict)."""

import asyncio

from backend.context_engine import initialize_context
from backend.tool_executor import ToolExecutor


def test_get_complaint_status_receives_string_ticket_id_not_entire_payload_dict():
    executor = ToolExecutor()
    context = initialize_context("user-tool-1")

    async def run() -> None:
        out = await executor.execute(
            "get_complaint_status",
            {"ticket_id": "WC-687SDN"},
            context,
        )
        assert "Error executing get_complaint_status" not in str(out)
        assert "dict" not in str(out).lower() or "Complaint" in str(out) or "Found" in str(out)

    asyncio.run(run())


def test_log_complaint_still_receives_full_payload_dict():
    executor = ToolExecutor()

    async def run() -> None:
        ctx = initialize_context("user-tool-2")
        out = await executor.execute(
            "log_complaint",
            {
                "name": "Test User",
                "area": "Area X",
                "issue": "No water",
            },
            ctx,
        )
        assert "Error executing log_complaint" not in str(out)
        assert "Logged" in str(out) or "Successfully" in str(out)

    asyncio.run(run())


def test_seeded_billing_lookup_does_not_fabricate_unknown_accounts():
    from backend.tools import get_bill

    # Account numbers were migrated: "123456" → "000001" (Mary Kija)
    known = get_bill("000001")
    assert "Mary Kija" in known
    assert "K94.02" in known  # LgWSC tariff: 12.84 m³ domestic metered

    unknown = get_bill("999999")
    assert "could not find" in unknown.lower()
    assert "K" not in unknown or "Amount Due" not in unknown


def test_tool_executor_records_observable_tool_selection_metadata():
    executor = ToolExecutor()
    context = initialize_context("user-tool-3")
    context["intent"] = "billing_inquiry"

    async def run() -> None:
        # Account numbers were migrated: "123456" → "000001" (Mary Kija)
        out = await executor.execute("get_bill", {"account_number": "000001"}, context)
        assert "Billing Information" in out
        assert context["last_tool_used"] == "get_bill"
        assert "billing system lookup" in context["last_tool_reason"]
        assert context["tool_trace"][-1]["tool"] == "get_bill"

    asyncio.run(run())
