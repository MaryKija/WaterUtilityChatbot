# backend/tools.py

from .storage import create_complaint, get_complaint, create_connection_request
import random
from datetime import datetime, timedelta
from .logger import logger


def log_complaint(data: dict):
    """Log a water utility complaint"""
    required_fields = ["name", "area", "issue"]

    missing = [field for field in required_fields if field not in data]

    if missing:
        return (
            "I still need the following information before logging your complaint:"
            + "\n" + "\n".join(f"- {field}" for field in missing)
        )

    # At this point, data is guaranteed to be complete
    name = data["name"]
    area = data["area"]
    issue = data["issue"]

    ticket_id = create_complaint(
        name=name,
        area=area,
        issue=issue,
        ticket_id=(data.get("ticket_id") or None),
    )

    logger.info(f"Logged complaint ticket={ticket_id} name={name} area={area} issue={issue}")

    return (
        f"✅ **Complaint Logged Successfully**\n\n"
        f"**Reference Number:** {ticket_id}\n"
        f"**Issue:** {issue}\n"
        f"**Area:** {area}\n\n"
        "Save this reference number to track your complaint status.\n\n"
        "We'll investigate and respond within 24-48 hours."
    )


def get_complaint_status(ticket_id: str):
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
    )


def get_bill(account_number: str):
    """Get billing information for an account (mock data for now)"""
    # Mock billing data - in production this would query a real billing system
    mock_bills = {
        "123456": {"amount": 245.60, "due_date": "2026-02-28", "status": "unpaid"},
        "789012": {"amount": 180.30, "due_date": "2026-02-15", "status": "unpaid"},
        "555666": {"amount": 0.00, "due_date": "2026-03-01", "status": "paid"},
    }
    
    # Generate random bill for unknown accounts
    if account_number not in mock_bills:
        amount = round(random.uniform(150, 400), 2)
        due_date = (datetime.now() + timedelta(days=random.randint(10, 30))).strftime("%Y-%m-%d")
        bill_data = {"amount": amount, "due_date": due_date, "status": "unpaid"}
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
    )


def escalate_to_human(*, include_account_number: bool = True):
    """Escalate the conversation to a human agent.

    Guardrail: only request an account number when it is relevant (e.g., billing).
    """

    if include_account_number:
        return (
            "I will connect you to a customer service agent.\n\n"
            "Please provide:\n\n"
            "• Name\n"
            "• Phone Number\n"
            "• Account Number"
        )

    return (
        "I will connect you to a customer service agent.\n\n"
        "Please provide:\n\n"
        "• Name\n"
        "• Phone Number"
    )


def get_payment_methods():
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
    )


def create_connection_request(data: dict) -> str:
    """Create a new connection request ticket"""
    from .storage import create_connection_request as _storage_create
    try:
        return _storage_create(data)
    except Exception as e:
        logger.error(f"Connection request failed: {e}")
        return "Sorry, I couldn't create the connection request. Please try again."
