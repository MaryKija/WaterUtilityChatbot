"""backend/regulatory.py

LgWSC Regulatory Rules and Compliance Disclosures
===================================================

Encodes the public utility commission rules applicable to Lukanga Water
Supply and Sanitation Company (LgWSC) under the National Water Supply and
Sanitation Council of Zambia (NWASCO) Consumer Protection Guidelines.

Sources:
  - NWASCO Service Level Standards for Water and Sanitation Utilities
  - Water Supply and Sanitation Act, Cap 281 of the Laws of Zambia
  - LgWSC Customer Service Charter

All disclosure strings are designed to be appended verbatim to bot
responses so customers receive accurate regulatory information.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ---------------------------------------------------------------------------
# SLA response time targets (working hours)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SLATarget:
    """Service Level Agreement target for a complaint priority."""
    priority: str
    response_hours: int       # Acknowledgement target
    resolution_hours: int     # Full resolution target
    description: str


SLA_TARGETS: Dict[str, SLATarget] = {
    "URGENT": SLATarget(
        priority="URGENT",
        response_hours=2,
        resolution_hours=4,
        description="Health/safety emergencies (contaminated water, total supply failure)",
    ),
    "HIGH": SLATarget(
        priority="HIGH",
        response_hours=4,
        resolution_hours=24,
        description="Water quality issues, major leaks, extended outages",
    ),
    "NORMAL": SLATarget(
        priority="NORMAL",
        response_hours=24,
        resolution_hours=48,
        description="Standard service complaints, billing disputes, meter issues",
    ),
    "LOW": SLATarget(
        priority="LOW",
        response_hours=48,
        resolution_hours=72,
        description="General enquiries, minor service requests",
    ),
}

# Days after which an unresolved complaint may be escalated to NWASCO
NWASCO_ESCALATION_DAYS = 30


# ---------------------------------------------------------------------------
# Disconnection rules (NWASCO Consumer Protection Guidelines)
# ---------------------------------------------------------------------------

DISCONNECTION_NOTICE_DAYS = 14          # Minimum written notice before disconnection
DISCONNECTION_FORBIDDEN_DAYS = [        # Days on which disconnection is prohibited
    "Friday", "Saturday", "Sunday",
]
DISCONNECTION_FORBIDDEN_PUBLIC_HOLIDAYS = True   # No disconnections on public holidays

DISCONNECTION_NOTICE_DISCLOSURE = (
    "⚠️ Disconnection Notice: LgWSC is required to provide a minimum of "
    f"{DISCONNECTION_NOTICE_DAYS} days written notice before disconnecting your supply "
    "for non-payment. Disconnections do not occur on Fridays, weekends, or public "
    "holidays. If you believe a disconnection notice has been issued in error, contact "
    "LgWSC immediately on +260 215 221529 or visit the nearest branch."
)


# ---------------------------------------------------------------------------
# Billing dispute rules
# ---------------------------------------------------------------------------

BILLING_DISPUTE_DAYS = 30       # Days from bill date within which a dispute must be raised
DISPUTE_PROTECTION = True       # Supply cannot be disconnected while dispute is under investigation

BILLING_DISPUTE_DISCLOSURE = (
    "ℹ️ Billing Dispute Rights: You have the right to dispute this bill within "
    f"{BILLING_DISPUTE_DAYS} days of the billing date. While a valid dispute is under "
    "investigation, LgWSC may not disconnect your supply on the basis of the disputed "
    "amount. To raise a dispute, contact LgWSC at kabwe@lgwsc.co.zm or call "
    "+260 215 221529. Reference: NWASCO Consumer Protection Guidelines."
)


# ---------------------------------------------------------------------------
# Complaint escalation disclosure
# ---------------------------------------------------------------------------

def complaint_timeline_disclosure(priority: str) -> str:
    """Return the SLA timeline disclosure for a given complaint priority."""
    target = SLA_TARGETS.get(priority.upper(), SLA_TARGETS["NORMAL"])
    return (
        f"📋 Your complaint has been logged. LgWSC will acknowledge it within "
        f"{target.response_hours} hour(s) and aims to resolve it within "
        f"{target.resolution_hours} hour(s) in line with NWASCO service standards. "
        f"If your complaint is not resolved within {NWASCO_ESCALATION_DAYS} days, "
        "you may escalate to NWASCO at www.nwasco.org.zm or call +260 211 254 498."
    )


# ---------------------------------------------------------------------------
# Liability limit disclosure
# ---------------------------------------------------------------------------

LIABILITY_LIMIT_DISCLOSURE = (
    "⚖️ Liability Notice: LgWSC's liability is limited to the cost of water supplied "
    "under the current billing period. Claims for property damage or consequential loss "
    "must be submitted in writing to the LgWSC Head Office within 30 days of the "
    "incident. LgWSC is not liable for damage caused by customer-side plumbing faults."
)


# ---------------------------------------------------------------------------
# SLA status helper (used by admin dashboard)
# ---------------------------------------------------------------------------

def compute_sla_status(sla_due_at: str | None, status: str) -> str:
    """Return 'BREACHED', 'AT_RISK', 'ON_TRACK', or 'RESOLVED'.

    Args:
        sla_due_at: ISO 8601 UTC timestamp string from the complaint row.
        status: Current complaint status string.

    Returns:
        A string label for the SLA status.
    """
    from datetime import datetime, timezone, timedelta

    resolved_statuses = {"RESOLVED", "CLOSED"}
    if (status or "").upper() in resolved_statuses:
        return "RESOLVED"

    if not sla_due_at:
        return "ON_TRACK"

    try:
        due = datetime.fromisoformat(sla_due_at)
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        if now > due:
            return "BREACHED"
        if now > due - timedelta(hours=2):
            return "AT_RISK"
        return "ON_TRACK"
    except (ValueError, TypeError):
        return "ON_TRACK"
