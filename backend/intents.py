"""backend/intents.py

Single source of truth for allowed intent names.

The application enforces this list to avoid random intent creation.
"""

ALLOWED_INTENTS = [
    "general_chat",
    "report_fault",
    "billing_inquiry",
    "new_connection",
    "complaint_followup",
    "leak_report",
    "meter_problem",
    "payment_info",
    "office_info",
    "escalation",
    "out_of_scope",
]

ALLOWED_INTENTS_SET = set(ALLOWED_INTENTS)
