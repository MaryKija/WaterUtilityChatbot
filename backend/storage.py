from __future__ import annotations

import json
import sqlite3
import uuid
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from typing import Any, Optional, Dict, List


# HARD REQUIREMENT: Persist in SQLite `water_utility.db`.
# Back-compat: if an older `database.db` exists and the new DB doesn't,
# copy it over on first run so existing local data isn't lost.
DB_PATH = Path(__file__).resolve().parents[1] / "water_utility.db"
_LEGACY_DB_PATH = Path(__file__).resolve().parents[1] / "database.db"

COMPLAINTS_TABLE = "water_complaints"
ESCALATIONS_TABLE = "escalations"
SESSION_CONTEXT_TABLE = "session_context"

# New tables for context + self-learning intent discovery
CONVERSATION_HISTORY_TABLE = "conversation_history"
CONVERSATION_HISTORY_PII_TABLE = "conversation_history_pii"
INTENT_SUGGESTIONS_TABLE = "intent_suggestions"
INTENT_LABELS_TABLE = "intent_labels"
INTENT_CANDIDATES_TABLE = "intent_candidates"
INTENT_METRICS_TABLE = "intent_metrics"
NEW_CONNECTIONS_TABLE = "new_connections"
CUSTOMERS_TABLE = "mock_customers"
ACCOUNTS_TABLE = "mock_accounts"
BILLS_TABLE = "mock_bills"
PAYMENTS_TABLE = "mock_payments"
OUTAGES_TABLE = "mock_outages"
OFFICES_TABLE = "mock_offices"

# Evaluation and feedback tables
SESSION_METRICS_TABLE = "session_metrics"
USER_FEEDBACK_TABLE = "user_feedback"
ADMIN_RESOLUTION_TABLE = "admin_resolution"

# Customer PIN authentication table
CUSTOMER_AUTH_TABLE = "customer_auth"


ALLOWED_COMPLAINT_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "ESCALATED"}
ALLOWED_ESCALATION_STATUSES = {"WAITING", "ACTIVE", "CLOSED"}
ALLOWED_COMPLAINT_CATEGORIES = {
    "BILLING",
    "NO_WATER",
    "LEAK",
    "WATER_QUALITY",
    "METER",
    "PAYMENT",
    "NEW_CONNECTION",
    "OTHER",
}
ALLOWED_COMPLAINT_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Legacy DB migration (best-effort copy). SQLite doesn't support cross-file migration
    # without attach; for local dev we do a simple copy when safe.
    if (not DB_PATH.exists()) and _LEGACY_DB_PATH.exists():
        try:
            shutil.copy2(_LEGACY_DB_PATH, DB_PATH)
        except Exception:
            # If copy fails, proceed to create a new DB.
            pass
    return sqlite3.connect(DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(value: Any, *, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


@dataclass(frozen=True)
class Complaint:
    ticket_id: str
    name: str
    area: str
    issue: str
    status: str
    created_at: str
    updated_at: str
    assigned_to: Optional[str]
    notes: list[dict[str, Any]]
    category: str
    priority: str
    sla_due_at: Optional[str]


@dataclass(frozen=True)
class Escalation:
    escalation_id: str
    ticket_id: str
    user_id: str
    reason: str
    status: str
    messages: list[dict[str, Any]]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Connection:
    id: int
    ticket_id: str
    name: str
    address: str
    phone: str
    email: str
    status: str
    created_at: str


@dataclass(frozen=True)
class CustomerAccount:
    account_number: str
    customer_name: str
    phone: str
    email: str
    area: str
    address: str
    meter_number: str
    account_status: str


@dataclass(frozen=True)
class Bill:
    bill_id: str
    account_number: str
    amount_due: float
    due_date: str
    status: str
    billing_period: str
    last_meter_reading: int


@dataclass(frozen=True)
class Payment:
    payment_id: str
    account_number: str
    amount: float
    method: str
    status: str
    paid_at: str
    reference: str


@dataclass(frozen=True)
class Outage:
    area: str
    status: str
    description: str
    estimated_restore_at: str
    last_updated: str


@dataclass(frozen=True)
class SessionMetrics:
    session_id: str
    user_id: str
    start_time: str
    end_time: str
    total_turns: int
    avg_response_time_ms: float
    resolved: bool
    escalated: bool
    failed_intent_count: int
    intent_confidence_avg: float
    completion_rate: float
    escalation_rate: float


@dataclass(frozen=True)
class UserFeedback:
    feedback_id: str
    session_id: str
    user_id: str
    rating: int  # 1-5
    text_feedback: Optional[str]
    helpful: bool
    timestamp: str


@dataclass(frozen=True)
class AdminResolution:
    resolution_id: str
    session_id: str
    admin_user_id: str
    resolution_status: str  # RESOLVED, UNRESOLVED, ESCALATED
    admin_notes: Optional[str]
    resolution_time: str
    timestamp: str


@dataclass(frozen=True)
class Office:
    branch_name: str
    area: str
    address: str
    hours: str
    phone: str
    email: str


def init_db() -> None:
    """Initialize / upgrade local SQLite schema."""

    with _connect() as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {COMPLAINTS_TABLE} (
                ticket_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                area TEXT NOT NULL,
                issue TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                assigned_to TEXT,
                notes_json TEXT,
                category TEXT NOT NULL DEFAULT 'OTHER',
                priority TEXT NOT NULL DEFAULT 'NORMAL',
                sla_due_at TEXT
            )
            """
        )

        # Schema upgrade (for existing DBs).
        for ddl in [
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN updated_at TEXT",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN assigned_to TEXT",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN notes_json TEXT",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN category TEXT NOT NULL DEFAULT 'OTHER'",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN priority TEXT NOT NULL DEFAULT 'NORMAL'",
            f"ALTER TABLE {COMPLAINTS_TABLE} ADD COLUMN sla_due_at TEXT",
        ]:
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                # Duplicate column, etc.
                pass
        conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET category = 'OTHER' WHERE category IS NULL OR TRIM(category) = ''"
        )
        conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET priority = 'NORMAL' WHERE priority IS NULL OR TRIM(priority) = ''"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ESCALATIONS_TABLE} (
                escalation_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Persistent per-user session context ("progress")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SESSION_CONTEXT_TABLE} (
                user_id TEXT PRIMARY KEY,
                context_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Backward-compatible schema upgrade: add last_updated if missing.
        # (Hard requirement mentions `last_updated`; we keep `updated_at` for existing code.)
        try:
            conn.execute(f"ALTER TABLE {SESSION_CONTEXT_TABLE} ADD COLUMN last_updated TEXT")
        except sqlite3.OperationalError:
            pass

        # ------------------------------
        # Conversation logs (privacy-aware)
        # ------------------------------
        # `conversation_history` stores *redacted* text used for discovery/analytics.
        # `conversation_history_pii` stores the original text for restricted/admin-only access.
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CONVERSATION_HISTORY_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                text_redacted TEXT NOT NULL,
                flow TEXT,
                intent TEXT,
                confidence REAL,
                ts TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CONVERSATION_HISTORY_PII_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                text_original TEXT NOT NULL,
                ts TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_conv_hist_ts ON {CONVERSATION_HISTORY_TABLE}(ts)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_conv_hist_user_ts ON {CONVERSATION_HISTORY_TABLE}(user_id, ts)"
        )

        # ------------------------------
        # Self-learning intent discovery tables
        # ------------------------------
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_SUGGESTIONS_TABLE} (
                suggestion_id TEXT PRIMARY KEY,
                label_suggestion TEXT,
                confidence_score REAL,
                sample_utts_json TEXT NOT NULL,
                summary TEXT,
                example_action TEXT,
                status TEXT NOT NULL,
                groq_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_LABELS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suggestion_id TEXT NOT NULL,
                label TEXT NOT NULL,
                approved_by TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_CANDIDATES_TABLE} (
                candidate_id TEXT PRIMARY KEY,
                source_suggestion_id TEXT,
                label TEXT NOT NULL,
                handler TEXT,
                active INTEGER NOT NULL DEFAULT 0,
                approvals_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_intent_candidates_active ON {INTENT_CANDIDATES_TABLE}(active)"
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {INTENT_METRICS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL,
                precision REAL,
                recall REAL,
                f1 REAL,
                evaluated_at TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
            """
        )

        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_escalations_status ON {ESCALATIONS_TABLE}(status)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_escalations_user ON {ESCALATIONS_TABLE}(user_id)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_session_context_updated ON {SESSION_CONTEXT_TABLE}(updated_at)"
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {NEW_CONNECTIONS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_new_connections_status ON {NEW_CONNECTIONS_TABLE}(status)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_new_connections_ticket ON {NEW_CONNECTIONS_TABLE}(ticket_id)")

        # ------------------------------
        # Mock utility integration tables
        # ------------------------------
        # These represent the company systems a production deployment would call:
        # CRM/customer registry, billing, payment reconciliation, outages, and branches.
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CUSTOMERS_TABLE} (
                customer_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                surname TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                email TEXT,
                physical_address TEXT NOT NULL,
                postal_address TEXT,
                customer_category TEXT NOT NULL,
                account_status TEXT NOT NULL,
                date_registered TEXT NOT NULL,
                last_transaction TEXT,
                total_spend_ZMW REAL,
                average_order_ZMW REAL,
                preferred_payment TEXT,
                credit_limit_ZMW REAL,
                loyalty_score INTEGER,
                primary_location TEXT NOT NULL,
                kabwe_central TEXT,
                annual_revenue_ZMW REAL
            )
            """
        )
        
        # Migration for existing customers table (if it exists with old schema)
        # First check if table exists and has old columns
        try:
            cursor = conn.execute(f"PRAGMA table_info({CUSTOMERS_TABLE})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # If old schema detected, migrate data
            if 'name' in columns and 'first_name' not in columns:
                print("Migrating customers table to new schema...")
                
                # Get existing data
                cursor = conn.execute(f"SELECT * FROM {CUSTOMERS_TABLE}")
                old_data = cursor.fetchall()
                old_columns = [desc[0] for desc in cursor.description]
                
                # Drop old table
                conn.execute(f"DROP TABLE {CUSTOMERS_TABLE}")
                
                # Recreate with new schema
                conn.execute(
                    f"""
                    CREATE TABLE {CUSTOMERS_TABLE} (
                        customer_id TEXT PRIMARY KEY,
                        first_name TEXT NOT NULL,
                        surname TEXT NOT NULL,
                        full_name TEXT NOT NULL,
                        phone_number TEXT NOT NULL,
                        email TEXT,
                        physical_address TEXT NOT NULL,
                        postal_address TEXT,
                        customer_category TEXT NOT NULL,
                        account_status TEXT NOT NULL,
                        date_registered TEXT NOT NULL,
                        last_transaction TEXT,
                        total_spend_ZMW REAL,
                        average_order_ZMW REAL,
                        preferred_payment TEXT,
                        credit_limit_ZMW REAL,
                        loyalty_score INTEGER,
                        primary_location TEXT NOT NULL,
                        kabwe_central TEXT,
                        annual_revenue_ZMW REAL
                    )
                    """
                )
                
                # Migrate data
                for row in old_data:
                    old_row = dict(zip(old_columns, row))
                    
                    # Split name into first_name and surname
                    name_parts = old_row.get('name', '').split(' ', 1)
                    first_name = name_parts[0] if name_parts else 'Unknown'
                    surname = name_parts[1] if len(name_parts) > 1 else 'Unknown'
                    
                    conn.execute(
                        f"""
                        INSERT INTO {CUSTOMERS_TABLE}
                        (customer_id, first_name, surname, full_name, phone_number, email, 
                         physical_address, postal_address, customer_category, account_status,
                         date_registered, last_transaction, total_spend_ZMW, average_order_ZMW,
                         preferred_payment, credit_limit_ZMW, loyalty_score, primary_location,
                         kabwe_central, annual_revenue_ZMW)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            old_row.get('customer_id', f'LEGACY/{hash(str(old_row)) % 10000:04d}'),
                            first_name,
                            surname,
                            old_row.get('name', f'{first_name} {surname}'),
                            old_row.get('phone', '+260000000000'),
                            old_row.get('email', ''),
                            old_row.get('address', 'Unknown Address, Zambia'),
                            'P.O. Box 00000, Kabwe',
                            'Residential',  # Default category
                            old_row.get('account_status', 'Active'),
                            '01/01/2023',  # Default date
                            None,
                            0.0,  # Default spend
                            0.0,  # Default average
                            'Cash',  # Default payment
                            5000.0,  # Default credit
                            100,  # Default loyalty
                            'Kabwe',  # Default location
                            'No',
                            50000.0  # Default revenue
                        )
                    )
                
                print(f"Migrated {len(old_data)} customers to new schema")
                
        except sqlite3.OperationalError:
            # Table doesn't exist yet, will be created normally
            pass
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ACCOUNTS_TABLE} (
                account_number TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                area TEXT NOT NULL,
                address TEXT NOT NULL,
                meter_number TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {BILLS_TABLE} (
                bill_id TEXT PRIMARY KEY,
                account_number TEXT NOT NULL,
                amount_due REAL NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL,
                billing_period TEXT NOT NULL,
                last_meter_reading INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {PAYMENTS_TABLE} (
                payment_id TEXT PRIMARY KEY,
                account_number TEXT NOT NULL,
                amount REAL NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL,
                paid_at TEXT NOT NULL,
                reference TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {OUTAGES_TABLE} (
                area TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                estimated_restore_at TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {OFFICES_TABLE} (
                branch_name TEXT PRIMARY KEY,
                area TEXT NOT NULL,
                address TEXT NOT NULL,
                hours TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL
            )
            """
        )
        
        # Evaluation and feedback tables
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SESSION_METRICS_TABLE} (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                total_turns INTEGER NOT NULL,
                avg_response_time_ms REAL NOT NULL,
                resolved BOOLEAN NOT NULL,
                escalated BOOLEAN NOT NULL,
                failed_intent_count INTEGER NOT NULL,
                intent_confidence_avg REAL NOT NULL,
                completion_rate REAL NOT NULL,
                escalation_rate REAL NOT NULL
            )
            """
        )
        
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {USER_FEEDBACK_TABLE} (
                feedback_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                text_feedback TEXT,
                helpful BOOLEAN NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ADMIN_RESOLUTION_TABLE} (
                resolution_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                admin_user_id TEXT NOT NULL,
                resolution_status TEXT NOT NULL,
                admin_notes TEXT,
                resolution_time TEXT,
                timestamp TEXT NOT NULL
            )
            """
        )

        # Customer PIN authentication table (Requirements 2.1, 2.3)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CUSTOMER_AUTH_TABLE} (
                account_number  TEXT    PRIMARY KEY,
                pin_salt        TEXT    NOT NULL,
                pin_hash        TEXT    NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until    TEXT
            )
            """
        )

        # Audit log table — also created by AuthService._init_audit_tables() in auth.py,
        # but we ensure it exists here so that customer_auth audit events can be written
        # to the same isolated test DB without depending on the auth_service singleton.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN NOT NULL,
                details TEXT
            )
            """
        )

        _seed_mock_utility_data(conn)


def _migrate_account_numbers(conn: sqlite3.Connection) -> None:
    """Rename legacy demo account numbers to zero-padded sequential values.

    Mapping:
        "123456" → "000001"  (CUST-001 Mary Kija)
        "789012" → "000002"  (CUST-002 John Banda)
        "555666" → "000003"  (CUST-003 Aisha Phiri)

    The rename is performed inside a single SQLite transaction.  All FK
    references in ``mock_bills`` and ``mock_payments`` are updated in the
    same transaction.  Accounts that have already been migrated (i.e. the
    old account number is absent from ``mock_accounts``) are silently
    skipped.  If any step fails the entire transaction is rolled back and
    the exception is re-raised so ``init_db()`` fails fast.

    Requirements: 1.4, 7.1, 7.2, 7.4
    """
    # Mapping: old_account_number → new_account_number
    MIGRATION_MAP = [
        ("123456", "000001"),
        ("789012", "000002"),
        ("555666", "000003"),
    ]

    try:
        # Use an explicit savepoint so we can roll back just this migration
        # block without affecting the outer connection state managed by
        # init_db()'s `with _connect() as conn:` context manager.
        conn.execute("SAVEPOINT acct_migration")

        for old_acct, new_acct in MIGRATION_MAP:
            # Check whether the old account number still exists (skip if
            # already migrated).
            row = conn.execute(
                f"SELECT 1 FROM {ACCOUNTS_TABLE} WHERE account_number = ?",
                (old_acct,),
            ).fetchone()
            if row is None:
                # Already migrated or never existed — nothing to do.
                continue

            # 1. Rename in mock_accounts (PRIMARY KEY update via INSERT+DELETE
            #    because SQLite does not support renaming a PK in-place).
            conn.execute(
                f"""
                INSERT INTO {ACCOUNTS_TABLE}
                    (account_number, customer_id, area, address, meter_number, status)
                SELECT ?, customer_id, area, address, meter_number, status
                FROM {ACCOUNTS_TABLE}
                WHERE account_number = ?
                """,
                (new_acct, old_acct),
            )
            conn.execute(
                f"DELETE FROM {ACCOUNTS_TABLE} WHERE account_number = ?",
                (old_acct,),
            )

            # 2. Update FK references in mock_bills.
            conn.execute(
                f"UPDATE {BILLS_TABLE} SET account_number = ? WHERE account_number = ?",
                (new_acct, old_acct),
            )

            # 3. Update FK references in mock_payments.
            conn.execute(
                f"UPDATE {PAYMENTS_TABLE} SET account_number = ? WHERE account_number = ?",
                (new_acct, old_acct),
            )

            # 4. Update FK references in customer_auth (if the table already
            #    has a row for the old account number from a previous partial
            #    run).
            conn.execute(
                f"""
                UPDATE {CUSTOMER_AUTH_TABLE}
                SET account_number = ?
                WHERE account_number = ?
                """,
                (new_acct, old_acct),
            )

        conn.execute("RELEASE SAVEPOINT acct_migration")

    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT acct_migration")
        conn.execute("RELEASE SAVEPOINT acct_migration")
        raise


def _seed_mock_utility_data(conn: sqlite3.Connection) -> None:
    """Seed deterministic demo data for the mock utility integration tables."""

    now = _now()
    # LgWSC service areas: Kabwe (Capital) + 12 districts in Central Province
    customers = [
        ("CUST-001", "Mary", "Kija", "Mary Kija", "+260970000000", "mary.kija@example.com",
         "Plot 21 Kabwe Central Road, Kabwe, Central Province, Zambia", "P.O. Box 71001, Kabwe, 10101",
         "Residential", "Active", "01/01/2023", "15/05/2024", 2500.00, 350.00,
         "MTN Mobile Money", 8000.00, 250, "Kabwe", "Yes", 50000.00),
        ("CUST-002", "John", "Banda", "John Banda", "+260971111111", "john.banda@example.com",
         "House 14 Kapiri Mposhi Township, Kapiri Mposhi, Central Province, Zambia", "P.O. Box 71002, Kabwe, 10101",
         "Residential", "Active", "15/02/2023", "10/05/2024", 1800.00, 300.00,
         "Airtel Money", 10000.00, 300, "Kapiri Mposhi", "No", 75000.00),
        ("CUST-003", "Aisha", "Phiri", "Aisha Phiri", "+260972222222", "aisha.phiri@example.com",
         "Stand 8 Mkushi Industrial Area, Mkushi, Central Province, Zambia", "P.O. Box 71003, Kabwe, 10101",
         "Commercial", "Active", "01/03/2023", "20/05/2024", 5000.00, 800.00,
         "Stanbic Bank", 15000.00, 450, "Mkushi", "No", 150000.00),
    ]
    # Seed accounts with the new zero-padded account numbers (post-migration values).
    # On a fresh database these are inserted directly; on an existing database the
    # migration step above will have already renamed the old numbers.
    accounts = [
        ("000001", "CUST-001", "Kabwe", "Plot 21 Kabwe Central Road", "MTR-100001", "ACTIVE"),
        ("000002", "CUST-002", "Kapiri Mposhi", "House 14 Kapiri Mposhi Township", "MTR-100002", "ACTIVE"),
        ("000003", "CUST-003", "Mkushi", "Stand 8 Mkushi Industrial Area", "MTR-100003", "ACTIVE"),
    ]
    bills = [
        ("BILL-2026-001", "000001", 245.60, "2026-05-28", "UNPAID", "May 2026", 12840),
        ("BILL-2026-002", "000002", 180.30, "2026-05-21", "UNPAID", "May 2026", 9350),
        ("BILL-2026-003", "000003", 0.00, "2026-05-15", "PAID", "May 2026", 4420),
    ]
    payments = [
        ("PAY-001", "000001", 245.60, "MTN Mobile Money", "PENDING_RECONCILIATION", "2026-05-03T08:15:00+02:00", "MTN-88991"),
        ("PAY-002", "000003", 122.75, "Bank Transfer", "POSTED", "2026-05-01T10:20:00+02:00", "BNK-44102"),
    ]
    outages = [
        ("Kabwe", "ACTIVE", "Planned maintenance affecting parts of Kabwe Central.", "2026-05-04T18:00:00+02:00", now),
        ("Kapiri Mposhi", "RESOLVED", "Burst pipe repaired near Kapiri Mposhi Township.", "2026-05-03T14:30:00+02:00", now),
    ]
    offices = [
        # LgWSC branch offices — real addresses, phone numbers, and operating hours
        # Standard hours: Mon–Fri 08:00–17:00 | Sat 08:00–12:00 (payments/prepaid only)
        # Sun & Public Holidays: Closed (emergency fault teams on-call)
        (
            "Kabwe Branch", "Kabwe",
            "High Ridge Water Works, Kabwe",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 215 221529", "kabwe@lgwsc.co.zm",
        ),
        (
            "Kapiri Mposhi Branch", "Kapiri Mposhi",
            "Off Great North Road, Kapiri Mposhi",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 215 271025", "kapiri@lgwsc.co.zm",
        ),
        (
            "Mkushi Branch", "Mkushi",
            "Off Independence Avenue, Mkushi",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 215 362291", "mkushi@lgwsc.co.zm",
        ),
        (
            "Serenje Branch", "Serenje",
            "Off Ng'answa Road, Serenje",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 215 382065", "serenje@lgwsc.co.zm",
        ),
        (
            "Mumbwa Branch", "Mumbwa",
            "Main Township Operational Hub, Mumbwa",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 211 800385", "mumbwa@lgwsc.co.zm",
        ),
        (
            "Chibombo Branch", "Chibombo",
            "Main Boma District Area, Chibombo",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 215 274125", "chibombo@lgwsc.co.zm",
        ),
        (
            "Chisamba Branch", "Chisamba",
            "Main Township Area, Chisamba",
            "Mon-Fri 08:00-17:00; Sat 08:00-12:00 (payments & prepaid only); Sun/Holidays: Closed",
            "+260 211 611010", "chisamba@lgwsc.co.zm",
        ),
    ]

    conn.executemany(
        f"""
        INSERT OR IGNORE INTO {CUSTOMERS_TABLE}
        (customer_id, first_name, surname, full_name, phone_number, email, 
         physical_address, postal_address, customer_category, account_status,
         date_registered, last_transaction, total_spend_ZMW, average_order_ZMW,
         preferred_payment, credit_limit_ZMW, loyalty_score, primary_location,
         kabwe_central, annual_revenue_ZMW)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        customers,
    )

    # Run the account-number migration before inserting new seed rows so that
    # any existing old-format rows are renamed first.  Failures roll back the
    # entire migration and re-raise, causing init_db() to fail fast.
    _migrate_account_numbers(conn)

    conn.executemany(
        f"INSERT OR IGNORE INTO {ACCOUNTS_TABLE}(account_number, customer_id, area, address, meter_number, status) VALUES (?, ?, ?, ?, ?, ?)",
        accounts,
    )
    conn.executemany(
        f"INSERT OR IGNORE INTO {BILLS_TABLE}(bill_id, account_number, amount_due, due_date, status, billing_period, last_meter_reading) VALUES (?, ?, ?, ?, ?, ?, ?)",
        bills,
    )
    conn.executemany(
        f"INSERT OR IGNORE INTO {PAYMENTS_TABLE}(payment_id, account_number, amount, method, status, paid_at, reference) VALUES (?, ?, ?, ?, ?, ?, ?)",
        payments,
    )
    conn.executemany(
        f"INSERT OR IGNORE INTO {OUTAGES_TABLE}(area, status, description, estimated_restore_at, last_updated) VALUES (?, ?, ?, ?, ?)",
        outages,
    )
    conn.executemany(
        f"""
        INSERT INTO {OFFICES_TABLE}(branch_name, area, address, hours, phone, email)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(branch_name) DO UPDATE SET
            area    = excluded.area,
            address = excluded.address,
            hours   = excluded.hours,
            phone   = excluded.phone,
            email   = excluded.email
        """,
        offices,
    )

    # Demo PINs: 000001→"1234", 000002→"5678", 000003→"9012"
    # We seed PINs inline using the existing connection so that the mock_accounts
    # rows (inserted above) are visible without requiring a separate commit.
    import hashlib as _hashlib
    import os as _os
    for acct, pin in [("000001", "1234"), ("000002", "5678"), ("000003", "9012")]:
        row = conn.execute(
            f"SELECT 1 FROM {CUSTOMER_AUTH_TABLE} WHERE account_number = ?", (acct,)
        ).fetchone()
        if row is None:
            salt_hex = _os.urandom(32).hex()
            pin_hash = _hashlib.pbkdf2_hmac(
                "sha256", pin.encode(), bytes.fromhex(salt_hex), 260_000
            ).hex()
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {CUSTOMER_AUTH_TABLE}
                    (account_number, pin_salt, pin_hash, failed_attempts, locked_until)
                VALUES (?, ?, ?, 0, NULL)
                """,
                (acct, salt_hex, pin_hash),
            )


def next_account_number(conn: sqlite3.Connection) -> str:
    """Return the next zero-padded 6-digit account number.

    Queries ``SELECT MAX(CAST(account_number AS INTEGER)) FROM mock_accounts``
    to find the current maximum, increments by 1, and zero-pads the result to
    6 digits.

    Raises ``ValueError`` if the next value would exceed 999 999.

    This function **must be called inside a transaction** (i.e. within a
    ``with conn:`` block or after ``conn.execute("BEGIN")``).  Calling it
    outside a transaction does not prevent the query from running, but it
    cannot guarantee uniqueness against concurrent writers.
    """
    row = conn.execute(
        f"SELECT MAX(CAST(account_number AS INTEGER)) FROM {ACCOUNTS_TABLE}"
    ).fetchone()
    current_max = row[0] if row[0] is not None else 0
    next_val = current_max + 1
    if next_val > 999_999:
        raise ValueError(
            "Account number space exhausted (max 999999 reached)"
        )
    return f"{next_val:06d}"


def log_conversation_turn(
    *,
    user_id: str,
    role: str,
    text_redacted: str,
    text_original: str,
    ts: str | None = None,
    session_id: str | None = None,
    flow: str | None = None,
    intent: str | None = None,
    confidence: float | None = None,
) -> None:
    """Persist a single conversation turn.

    Privacy:
    - `conversation_history` receives redacted text only (safe for discovery/analytics).
    - `conversation_history_pii` receives the original text (restricted use only; no API endpoints expose it).
    """

    init_db()
    uid = (user_id or "").strip() or "unknown"
    role = (role or "").strip().lower() or "user"
    when = ts or _now()
    sid = (session_id or "").strip() or None
    tr = (text_redacted or "").strip()
    to = (text_original or "").strip()
    fl = (flow or "").strip() or None
    it = (intent or "").strip() or None
    conf = confidence if confidence is not None else None

    if not tr:
        tr = "[EMPTY]"
    if not to:
        to = "[EMPTY]"

    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {CONVERSATION_HISTORY_TABLE}(
                user_id, session_id, role, text_redacted, flow, intent, confidence, ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, sid, role, tr, fl, it, conf, when),
        )
        conn.execute(
            f"""
            INSERT INTO {CONVERSATION_HISTORY_PII_TABLE}(
                user_id, session_id, role, text_original, ts
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (uid, sid, role, to, when),
        )


def get_session_context(user_id: str) -> dict[str, Any]:
    """Load persisted session context for a user_id (or {} if none)."""

    init_db()
    uid = (user_id or "").strip() or "unknown"
    with _connect() as conn:
        row = conn.execute(
            f"SELECT context_json FROM {SESSION_CONTEXT_TABLE} WHERE user_id = ?",
            (uid,),
        ).fetchone()

    if not row:
        return {}

    ctx = _safe_json_loads(row[0], default={})
    return ctx if isinstance(ctx, dict) else {}


def upsert_session_context(user_id: str, context: dict[str, Any]) -> None:
    """Persist (insert/update) the session context for a user_id."""

    init_db()
    uid = (user_id or "").strip() or "unknown"
    payload = context if isinstance(context, dict) else {}
    now = _now()

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {SESSION_CONTEXT_TABLE} SET context_json = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(payload), now, uid),
        )
        if cur.rowcount <= 0:
            conn.execute(
                f"""
                INSERT INTO {SESSION_CONTEXT_TABLE}(user_id, context_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (uid, json.dumps(payload), now, now),
            )


def infer_complaint_category(issue: str) -> str:
    """Infer staff triage category from a customer issue description."""

    text = (issue or "").lower()
    if any(term in text for term in ["dirty", "brown", "smell", "smelly", "quality", "taste", "contaminated", "unsafe"]):
        return "WATER_QUALITY"
    if any(term in text for term in ["leak", "burst", "pipe", "flood"]):
        return "LEAK"
    if any(term in text for term in ["no water", "outage", "low pressure", "pressure", "supply"]):
        return "NO_WATER"
    if any(term in text for term in ["meter", "reading", "prepaid"]):
        return "METER"
    if any(term in text for term in ["payment", "paid", "not reflected", "receipt"]):
        return "PAYMENT"
    if any(term in text for term in ["bill", "billing", "balance", "charge"]):
        return "BILLING"
    if any(term in text for term in ["new connection", "connect", "connection"]):
        return "NEW_CONNECTION"
    return "OTHER"


def infer_complaint_priority(category: str, issue: str) -> str:
    """Infer staff triage priority from category and urgency words."""

    text = (issue or "").lower()
    if any(term in text for term in ["emergency", "danger", "sewage", "contaminated", "unsafe", "hospital", "school"]):
        return "URGENT"
    if category in {"LEAK", "WATER_QUALITY"}:
        return "HIGH"
    if category == "NO_WATER" and any(term in text for term in ["long", "days", "since yesterday", "all day", "entire"]):
        return "HIGH"
    if category in {"BILLING", "PAYMENT", "METER", "NO_WATER"}:
        return "NORMAL"
    return "LOW"


def calculate_sla_due_at(priority: str, created_at: str | None = None) -> str:
    base = datetime.fromisoformat(created_at) if created_at else datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    hours = {"URGENT": 4, "HIGH": 24, "NORMAL": 48, "LOW": 72}.get((priority or "").upper(), 48)
    return (base + timedelta(hours=hours)).isoformat()


def _complaint_from_row(row: Any) -> Complaint:
    notes = _safe_json_loads(row[8], default=[])
    if not isinstance(notes, list):
        notes = []
    return Complaint(
        ticket_id=row[0],
        name=row[1],
        area=row[2],
        issue=row[3],
        status=row[4],
        created_at=row[5],
        updated_at=row[6],
        assigned_to=row[7],
        notes=notes,
        category=row[9] or "OTHER",
        priority=row[10] or "NORMAL",
        sla_due_at=row[11],
    )


def create_complaint(
    *,
    name: str,
    area: str,
    issue: str,
    ticket_id: str | None = None,
    category: str | None = None,
    priority: str | None = None,
) -> str:
    """Create a complaint ticket and return ticket_id."""

    init_db()
    created_at = _now()
    issue_category = (category or infer_complaint_category(issue)).upper().strip()
    if issue_category not in ALLOWED_COMPLAINT_CATEGORIES:
        issue_category = "OTHER"
    issue_priority = (priority or infer_complaint_priority(issue_category, issue)).upper().strip()
    if issue_priority not in ALLOWED_COMPLAINT_PRIORITIES:
        issue_priority = "NORMAL"
    sla_due_at = calculate_sla_due_at(issue_priority, created_at)

    def _generate_ticket_id() -> str:
        import random
        import string

        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"WC-{chars}"

    for _ in range(3):
        tid = (ticket_id or _generate_ticket_id()).upper().strip()
        try:
            with _connect() as conn:
                conn.execute(
                    f"""
                    INSERT INTO {COMPLAINTS_TABLE}(
                        ticket_id, name, area, issue, status, created_at, updated_at,
                        assigned_to, notes_json, category, priority, sla_due_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tid,
                        name,
                        area,
                        issue,
                        "OPEN",
                        created_at,
                        created_at,
                        None,
                        "[]",
                        issue_category,
                        issue_priority,
                        sla_due_at,
                    ),
                )
            return tid
        except sqlite3.IntegrityError:
            ticket_id = None

    raise RuntimeError("Failed to allocate a unique ticket_id")


def list_complaints() -> list[Complaint]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                ticket_id,
                name,
                area,
                issue,
                status,
                created_at,
                COALESCE(updated_at, created_at) as updated_at,
                assigned_to,
                COALESCE(notes_json, '[]') as notes_json,
                COALESCE(category, 'OTHER') as category,
                COALESCE(priority, 'NORMAL') as priority,
                sla_due_at
            FROM {COMPLAINTS_TABLE}
            ORDER BY created_at DESC
            """
        ).fetchall()

    items: list[Complaint] = []
    for row in rows:
        items.append(_complaint_from_row(row))
    return items


def get_complaint(ticket_id: str) -> Complaint | None:
    init_db()
    tid = (ticket_id or "").upper().strip()
    if not tid:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                ticket_id,
                name,
                area,
                issue,
                status,
                created_at,
                COALESCE(updated_at, created_at) as updated_at,
                assigned_to,
                COALESCE(notes_json, '[]') as notes_json,
                COALESCE(category, 'OTHER') as category,
                COALESCE(priority, 'NORMAL') as priority,
                sla_due_at
            FROM {COMPLAINTS_TABLE}
            WHERE ticket_id = ?
            """,
            (tid,),
        ).fetchone()

    if not row:
        return None

    return _complaint_from_row(row)


def set_complaint_status(ticket_id: str, status: str) -> bool:
    init_db()

    tid = (ticket_id or "").upper().strip()
    st = (status or "").upper().strip()
    if not tid:
        return False
    if st not in ALLOWED_COMPLAINT_STATUSES:
        raise ValueError(f"Invalid complaint status: {st!r}")

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET status = ?, updated_at = ? WHERE ticket_id = ?",
            (st, _now(), tid),
        )
    return cur.rowcount > 0


def add_complaint_note(ticket_id: str, note: str, *, author: str = "agent") -> bool:
    init_db()

    tid = (ticket_id or "").upper().strip()
    note = (note or "").strip()
    if not tid:
        return False
    if not note:
        raise ValueError("note cannot be empty")

    complaint = get_complaint(tid)
    if not complaint:
        return False

    notes = list(complaint.notes or [])
    notes.append({"note": note, "author": author, "created_at": _now()})

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET notes_json = ?, updated_at = ? WHERE ticket_id = ?",
            (json.dumps(notes), _now(), tid),
        )
    return cur.rowcount > 0


def assign_complaint(ticket_id: str, assigned_to: str | None) -> bool:
    init_db()

    tid = (ticket_id or "").upper().strip()
    assignee = (assigned_to or "").strip() or None
    if not tid:
        return False

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET assigned_to = ?, updated_at = ? WHERE ticket_id = ?",
            (assignee, _now(), tid),
        )
    return cur.rowcount > 0


def set_complaint_priority(ticket_id: str, priority: str) -> bool:
    init_db()

    tid = (ticket_id or "").upper().strip()
    pr = (priority or "").upper().strip()
    if not tid:
        return False
    if pr not in ALLOWED_COMPLAINT_PRIORITIES:
        raise ValueError(f"Invalid complaint priority: {pr!r}")

    complaint = get_complaint(tid)
    if not complaint:
        return False
    sla_due_at = calculate_sla_due_at(pr, complaint.created_at)

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {COMPLAINTS_TABLE} SET priority = ?, sla_due_at = ?, updated_at = ? WHERE ticket_id = ?",
            (pr, sla_due_at, _now(), tid),
        )
    return cur.rowcount > 0


def create_escalation(
    *,
    ticket_id: str,
    user_id: str,
    reason: str,
    messages: Optional[list[dict[str, Any]]] = None,
) -> str:
    init_db()

    created_at = _now()
    reason = (reason or "").strip() or "complex_case"
    uid = (user_id or "").strip() or "unknown"
    tid = (ticket_id or "").upper().strip() or "WC-UNKNOWN"
    msgs = messages if isinstance(messages, list) else []

    def _generate_escalation_id() -> str:
        import random
        import string

        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ESC-{chars}"

    for _ in range(3):
        esc_id = _generate_escalation_id()
        try:
            with _connect() as conn:
                conn.execute(
                    f"""
                    INSERT INTO {ESCALATIONS_TABLE}(
                        escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        esc_id,
                        tid,
                        uid,
                        reason,
                        "WAITING",
                        json.dumps(msgs),
                        created_at,
                        created_at,
                    ),
                )
            return esc_id
        except sqlite3.IntegrityError:
            continue

    raise RuntimeError("Failed to allocate a unique escalation_id")


def list_escalations(*, status: str | None = None) -> list[Escalation]:
    init_db()
    st = (status or "").upper().strip() if status else None

    with _connect() as conn:
        if st:
            rows = conn.execute(
                f"""
                SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
                FROM {ESCALATIONS_TABLE}
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (st,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
                FROM {ESCALATIONS_TABLE}
                ORDER BY created_at DESC
                """
            ).fetchall()

    items: list[Escalation] = []
    for row in rows:
        msgs = _safe_json_loads(row[5], default=[])
        if not isinstance(msgs, list):
            msgs = []
        items.append(
            Escalation(
                escalation_id=row[0],
                ticket_id=row[1],
                user_id=row[2],
                reason=row[3],
                status=row[4],
                messages=msgs,
                created_at=row[6],
                updated_at=row[7],
            )
        )
    return items


def get_escalation(escalation_id: str) -> Escalation | None:
    init_db()
    eid = (escalation_id or "").upper().strip()
    if not eid:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
            FROM {ESCALATIONS_TABLE}
            WHERE escalation_id = ?
            """,
            (eid,),
        ).fetchone()

    if not row:
        return None

    msgs = _safe_json_loads(row[5], default=[])
    if not isinstance(msgs, list):
        msgs = []

    return Escalation(
        escalation_id=row[0],
        ticket_id=row[1],
        user_id=row[2],
        reason=row[3],
        status=row[4],
        messages=msgs,
        created_at=row[6],
        updated_at=row[7],
    )


def append_escalation_message(*, escalation_id: str, sender: str, text: str) -> bool:
    init_db()

    eid = (escalation_id or "").upper().strip()
    sender = (sender or "").strip().lower() or "user"
    text = (text or "").strip()
    if not eid or not text:
        return False

    esc = get_escalation(eid)
    if not esc:
        return False

    msgs = list(esc.messages or [])
    msgs.append({"sender": sender, "text": text, "created_at": _now()})

    new_status = esc.status
    if esc.status == "WAITING" and sender == "agent":
        new_status = "ACTIVE"

    with _connect() as conn:
        cur = conn.execute(
            f"""
            UPDATE {ESCALATIONS_TABLE}
            SET messages_json = ?, status = ?, updated_at = ?
            WHERE escalation_id = ?
            """,
            (json.dumps(msgs), new_status, _now(), eid),
        )
    return cur.rowcount > 0


def set_escalation_status(escalation_id: str, status: str) -> bool:
    init_db()

    eid = (escalation_id or "").upper().strip()
    st = (status or "").upper().strip()
    if not eid:
        return False
    if st not in ALLOWED_ESCALATION_STATUSES:
        raise ValueError(f"Invalid escalation status: {st!r}")

    with _connect() as conn:
        cur = conn.execute(
            f"UPDATE {ESCALATIONS_TABLE} SET status = ?, updated_at = ? WHERE escalation_id = ?",
            (st, _now(), eid),
        )
    return cur.rowcount > 0


def close_escalation(escalation_id: str) -> bool:
    return set_escalation_status(escalation_id, "CLOSED")


def find_open_escalation_for_user(user_id: str) -> Escalation | None:
    """Find the most recent non-closed escalation for a user."""

    init_db()
    uid = (user_id or "").strip() or "unknown"
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at
            FROM {ESCALATIONS_TABLE}
            WHERE user_id = ? AND status != 'CLOSED'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (uid,),
        ).fetchone()

    if not row:
        return None

    msgs = _safe_json_loads(row[5], default=[])
    if not isinstance(msgs, list):
        msgs = []

    return Escalation(
        escalation_id=row[0],
        ticket_id=row[1],
        user_id=row[2],
        reason=row[3],
        status=row[4],
        messages=msgs,
        created_at=row[6],
        updated_at=row[7],
    )


def list_connections() -> list[Connection]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT id, ticket_id, name, address, phone, email, status, created_at
            FROM {NEW_CONNECTIONS_TABLE}
            ORDER BY created_at DESC
            """
        ).fetchall()
    items: list[Connection] = []
    for row in rows:
        items.append(
            Connection(
                id=row[0],
                ticket_id=row[1],
                name=row[2],
                address=row[3],
                phone=row[4] or "",
                email=row[5] or "",
                status=row[6],
                created_at=row[7],
            )
        )
    return items


def get_connection(ticket_id: str) -> Connection | None:
    init_db()
    tid = (ticket_id or "").upper().strip()
    if not tid:
        return None
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT id, ticket_id, name, address, phone, email, status, created_at
            FROM {NEW_CONNECTIONS_TABLE}
            WHERE ticket_id = ?
            """,
            (tid,),
        ).fetchone()
        if not row:
            return None
        return Connection(
            id=row[0],
            ticket_id=row[1],
            name=row[2],
            address=row[3],
            phone=row[4] or "",
            email=row[5] or "",
            status=row[6],
            created_at=row[7],
        )


def create_connection_request(data: dict) -> str:
    """Create a new connection request and return ticket_id."""

    init_db()
    created_at = _now()

    def _generate_ticket_id() -> str:
        import random
        import string
        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"NC-{chars}"

    name = data.get("name", "").strip()
    address = data.get("address", "").strip()
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()

    if not name or not address:
        raise ValueError("name and address required")

    tid = _generate_ticket_id()
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT INTO {NEW_CONNECTIONS_TABLE}(
                ticket_id, name, address, phone, email, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tid, name, address, phone, email, "pending", created_at),
        )
    from .logger import logger
    logger.info(f"Created connection request ticket={tid} name={name} address={address}")
    return f"Connection request #{tid} created successfully for {name}."


def get_customer_account(account_number: str) -> CustomerAccount | None:
    """Fetch customer/account profile from the mock CRM/account registry."""

    init_db()
    acct = (account_number or "").strip()
    if not acct:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT
                a.account_number,
                c.full_name,
                COALESCE(c.phone_number, ''),
                COALESCE(c.email, ''),
                a.area,
                a.address,
                a.meter_number,
                a.status
            FROM {ACCOUNTS_TABLE} a
            JOIN {CUSTOMERS_TABLE} c ON c.customer_id = a.customer_id
            WHERE a.account_number = ?
            """,
            (acct,),
        ).fetchone()

    if not row:
        return None

    return CustomerAccount(
        account_number=row[0],
        customer_name=row[1],
        phone=row[2],
        email=row[3],
        area=row[4],
        address=row[5],
        meter_number=row[6],
        account_status=row[7],
    )


def get_latest_bill(account_number: str) -> Bill | None:
    """Fetch the latest bill from the mock billing system."""

    init_db()
    acct = (account_number or "").strip()
    if not acct:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT bill_id, account_number, amount_due, due_date, status, billing_period, last_meter_reading
            FROM {BILLS_TABLE}
            WHERE account_number = ?
            ORDER BY due_date DESC
            LIMIT 1
            """,
            (acct,),
        ).fetchone()

    if not row:
        return None

    return Bill(
        bill_id=row[0],
        account_number=row[1],
        amount_due=float(row[2]),
        due_date=row[3],
        status=row[4],
        billing_period=row[5],
        last_meter_reading=int(row[6]),
    )


def get_payment_status(account_number: str) -> Payment | None:
    """Fetch the most recent payment from the mock payment reconciliation system."""

    init_db()
    acct = (account_number or "").strip()
    if not acct:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT payment_id, account_number, amount, method, status, paid_at, reference
            FROM {PAYMENTS_TABLE}
            WHERE account_number = ?
            ORDER BY paid_at DESC
            LIMIT 1
            """,
            (acct,),
        ).fetchone()

    if not row:
        return None

    return Payment(
        payment_id=row[0],
        account_number=row[1],
        amount=float(row[2]),
        method=row[3],
        status=row[4],
        paid_at=row[5],
        reference=row[6],
    )


def check_area_outage(area: str) -> Outage | None:
    """Fetch outage information from the mock outage/service operations system."""

    init_db()
    area_norm = (area or "").strip()
    if not area_norm:
        return None

    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT area, status, description, estimated_restore_at, last_updated
            FROM {OUTAGES_TABLE}
            WHERE LOWER(area) = LOWER(?)
            """,
            (area_norm,),
        ).fetchone()

    if not row:
        return None

    return Outage(
        area=row[0],
        status=row[1],
        description=row[2],
        estimated_restore_at=row[3],
        last_updated=row[4],
    )


def get_office(branch_or_area: str | None = None) -> Office | None:
    """Fetch branch details from the mock branch/office directory."""

    init_db()
    target = (branch_or_area or "").strip()

    with _connect() as conn:
        if target:
            row = conn.execute(
                f"""
                SELECT branch_name, area, address, hours, phone, email
                FROM {OFFICES_TABLE}
                WHERE LOWER(branch_name) = LOWER(?) OR LOWER(area) = LOWER(?)
                ORDER BY CASE WHEN LOWER(area) = LOWER(?) THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (target, target, target),
            ).fetchone()
        else:
            row = conn.execute(
                f"""
                SELECT branch_name, area, address, hours, phone, email
                FROM {OFFICES_TABLE}
                WHERE branch_name = 'Main Office'
                LIMIT 1
                """
            ).fetchone()

    if not row:
        return None

    return Office(
        branch_name=row[0],
        area=row[1],
        address=row[2],
        hours=row[3],
        phone=row[4],
        email=row[5],
    )


# Evaluation and Feedback Functions

def create_session_metrics(metrics: SessionMetrics) -> None:
    """Store session metrics for evaluation."""
    init_db()
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {SESSION_METRICS_TABLE} 
            (session_id, user_id, start_time, end_time, total_turns, 
             avg_response_time_ms, resolved, escalated, failed_intent_count,
             intent_confidence_avg, completion_rate, escalation_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.session_id,
                metrics.user_id,
                metrics.start_time,
                metrics.end_time,
                metrics.total_turns,
                metrics.avg_response_time_ms,
                metrics.resolved,
                metrics.escalated,
                metrics.failed_intent_count,
                metrics.intent_confidence_avg,
                metrics.completion_rate,
                metrics.escalation_rate,
            ),
        )


def get_session_metrics(session_id: str) -> SessionMetrics | None:
    """Retrieve session metrics by session ID."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT session_id, user_id, start_time, end_time, total_turns,
                   avg_response_time_ms, resolved, escalated, failed_intent_count,
                   intent_confidence_avg, completion_rate, escalation_rate
            FROM {SESSION_METRICS_TABLE}
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

    if not row:
        return None

    return SessionMetrics(
        session_id=row[0],
        user_id=row[1],
        start_time=row[2],
        end_time=row[3],
        total_turns=row[4],
        avg_response_time_ms=row[5],
        resolved=bool(row[6]),
        escalated=bool(row[7]),
        failed_intent_count=row[8],
        intent_confidence_avg=row[9],
        completion_rate=row[10],
        escalation_rate=row[11],
    )


def create_user_feedback(feedback: UserFeedback) -> None:
    """Store user feedback for a session."""
    init_db()
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {USER_FEEDBACK_TABLE}
            (feedback_id, session_id, user_id, rating, text_feedback, helpful, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback.feedback_id,
                feedback.session_id,
                feedback.user_id,
                feedback.rating,
                feedback.text_feedback,
                feedback.helpful,
                feedback.timestamp,
            ),
        )


def get_user_feedback(session_id: str) -> UserFeedback | None:
    """Retrieve user feedback for a session."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT feedback_id, session_id, user_id, rating, text_feedback, helpful, timestamp
            FROM {USER_FEEDBACK_TABLE}
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()

    if not row:
        return None

    return UserFeedback(
        feedback_id=row[0],
        session_id=row[1],
        user_id=row[2],
        rating=row[3],
        text_feedback=row[4],
        helpful=bool(row[5]),
        timestamp=row[6],
    )


def list_user_feedback(*, limit: int = 20) -> list[UserFeedback]:
    """Return recent user feedback for staff review."""
    init_db()
    lim = max(1, min(limit or 20, 100))
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT feedback_id, session_id, user_id, rating, text_feedback, helpful, timestamp
            FROM {USER_FEEDBACK_TABLE}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()

    return [
        UserFeedback(
            feedback_id=row[0],
            session_id=row[1],
            user_id=row[2],
            rating=int(row[3]),
            text_feedback=row[4],
            helpful=bool(row[5]),
            timestamp=row[6],
        )
        for row in rows
    ]


def create_admin_resolution(resolution: AdminResolution) -> None:
    """Store admin resolution status for a session."""
    init_db()
    with _connect() as conn:
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {ADMIN_RESOLUTION_TABLE}
            (resolution_id, session_id, admin_user_id, resolution_status, 
             admin_notes, resolution_time, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolution.resolution_id,
                resolution.session_id,
                resolution.admin_user_id,
                resolution.resolution_status,
                resolution.admin_notes,
                resolution.resolution_time,
                resolution.timestamp,
            ),
        )


def get_admin_resolution(session_id: str) -> AdminResolution | None:
    """Get admin resolution for a session."""
    with _connect() as conn:
        row = conn.execute(
            f"""
            SELECT resolution_id, session_id, admin_user_id, resolution_status, admin_notes, resolution_time, timestamp
            FROM {ADMIN_RESOLUTION_TABLE}
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (session_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return AdminResolution(
            resolution_id=row[0],
            session_id=row[1],
            admin_user_id=row[2],
            resolution_status=row[3],
            admin_notes=row[4],
            resolution_time=row[5],
            timestamp=row[6]
        )


def get_conversation_history(session_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get conversation history for a session."""
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT role, text, timestamp
            FROM {CONVERSATION_HISTORY_TABLE}
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,)
        ).fetchall()
        
        if not rows:
            return None
        
        return [
            {
                "role": row[0],
                "text": row[1],
                "timestamp": row[2]
            }
            for row in rows
        ]


def get_dashboard_metrics() -> dict:
    """Get aggregated metrics for admin dashboard."""
    init_db()
    with _connect() as conn:
        # Total complaints
        total_complaints = conn.execute(
            f"SELECT COUNT(*) FROM {COMPLAINTS_TABLE}"
        ).fetchone()[0]

        # Average response time
        avg_response_time = conn.execute(
            f"SELECT AVG(avg_response_time_ms) FROM {SESSION_METRICS_TABLE}"
        ).fetchone()[0] or 0

        # Average satisfaction
        avg_satisfaction = conn.execute(
            f"SELECT AVG(rating) FROM {USER_FEEDBACK_TABLE} WHERE rating IS NOT NULL"
        ).fetchone()[0] or 0

        # Resolved complaints
        resolved_complaints = conn.execute(
            f"SELECT COUNT(*) FROM {COMPLAINTS_TABLE} WHERE status = 'RESOLVED'"
        ).fetchone()[0]

        open_complaints = conn.execute(
            f"SELECT COUNT(*) FROM {COMPLAINTS_TABLE} WHERE status IN ('OPEN', 'IN_PROGRESS', 'ESCALATED')"
        ).fetchone()[0]

        urgent_cases = conn.execute(
            f"""
            SELECT COUNT(*) FROM {COMPLAINTS_TABLE}
            WHERE priority IN ('URGENT', 'HIGH') AND status NOT IN ('RESOLVED', 'CLOSED')
            """
        ).fetchone()[0]

        resolved_today = conn.execute(
            f"""
            SELECT COUNT(*) FROM {COMPLAINTS_TABLE}
            WHERE status = 'RESOLVED' AND DATE(COALESCE(updated_at, created_at)) = DATE('now')
            """
        ).fetchone()[0]

        # Escalations
        escalations = conn.execute(
            f"SELECT COUNT(*) FROM {ESCALATIONS_TABLE}"
        ).fetchone()[0]

        # Most common intents
        common_intents = conn.execute(
            f"""
            SELECT intent, COUNT(*) as count
            FROM {CONVERSATION_HISTORY_TABLE}
            WHERE intent IS NOT NULL
            GROUP BY intent
            ORDER BY count DESC
            LIMIT 5
            """
        ).fetchall()

        cases_by_category = conn.execute(
            f"""
            SELECT COALESCE(category, 'OTHER') as category, COUNT(*) as count
            FROM {COMPLAINTS_TABLE}
            GROUP BY COALESCE(category, 'OTHER')
            ORDER BY count DESC, category ASC
            """
        ).fetchall()

        cases_by_area = conn.execute(
            f"""
            SELECT COALESCE(NULLIF(TRIM(area), ''), 'Unknown') as area, COUNT(*) as count
            FROM {COMPLAINTS_TABLE}
            GROUP BY COALESCE(NULLIF(TRIM(area), ''), 'Unknown')
            ORDER BY count DESC, area ASC
            LIMIT 8
            """
        ).fetchall()

        needs_attention = conn.execute(
            f"""
            SELECT ticket_id, name, area, issue, status, created_at, COALESCE(updated_at, created_at),
                   assigned_to, COALESCE(notes_json, '[]'), COALESCE(category, 'OTHER'),
                   COALESCE(priority, 'NORMAL'), sla_due_at
            FROM {COMPLAINTS_TABLE}
            WHERE priority IN ('URGENT', 'HIGH') AND status NOT IN ('RESOLVED', 'CLOSED')
            ORDER BY
                CASE priority WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END,
                COALESCE(sla_due_at, created_at) ASC
            LIMIT 8
            """
        ).fetchall()

        recent_feedback = conn.execute(
            f"""
            SELECT feedback_id, session_id, user_id, rating, text_feedback, helpful, timestamp
            FROM {USER_FEEDBACK_TABLE}
            ORDER BY timestamp DESC
            LIMIT 5
            """
        ).fetchall()

        return {
            "total_complaints": total_complaints,
            "avg_response_time_ms": round(avg_response_time, 2),
            "avg_satisfaction": round(avg_satisfaction, 2),
            "resolved_complaints": resolved_complaints,
            "open_complaints": open_complaints,
            "urgent_cases": urgent_cases,
            "resolved_today": resolved_today,
            "escalations": escalations,
            "common_intents": [{"intent": row[0], "count": row[1]} for row in common_intents],
            "cases_by_category": [{"category": row[0], "count": row[1]} for row in cases_by_category],
            "cases_by_area": [{"area": row[0], "count": row[1]} for row in cases_by_area],
            "needs_attention": [
                {
                    "ticket_id": c.ticket_id,
                    "name": c.name,
                    "area": c.area,
                    "issue": c.issue,
                    "status": c.status,
                    "category": c.category,
                    "priority": c.priority,
                    "sla_due_at": c.sla_due_at,
                    "assigned_to": c.assigned_to,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in (_complaint_from_row(row) for row in needs_attention)
            ],
            "recent_feedback": [
                {
                    "feedback_id": row[0],
                    "session_id": row[1],
                    "user_id": row[2],
                    "rating": row[3],
                    "text_feedback": row[4],
                    "helpful": bool(row[5]),
                    "timestamp": row[6],
                }
                for row in recent_feedback
            ],
        }


# ------------------------------
# Customer data management functions
# ------------------------------

def get_customer_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """Get customer by phone number."""
    with _connect() as conn:
        cursor = conn.execute(
            f"SELECT * FROM {CUSTOMERS_TABLE} WHERE phone_number = ?",
            (phone_number,)
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None


def get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
    """Get customer by customer ID."""
    with _connect() as conn:
        cursor = conn.execute(
            f"SELECT * FROM {CUSTOMERS_TABLE} WHERE customer_id = ?",
            (customer_id,)
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None


def get_customers_by_location(location: str) -> List[Dict[str, Any]]:
    """Get customers by location."""
    with _connect() as conn:
        cursor = conn.execute(
            f"SELECT * FROM {CUSTOMERS_TABLE} WHERE primary_location = ?",
            (location,)
        )
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []


def get_kabwe_central_customers() -> List[Dict[str, Any]]:
    """Get Kabwe central customers."""
    with _connect() as conn:
        cursor = conn.execute(
            f"SELECT * FROM {CUSTOMERS_TABLE} WHERE kabwe_central = 'Yes'"
        )
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []


def get_customers_by_category(category: str) -> List[Dict[str, Any]]:
    """Get customers by category."""
    with _connect() as conn:
        cursor = conn.execute(
            f"SELECT * FROM {CUSTOMERS_TABLE} WHERE customer_category = ?",
            (category,)
        )
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []


def get_vip_customers() -> List[Dict[str, Any]]:
    """Get VIP customers."""
    with _connect() as conn:
        cursor = conn.execute(
            f"SELECT * FROM {CUSTOMERS_TABLE} WHERE account_status = 'VIP'"
        )
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []


def search_customers(query: str) -> List[Dict[str, Any]]:
    """Search customers by name, phone, or email."""
    with _connect() as conn:
        cursor = conn.execute(
            f"""
            SELECT * FROM {CUSTOMERS_TABLE} 
            WHERE full_name LIKE ? OR phone_number LIKE ? OR email LIKE ?
            ORDER BY full_name
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%")
        )
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return []


def get_customer_statistics() -> Dict[str, Any]:
    """Get customer statistics and insights."""
    with _connect() as conn:
        total_customers = conn.execute(
            f"SELECT COUNT(*) FROM {CUSTOMERS_TABLE}"
        ).fetchone()[0]
        
        kabwe_central_count = conn.execute(
            f"SELECT COUNT(*) FROM {CUSTOMERS_TABLE} WHERE kabwe_central = 'Yes'"
        ).fetchone()[0]
        
        vip_count = conn.execute(
            f"SELECT COUNT(*) FROM {CUSTOMERS_TABLE} WHERE account_status = 'VIP'"
        ).fetchone()[0]
        
        total_spend = conn.execute(
            f"SELECT SUM(total_spend_ZMW) FROM {CUSTOMERS_TABLE}"
        ).fetchone()[0] or 0
        
        avg_loyalty = conn.execute(
            f"SELECT AVG(loyalty_score) FROM {CUSTOMERS_TABLE}"
        ).fetchone()[0] or 0
        
        # Category breakdown
        categories = conn.execute(
            f"""
            SELECT customer_category, COUNT(*) as count
            FROM {CUSTOMERS_TABLE}
            GROUP BY customer_category
            ORDER BY count DESC
            """
        ).fetchall()
        
        # Location breakdown
        locations = conn.execute(
            f"""
            SELECT primary_location, COUNT(*) as count
            FROM {CUSTOMERS_TABLE}
            GROUP BY primary_location
            ORDER BY count DESC
            """
        ).fetchall()
        
        return {
            "total_customers": total_customers,
            "kabwe_central_customers": kabwe_central_count,
            "vip_customers": vip_count,
            "total_spend_ZMW": round(total_spend, 2),
            "average_loyalty_score": round(avg_loyalty, 2),
            "categories": [{"category": row[0], "count": row[1]} for row in categories],
            "locations": [{"location": row[0], "count": row[1]} for row in locations],
        }


def update_customer_status(customer_id: str, status: str) -> bool:
    """Update customer account status."""
    with _connect() as conn:
        try:
            conn.execute(
                f"UPDATE {CUSTOMERS_TABLE} SET account_status = ? WHERE customer_id = ?",
                (status, customer_id)
            )
            return True
        except Exception:
            return False


def update_customer_loyalty(customer_id: str, loyalty_score: int) -> bool:
    """Update customer loyalty score."""
    with _connect() as conn:
        try:
            conn.execute(
                f"UPDATE {CUSTOMERS_TABLE} SET loyalty_score = ? WHERE customer_id = ?",
                (loyalty_score, customer_id)
            )
            return True
        except Exception:
            return False


