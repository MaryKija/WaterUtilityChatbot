#!/usr/bin/env python3
"""
Database seeding script for Water Utility Chatbot.

This script creates a fresh database with sample data for development
and testing purposes. It should be run instead of committing
database files to the repository.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.storage import init_db, _connect, COMPLAINTS_TABLE, ESCALATIONS_TABLE, CUSTOMERS_TABLE, ACCOUNTS_TABLE, BILLS_TABLE, PAYMENTS_TABLE, OUTAGES_TABLE, OFFICES_TABLE


def create_sample_complaints():
    """Create sample complaint data."""
    complaints = [
        {
            "ticket_id": "WC-000001",
            "name": "John Banda",
            "area": "Lusaka",
            "issue": "Water leak in kitchen",
            "status": "OPEN",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "assigned_to": None,
            "notes": []
        },
        {
            "ticket_id": "WC-000002", 
            "name": "Mary Phiri",
            "area": "Kabwe",
            "issue": "No water supply",
            "status": "IN_PROGRESS",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "assigned_to": "Technician Team",
            "notes": [{"note": "Customer called to follow up", "timestamp": datetime.now(timezone.utc).isoformat()}]
        },
        {
            "ticket_id": "WC-000003",
            "name": "James Mwila", 
            "area": "Ndola",
            "issue": "Low water pressure",
            "status": "RESOLVED",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "updated_at": (datetime.now(timezone.utc) - timedelta(days=6)).isoformat(),
            "assigned_to": "Maintenance Team",
            "notes": [{"note": "Pressure regulator replaced", "timestamp": datetime.now(timezone.utc).isoformat()}]
        }
    ]
    
    with _connect() as conn:
        for complaint in complaints:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {COMPLAINTS_TABLE} 
                (ticket_id, name, area, issue, status, created_at, updated_at, assigned_to, notes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    complaint["ticket_id"],
                    complaint["name"], 
                    complaint["area"],
                    complaint["issue"],
                    complaint["status"],
                    complaint["created_at"],
                    complaint["updated_at"],
                    complaint["assigned_to"],
                    str(complaint["notes"])
                )
            )


def create_sample_escalations():
    """Create sample escalation data."""
    escalations = [
        {
            "escalation_id": f"ESC-{uuid.uuid4().hex[:8].upper()}",
            "ticket_id": "WC-000001",
            "user_id": "user_001",
            "reason": "Customer requested supervisor due to delayed response",
            "status": "ACTIVE",
            "messages": [
                {"role": "customer", "text": "I need to speak with a manager", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "agent", "text": "I'll escalate this to our supervisor", "timestamp": datetime.now(timezone.utc).isoformat()}
            ],
            "created_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    with _connect() as conn:
        for escalation in escalations:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {ESCALATIONS_TABLE}
                (escalation_id, ticket_id, user_id, reason, status, messages_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    escalation["escalation_id"],
                    escalation["ticket_id"],
                    escalation["user_id"],
                    escalation["reason"],
                    escalation["status"],
                    str(escalation["messages"]),
                    escalation["created_at"],
                    escalation["updated_at"]
                )
            )


def create_sample_customers():
    """Create enhanced Zambian customer data."""
    try:
        from generate_zambian_customers import generate_customers, save_to_database
        
        # Generate 50 customers for seeding (smaller than full generator)
        customers = generate_customers(50)
        save_to_database(customers)
        print(f"Created {len(customers)} Zambian customers")
    except ImportError:
        # Fallback to basic customers if generator not available
        print("Generator not available, creating basic customers")
        customers = [
            {
                "customer_id": "KABWE/1001/24",
                "first_name": "John",
                "surname": "Banda", 
                "full_name": "John Banda",
                "phone_number": "+260977123456",
                "email": "john.banda@email.com",
                "physical_address": "123 Main Street, Lusaka, Zambia",
                "postal_address": "P.O. Box 70001, Lusaka",
                "customer_category": "Residential",
                "account_status": "Active",
                "date_registered": "01/01/2023",
                "last_transaction": "15/05/2024",
                "total_spend_ZMW": 2500.00,
                "average_order_ZMW": 350.00,
                "preferred_payment": "MTN Mobile Money",
                "credit_limit_ZMW": 8000.00,
                "loyalty_score": 250,
                "primary_location": "Lusaka",
                "kabwe_central": "No",
                "annual_revenue_ZMW": 50000.00
            },
            {
                "customer_id": "KABWE/1002/24",
                "first_name": "Mary",
                "surname": "Phiri",
                "full_name": "Mary Phiri", 
                "phone_number": "+260977654321",
                "email": "mary.phiri@email.com",
                "physical_address": "456 Oak Avenue, Kabwe, Zambia",
                "postal_address": "P.O. Box 70002, Kabwe",
                "customer_category": "Residential",
                "account_status": "Active",
                "date_registered": "15/02/2023",
                "last_transaction": "10/05/2024",
                "total_spend_ZMW": 1800.00,
                "average_order_ZMW": 300.00,
                "preferred_payment": "Airtel Money",
                "credit_limit_ZMW": 10000.00,
                "loyalty_score": 300,
                "primary_location": "Kabwe",
                "kabwe_central": "Yes",
                "annual_revenue_ZMW": 75000.00
            }
        ]
        
        with _connect() as conn:
            for customer in customers:
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
                        customer["customer_id"],
                        customer["first_name"],
                        customer["surname"],
                        customer["full_name"],
                        customer["phone_number"],
                        customer["email"],
                        customer["physical_address"],
                        customer["postal_address"],
                        customer["customer_category"],
                        customer["account_status"],
                        customer["date_registered"],
                        customer["last_transaction"],
                        customer["total_spend_ZMW"],
                        customer["average_order_ZMW"],
                        customer["preferred_payment"],
                        customer["credit_limit_ZMW"],
                        customer["loyalty_score"],
                        customer["primary_location"],
                        customer["kabwe_central"],
                        customer["annual_revenue_ZMW"]
                    )
                )


def create_sample_bills():
    """Create sample billing data."""
    bills = [
        {
            "bill_id": f"BILL-{uuid.uuid4().hex[:8].upper()}",
            "account_number": "100001",
            "amount_due": 250.50,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
            "status": "PENDING",
            "billing_period": "2024-05",
            "last_meter_reading": 12345
        },
        {
            "bill_id": f"BILL-{uuid.uuid4().hex[:8].upper()}",
            "account_number": "100002", 
            "amount_due": 180.75,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            "status": "PAID",
            "billing_period": "2024-05",
            "last_meter_reading": 67890
        }
    ]
    
    with _connect() as conn:
        for bill in bills:
            conn.execute(
                f"""
                INSERT INTO {BILLS_TABLE}
                (bill_id, account_number, amount_due, due_date, status, billing_period, last_meter_reading)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bill["bill_id"],
                    bill["account_number"],
                    bill["amount_due"],
                    bill["due_date"],
                    bill["status"],
                    bill["billing_period"],
                    bill["last_meter_reading"]
                )
            )


def create_sample_outages():
    """Create sample outage data."""
    outages = [
        {
            "area": "Kabwe",
            "status": "ACTIVE",
            "description": "Scheduled maintenance for main water pipe replacement",
            "estimated_restore_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "area": "Ndola",
            "status": "RESOLVED",
            "description": "Electrical fault at pumping station - resolved",
            "estimated_restore_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "last_updated": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        }
    ]
    
    with _connect() as conn:
        for outage in outages:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {OUTAGES_TABLE}
                (area, status, description, estimated_restore_at, last_updated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    outage["area"],
                    outage["status"],
                    outage["description"],
                    outage["estimated_restore_at"],
                    outage["last_updated"]
                )
            )


def create_sample_offices():
    """Create sample office data."""
    offices = [
        {
            "branch_name": "Main Office",
            "area": "Lusaka",
            "address": "123 Independence Avenue, Lusaka",
            "hours": "Mon-Fri: 08:00-17:00, Sat: 08:00-13:00",
            "phone": "+260 211 000 000",
            "email": "info@waterutility.co.zm"
        },
        {
            "branch_name": "Kabwe Branch",
            "area": "Kabwe", 
            "address": "456 Church Road, Kabwe",
            "hours": "Mon-Fri: 08:00-16:30, Sat: 08:00-12:00",
            "phone": "+260 211 000 001",
            "email": "kabwe@waterutility.co.zm"
        }
    ]
    
    with _connect() as conn:
        for office in offices:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {OFFICES_TABLE}
                (branch_name, area, address, hours, phone, email)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    office["branch_name"],
                    office["area"],
                    office["address"],
                    office["hours"],
                    office["phone"],
                    office["email"]
                )
            )


def main():
    """Main seeding function."""
    print("🌱 Starting database seeding...")
    
    # Initialize database schema
    init_db()
    print("✅ Database schema initialized")
    
    # Create sample data
    create_sample_complaints()
    print("✅ Sample complaints created")
    
    create_sample_escalations()
    print("✅ Sample escalations created")
    
    create_sample_customers()
    print("✅ Sample customers created")
    
    create_sample_bills()
    print("✅ Sample bills created")
    
    create_sample_outages()
    print("✅ Sample outages created")
    
    create_sample_offices()
    print("✅ Sample offices created")
    
    print("🎉 Database seeding completed successfully!")
    print("\nDatabase is ready for development and testing.")
    print("Run 'python main.py' to start the application.")


if __name__ == "__main__":
    main()
