<<<<<<< HEAD
# backend/tools.py

from .storage import create_complaint, get_complaint, create_connection_request
import random
from datetime import datetime, timedelta
from .logger import logger


def log_complaint(data: dict):
    """Log a water utility complaint"""
    required_fields = ["name", "area", "issue"]

=======
"""Tool layer for water utility customer-service actions.

The functions in this module deliberately look like integration adapters. In
the demo they read seeded SQLite data, but the same boundaries can later be
replaced by real CRM, billing, outage-management, payment, and branch systems.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .logger import logger
from .regulatory import (
    BILLING_DISPUTE_DISCLOSURE,
    LIABILITY_LIMIT_DISCLOSURE,
    complaint_timeline_disclosure,
)
from .storage import (
    check_area_outage as storage_check_area_outage,
    create_complaint,
    create_connection_request as storage_create_connection_request,
    get_complaint,
    get_customer_account as storage_get_customer_account,
    get_latest_bill as storage_get_latest_bill,
    get_office as storage_get_office,
    get_payment_status as storage_get_payment_status,
)


# ---------------------------------------------------------------------------
# Date / time formatting helpers
# ---------------------------------------------------------------------------

def _fmt_datetime(iso_str: str | None) -> str:
    """Convert an ISO 8601 timestamp to a friendly human-readable string.

    Input:  "2026-05-19T22:33:55.117681+00:00"
    Output: "19 May 2026, 10:33 PM"

    Falls back to the raw string if parsing fails.
    Works on both Windows (%#d) and Linux/Mac (%-d).
    """
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        # Day without leading zero — Windows uses %#d, Linux/Mac uses %-d
        import platform
        day_fmt = "%#d" if platform.system() == "Windows" else "%-d"
        return dt.strftime(f"{day_fmt} %b %Y, %I:%M %p").lstrip("0")
    except Exception:
        return str(iso_str)


def _fmt_date(iso_str: str | None) -> str:
    """Convert an ISO date or datetime to a short date string.

    Input:  "2026-05-28" or "2026-05-28T00:00:00+00:00"
    Output: "28 May 2026"

    Works on both Windows and Linux/Mac.
    """
    if not iso_str:
        return "—"
    try:
        raw = str(iso_str).split("T")[0]
        dt = datetime.strptime(raw, "%Y-%m-%d")
        import platform
        day_fmt = "%#d" if platform.system() == "Windows" else "%-d"
        return dt.strftime(f"{day_fmt} %b %Y")
    except Exception:
        return str(iso_str)


def is_valid_name(name: str) -> bool:
    return len(name.strip()) > 1


def is_valid_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?1?\d{9,15}$", phone))


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def get_customer_account(account_number: str):
    """Read customer/account details from the mock CRM/account registry."""

    return storage_get_customer_account(str(account_number or "").strip())


def get_latest_bill(account_number: str):
    """Read the latest bill from the mock billing system."""

    return storage_get_latest_bill(str(account_number or "").strip())


def get_payment_status(account_number: str):
    """Read payment reconciliation status from the mock payment system."""

    return storage_get_payment_status(str(account_number or "").strip())


def check_area_outage(area: str):
    """Read outage status from the mock operations/outage system."""

    return storage_check_area_outage(str(area or "").strip())


def create_complaint_ticket(*, name: str, area: str, issue: str, ticket_id: str | None = None) -> str:
    """Create a complaint ticket in the mock complaints/CRM system."""

    return create_complaint(name=name, area=area, issue=issue, ticket_id=ticket_id)


def log_complaint(data: dict):
    """Log a water utility complaint."""

    required_fields = ["name", "area", "issue"]
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    missing = [field for field in required_fields if field not in data]

    if missing:
        return (
            "I still need the following information before logging your complaint:"
<<<<<<< HEAD
            + "\n" + "\n".join(f"- {field}" for field in missing)
        )

    # At this point, data is guaranteed to be complete
=======
            + "\n"
            + "\n".join(f"- {field}" for field in missing)
        )

>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    name = data["name"]
    area = data["area"]
    issue = data["issue"]

<<<<<<< HEAD
    ticket_id = create_complaint(
=======
    outage = check_area_outage(area)
    ticket_id = create_complaint_ticket(
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
        name=name,
        area=area,
        issue=issue,
        ticket_id=(data.get("ticket_id") or None),
    )

    logger.info(f"Logged complaint ticket={ticket_id} name={name} area={area} issue={issue}")

<<<<<<< HEAD
    return (
        f"✅ **Complaint Logged Successfully**\n\n"
        f"**Reference Number:** {ticket_id}\n"
        f"**Issue:** {issue}\n"
        f"**Area:** {area}\n\n"
        "Save this reference number to track your complaint status.\n\n"
        "We'll investigate and respond within 24-48 hours."
=======
    outage_note = ""
    if outage and outage.status.upper() == "ACTIVE":
        outage_note = (
            f"\n\nKnown Area Notice: {outage.description}\n"
            f"Estimated Restoration: {_fmt_datetime(outage.estimated_restore_at)}"
        )

    # Infer priority from category for the SLA disclosure
    from .storage import infer_complaint_category, infer_complaint_priority
    category = infer_complaint_category(issue)
    priority = infer_complaint_priority(category, issue)
    timeline = complaint_timeline_disclosure(priority)

    return (
        f"Complaint Logged Successfully\n\n"
        f"Reference Number: {ticket_id}\n\n"
        f"Issue: {issue}\n"
        f"Area: {area}"
        f"{outage_note}\n\n"
        f"Save this reference number: {ticket_id}\n"
        f"Use it to track your complaint status anytime.\n\n"
        f"{timeline}\n\n"
        f"{LIABILITY_LIMIT_DISCLOSURE}"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    )


def get_complaint_status(ticket_id: str):
<<<<<<< HEAD
    """Get the status of a complaint by ticket ID"""
    complaint = get_complaint(ticket_id)
    
    if not complaint:
        return (
            f"❌ **Complaint Not Found**\n\n"
            f"I couldn't find a complaint with reference **{ticket_id}**.\n\n"
            "Please check the reference number or contact support."
        )
    
    return (
        f"✅ **Complaint Status**\n\n"
        f"**Reference:** {complaint.ticket_id}\n"
        f"**Status:** {complaint.status.upper()}\n"
        f"**Created:** {complaint.created_at}\n\n"
        f"**Issue:** {complaint.issue}\n"
        f"**Area:** {complaint.area}\n\n"
        "Need help? Type 'agent' to speak with a representative."
=======
    """Get the status of a complaint by ticket ID."""

    if isinstance(ticket_id, dict):
        ticket_id = str(ticket_id.get("ticket_id") or ticket_id.get("ticket") or "").strip()
    ticket_id = str(ticket_id or "").strip()

    complaint = get_complaint(ticket_id)

    if not complaint:
        return (
            f"Complaint Not Found\n\n"
            f"I could not find a complaint with reference {ticket_id}.\n\n"
            "Please check the reference number or contact support."
        )

    updated_line = ""
    if complaint.updated_at and complaint.updated_at != complaint.created_at:
        updated_line = f"\nLast Updated: {_fmt_datetime(complaint.updated_at)}"

    return (
        f"Complaint Status\n\n"
        f"Reference: {complaint.ticket_id}\n"
        f"Status: {str(complaint.status).upper()}\n"
        f"Logged: {_fmt_datetime(complaint.created_at)}"
        f"{updated_line}\n\n"
        f"Issue: {complaint.issue}\n"
        f"Area: {complaint.area}\n\n"
        f"Need help? Type 'human agent' to speak with a representative."
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    )


def get_bill(account_number: str):
<<<<<<< HEAD
    """Get billing information for an account (mock data for now)"""
    # Mock billing data - in production this would query a real billing system
    mock_bills = {
        "123456": {"amount": 245.60, "due_date": "2026-02-28", "status": "unpaid"},
        "789012": {"amount": 180.30, "due_date": "2026-02-15", "status": "unpaid"},
        "555666": {"amount": 0.00, "due_date": "2026-03-01", "status": "paid"},
    }
    
    # Generate random bill for unknown accounts
    if account_number not in mock_bills:
        # SEED using the account number to keep data consistent
        random.seed(account_number)
        
        amount = round(random.uniform(150, 400), 2)
        due_days = random.randint(10, 30)
        due_date = (datetime.now() + timedelta(days=due_days)).strftime("%Y-%m-%d")
        bill_data = {"amount": amount, "due_date": due_date, "status": "unpaid"}
    
        random.seed()  # Reset seed to system time for other operations
    else:
        bill_data = mock_bills[account_number]
    
    if bill_data["status"] == "paid":
        return (
            f"💳 **Billing Information**\n\n"
            f"**Account:** {account_number}\n"
            f"**Current Balance:** K0.00\n"
            f"**Status:** ✅ PAID\n\n"
            "Your account is up to date. Thank you for your payment!"
        )
    
    return (
        f"💳 **Billing Information**\n\n"
        f"**Account:** {account_number}\n"
        f"**Amount Due:** K{bill_data['amount']}\n"
        f"**Due Date:** {bill_data['due_date']}\n"
        f"**Status:** ⚠️ UNPAID\n\n"
        "To see payment options, ask: **payment methods**."
=======
    """Get billing information from seeded SQLite mock utility systems.

    Computes the itemised bill using the LgWSC tariff schedule appropriate
    for the customer's category (domestic metered or commercial/institutional).
    """
    from .tariffs import (
        calculate_bill,
        format_bill_breakdown,
        get_schedule_for_category,
    )

    account_number = str(account_number or "").strip()
    account = get_customer_account(account_number)
    if not account:
        logger.info(f"Billing lookup account_not_found account={account_number}")
        return (
            "I could not find that account number in the LgWSC billing system.\n\n"
            "Please check the number on your bill or meter card and try again."
        )

    bill = get_latest_bill(account_number)
    if not bill:
        logger.info(f"Billing lookup bill_not_found account={account_number}")
        return (
            f"Account {account_number} was found for {account.customer_name}, "
            "but there is no current bill on record."
        )

    payment = get_payment_status(account_number)
    payment_line = ""
    if payment:
        payment_line = (
            f"\nLatest Payment: K{payment.amount:.2f} via {payment.method} "
            f"({payment.status}, Ref: {payment.reference})"
        )

    if bill.status.upper() == "PAID" or float(bill.amount_due) <= 0:
        return (
            "Billing Information — LgWSC\n\n"
            f"Account: {account_number}\n"
            f"Customer: {account.customer_name}\n"
            f"Area: {account.area}\n"
            f"Billing Period: {bill.billing_period}\n"
            "Current Balance: K0.00\n"
            "Status: PAID"
            f"{payment_line}\n\n"
            "Your account is up to date. Thank you for your payment!"
        )

    # Derive consumption from meter reading (current reading assumed as monthly usage)
    consumption_m3 = float(bill.last_meter_reading) / 1000.0  # reading in litres → m³

    # Select tariff schedule based on customer category
    schedule = get_schedule_for_category(account.account_status or "Residential")
    breakdown = calculate_bill(consumption_m3, schedule)

    bill_detail = format_bill_breakdown(breakdown, bill.billing_period)

    return (
        "Billing Information — LgWSC\n\n"
        f"Account: {account_number}\n"
        f"Customer: {account.customer_name}\n"
        f"Area: {account.area}\n"
        f"Meter No: {account.meter_number}\n"
        f"Tariff: {breakdown.schedule_name}\n\n"
        f"{bill_detail}\n"
        f"Due Date: {_fmt_date(bill.due_date)}\n"
        f"Status: {bill.status.upper()}"
        f"{payment_line}\n\n"
        "To pay or see payment options, ask: payment methods.\n\n"
        f"{BILLING_DISPUTE_DISCLOSURE}"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    )


def escalate_to_human(*, include_account_number: bool = True):
<<<<<<< HEAD
    """Escalate the conversation to a human agent.

    Guardrail: only request an account number when it is relevant (e.g., billing).
    """
=======
    """Prepare a handoff form for a human customer-service agent."""
>>>>>>> 9a7f394 (Initial clean commit for capstone project)

    if include_account_number:
        return (
            "I will connect you to a customer service agent.\n\n"
            "Please provide:\n\n"
<<<<<<< HEAD
            "• Name\n"
            "• Phone Number\n"
            "• Account Number"
=======
            "- Name\n"
            "- Phone Number\n"
            "- Account Number"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
        )

    return (
        "I will connect you to a customer service agent.\n\n"
        "Please provide:\n\n"
<<<<<<< HEAD
        "• Name\n"
        "• Phone Number"
=======
        "- Name\n"
        "- Phone Number"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    )


def get_payment_methods():
<<<<<<< HEAD
    """Get information about available payment methods"""
    return (
        "💰 **Payment Methods**\n\n"
        "**1. Mobile Money**\n"
        "- MTN: *123*4*5#\n"
        "- Airtel: *115#\n"
        "- Zamtel: *555#\n\n"
        "**2. Bank Transfer**\n"
        "Account: 1234567890\n"
        "Bank: Zambia National Commercial Bank\n"
        "Branch: Main Branch\n\n"
        "**3. Office Payment**\n"
        "Visit any water utility office\n"
        "Cash or card accepted\n\n"
        "**4. Online Payment**\n"
        "Visit: www.waterutility.zm/pay\n\n"
        "Need your account number? Type 'billing'."
    )


def get_office_info():
    """Get office location and hours information"""
    return (
        "🏢 **Water Utility Office Information**\n\n"
        "**Main Office:**\n"
        "123 Water Street, City Center\n\n"
        "**Operating Hours:**\n"
        "Monday - Friday: 8:00 AM - 5:00 PM\n"
        "Saturday: 9:00 AM - 1:00 PM\n"
        "Sunday: Closed\n\n"
        "**Emergency Hotline (24/7):**\n"
        "+260 XXX XXX XXX\n\n"
        "**Email:**\n"
        "support@waterutility.zm\n\n"
        "**Branch Offices:**\n"
        "- Makululu Branch\n"
        "- Riverside Branch\n"
        "- Industrial Area Branch"
=======
    """Get LgWSC payment channel information."""

    return (
        "LgWSC Payment Methods\n\n"
        "1. Mobile Money\n"
        "   - MTN Mobile Money: Dial *303# → Payments → LgWSC\n"
        "   - Airtel Money: Dial *778# → Pay Bill → LgWSC\n"
        "   - Zamtel Kwacha: Dial *422# → Pay Bill → LgWSC\n\n"
        "2. Bank Transfer\n"
        "   Account Name: Lukanga Water Supply & Sanitation Co.\n"
        "   Bank: Zambia National Commercial Bank (ZANACO)\n"
        "   Branch: Kabwe Main Branch\n"
        "   Account No: 5490012345678\n\n"
        "3. FNB Zambia\n"
        "   Account No: 62012345678\n\n"
        "4. Stanbic Bank\n"
        "   Account No: 9130001234567\n\n"
        "5. Pay at LgWSC Office\n"
        "   Cash or card accepted at any LgWSC service centre.\n"
        "   Head Office: Independence Avenue, Kabwe\n"
        "   Hours: Mon–Fri 08:00–17:00, Sat 09:00–13:00\n\n"
        "Always quote your Account Number as the payment reference."
    )


def get_office_info(branch_or_area: str | None = None):
    """Get LgWSC branch details from the office directory."""

    office = storage_get_office(branch_or_area)
    if not office:
        return (
            "I could not find that branch or area in the LgWSC office directory.\n\n"
            "LgWSC serves: Kabwe, Kapiri Mposhi, Mkushi, Serenje, Mumbwa, "
            "Chibombo, Chisamba, Shibuyunji, Itezhi-Tezhi, Chitambo, Luano and Ngabwe.\n\n"
            "Ask for a specific area, e.g. 'Kabwe office' or 'Serenje branch'."
        )

    # Parse the hours string into structured lines for readability
    hours_raw = office.hours
    hours_lines = [h.strip() for h in hours_raw.split(";") if h.strip()]
    hours_formatted = "\n  ".join(hours_lines)

    return (
        f"LgWSC — {office.branch_name}\n\n"
        f"Address: {office.address}\n"
        f"Phone:   {office.phone}\n"
        f"Email:   {office.email}\n\n"
        f"Operating Hours:\n"
        f"  {hours_formatted}\n"
        f"  Emergency faults: On-call 24/7 — report via this chatbot\n\n"
        f"To pay outside office hours:\n"
        f"  MTN Mobile Money:  *303#\n"
        f"  Airtel Money:      *778#\n"
        f"  Zazu / Zonke:      use your account number as reference"
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    )


def create_connection_request(data: dict) -> str:
<<<<<<< HEAD
    """Create a new connection request ticket"""
    from .storage import create_connection_request as _storage_create
    try:
        return _storage_create(data)
=======
    """Create a new connection request ticket in the mock CRM system."""

    try:
        return storage_create_connection_request(data)
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    except Exception as e:
        logger.error(f"Connection request failed: {e}")
        return "Sorry, I couldn't create the connection request. Please try again."
