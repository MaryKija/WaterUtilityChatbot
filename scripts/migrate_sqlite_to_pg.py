#!/usr/bin/env python3
"""scripts/migrate_sqlite_to_pg.py

Data migration utility to migrate LgWSC data from SQLite to PostgreSQL.
Usage:
    export DATABASE_URL="postgresql://user:pass@host:port/dbname"
    python scripts/migrate_sqlite_to_pg.py
"""

import os
import sys
import sqlite3
import psycopg2
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.storage import DB_PATH

def migrate():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable must be set.")
        sys.exit(1)

    print(f"Connecting to source SQLite database: {DB_PATH}")
    if not DB_PATH.exists():
        print("Error: Source SQLite database file does not exist.")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    print(f"Connecting to target PostgreSQL database...")
    try:
        pg_conn = psycopg2.connect(database_url)
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sys.exit(1)

    # Tables to migrate
    tables = [
        "water_complaints",
        "escalations",
        "session_context",
        "conversation_history",
        "conversation_history_pii",
        "intent_suggestions",
        "intent_labels",
        "intent_candidates",
        "intent_metrics",
        "new_connections",
        "mock_customers",
        "mock_accounts",
        "mock_bills",
        "mock_payments",
        "mock_outages",
        "mock_offices",
        "session_metrics",
        "user_feedback",
        "admin_resolution",
        "customer_auth",
        "audit_logs"
    ]

    for table in tables:
        print(f"Migrating table: {table}...")
        try:
            # Check if table exists in SQLite
            sqlite_cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
            if sqlite_cursor.fetchone()[0] == 0:
                print(f"  Table {table} does not exist in SQLite source. Skipping.")
                continue

            # Fetch columns and data
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            columns = [desc[0] for desc in sqlite_cursor.description]

            if not rows:
                print(f"  Table {table} is empty. Skipping.")
                continue

            # Clear existing data in target PostgreSQL (optional, safe default is DO NOTHING)
            # We use ON CONFLICT DO NOTHING to avoid duplicate key errors if run multiple times
            placeholders = ", ".join(["%s"] * len(columns))
            cols_str = ", ".join(columns)

            # Build query
            insert_query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"

            # For tables with primary keys, add ON CONFLICT DO NOTHING
            primary_keys = {
                "water_complaints": "ticket_id",
                "escalations": "escalation_id",
                "session_context": "user_id",
                "intent_suggestions": "suggestion_id",
                "intent_candidates": "candidate_id",
                "new_connections": "ticket_id",
                "mock_customers": "customer_id",
                "mock_accounts": "account_number",
                "mock_bills": "bill_id",
                "mock_payments": "payment_id",
                "mock_outages": "area",
                "mock_offices": "branch_name",
                "session_metrics": "session_id",
                "user_feedback": "feedback_id",
                "admin_resolution": "resolution_id",
                "customer_auth": "account_number",
                "audit_logs": "log_id"
            }

            if table in primary_keys:
                pk = primary_keys[table]
                insert_query += f" ON CONFLICT ({pk}) DO NOTHING"
            elif table in ["conversation_history", "conversation_history_pii", "intent_labels", "intent_metrics"]:
                # Auto-increment tables, no PK or sequential id PK
                insert_query += " ON CONFLICT DO NOTHING"

            print(f"  Inserting {len(rows)} records...")
            pg_cursor.executemany(insert_query, rows)
            pg_conn.commit()
            print(f"  Successfully migrated {len(rows)} records from {table}.")

        except Exception as e:
            pg_conn.rollback()
            print(f"  Error migrating table {table}: {e}")

    sqlite_conn.close()
    pg_conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
