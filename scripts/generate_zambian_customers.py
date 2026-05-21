#!/usr/bin/env python3
"""
Zambian Customer Data Generator for Water Utility Chatbot
Generates realistic Kabwe, Zambia customer data with local names and patterns
"""

import csv
import random
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from faker import Faker
from faker.providers import BaseProvider

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.storage import _connect, CUSTOMERS_TABLE, init_db

# Faker with Zambian focus
fake = Faker('en_US')

class ZambianNameProvider(BaseProvider):
    zambian_first_names = [
        'Chisomo', 'Tapiwa', 'Given', 'Malaika', 'Natasha', 'Precious', 'Grace', 
        'Emmanuel', 'David', 'Joseph', 'Mwila', 'Nelly', 'Mwansa', 'Chileshe', 
        'Kalumbu', 'Bwalya', 'Zoe', 'Lumbani', 'Chikondi', 'Esther', 'Abigail',
        'Miriam', 'Ruth', 'Rebecca', 'Sarah', 'Naomi', 'Hannah', 'Deborah', 'Lydia',
        'Peter', 'Andrew', 'James', 'John', 'Michael', 'Gabriel', 'Samuel', 'Daniel',
        'Elizabeth', 'Martha', 'Judith', 'Rachel', 'Leah', 'Bathsheba', 'Priscilla'
    ]
    
    zambian_surnames = [
        'Banda', 'Phiri', 'Mwale', 'Zulu', 'Sichone', 'Chanda', 'Sakala', 'Mhango', 
        'Tembo', 'Lunguni', 'Daka', 'Mwamba', 'Mulenga', 'Kunda', 'Musonda', 
        'Nyirenda', 'Mumba', 'Nkhoma', 'Mwanza', 'Shawa', 'Kaposa', 'Chileshe',
        'Bwalya', 'Kapembwa', 'Chikoti', 'Kasonde', 'Mwansa', 'Sichinga', 'Mwewa'
    ]

    def zambian_first_name(self):
        return self.random_element(self.zambian_first_names)

    def zambian_surname(self):
        return self.random_element(self.zambian_surnames)

    def zambian_full_name(self):
        return f"{self.zambian_first_name()} {self.zambian_surname()}"

# Add custom provider
fake.add_provider(ZambianNameProvider)

# Kabwe, Zambia specific data
KABWE_CITIES_DISTRICTS = [
    'Kabwe', 'Mkushi', 'Kapiri Mposhi', 'Serenje', 'Chibombo',
    'Ibenga', 'Mulungushi', 'Broken Hill'
]

ZAMBIAN_MOBILES = ['+260977', '+260955', '+260966', '+260976', '+260967']
KABWE_CUSTOMER_TYPES = ['Residential', 'Mining', 'Commercial', 'Agriculture', 'SME', 'Transport']
PAYMENT_METHODS = ['MTN Mobile Money', 'Airtel Money', 'Zamtel Kwacha', 'FNB Zambia', 'Stanbic Bank', 'Cash']

def generate_customers(count=100):
    """Generate Zambian customer data"""
    customers = []
    
    for i in range(count):
        main_location = random.choice(KABWE_CITIES_DISTRICTS)
        phone_prefix = random.choice(ZAMBIAN_MOBILES)
        
        customer = {
            'customer_id': f'KABWE/{random.randint(1000, 9999):04d}/{random.randint(24, 25):02d}',
            'first_name': fake.zambian_first_name(),
            'surname': fake.zambian_surname(),
            'full_name': fake.zambian_full_name(),
            'phone_number': f"{phone_prefix}{random.randint(100000, 999999)}",
            'email': fake.email().lower(),
            'physical_address': f"{fake.street_name()} Road, {main_location}, Central Province, Zambia",
            'postal_address': f"P.O. Box {random.randint(70000, 72000)}, Kabwe, 10101",
            'customer_category': random.choice(KABWE_CUSTOMER_TYPES),
            'account_status': random.choice(['Active', 'Inactive', 'Suspended', 'VIP']),
            'date_registered': fake.date_between(start_date='-2y', end_date='today').strftime('%d/%m/%Y'),
            'last_transaction': fake.date_between(start_date='-6m', end_date='today').strftime('%d/%m/%Y'),
            'total_spend_ZMW': round(random.uniform(2_500, 85_000), 2),
            'average_order_ZMW': round(random.uniform(350, 4_500), 2),
            'preferred_payment': random.choice(PAYMENT_METHODS),
            'credit_limit_ZMW': round(random.uniform(8_000, 45_000), 2),
            'loyalty_score': random.randint(25, 950),
            'primary_location': main_location,
            'kabwe_central': 'Yes' if main_location == 'Kabwe' and random.random() < 0.7 else 'No',
            'annual_revenue_ZMW': round(random.uniform(50_000, 2_500_000), 2)
        }
        customers.append(customer)
    
    return customers

def save_to_database(customers):
    """Save customers to SQLite database"""
    # Initialize database schema first
    init_db()
    
    with _connect() as conn:
        for customer in customers:
            conn.execute(
                f"""
                INSERT OR REPLACE INTO {CUSTOMERS_TABLE}
                (customer_id, first_name, surname, full_name, phone_number, email, 
                 physical_address, postal_address, customer_category, account_status,
                 date_registered, last_transaction, total_spend_ZMW, average_order_ZMW,
                 preferred_payment, credit_limit_ZMW, loyalty_score, primary_location,
                 kabwe_central, annual_revenue_ZMW)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer['customer_id'],
                    customer['first_name'],
                    customer['surname'],
                    customer['full_name'],
                    customer['phone_number'],
                    customer['email'],
                    customer['physical_address'],
                    customer['postal_address'],
                    customer['customer_category'],
                    customer['account_status'],
                    customer['date_registered'],
                    customer['last_transaction'],
                    customer['total_spend_ZMW'],
                    customer['average_order_ZMW'],
                    customer['preferred_payment'],
                    customer['credit_limit_ZMW'],
                    customer['loyalty_score'],
                    customer['primary_location'],
                    customer['kabwe_central'],
                    customer['annual_revenue_ZMW']
                )
            )

def save_to_csv(customers, filename):
    """Save customers to CSV file"""
    import pandas as pd
    df = pd.DataFrame(customers)
    df.to_csv(filename, index=False)
    return filename

def main():
    """Main generation function"""
    print("🇿🇲 Generating Zambian Customer Data for Water Utility...")
    
    # Generate customers
    customers = generate_customers(100)
    print(f"Generated {len(customers)} customers")
    
    # Save to database
    save_to_database(customers)
    print("Saved to database")
    
    # Save to CSV
    filename = save_to_csv(customers, 'Kabwe_ZAMBIA_CUSTOMERS_100.csv')
    print(f"Saved to {filename}")
    
    # Display insights
    import pandas as pd
    df = pd.DataFrame(customers)
    
    print("\nKABWE BUSINESS INSIGHTS:")
    kabwe_count = len(df[df['kabwe_central'] == 'Yes'])
    print(f"Kabwe Central customers: {kabwe_count} ({kabwe_count/len(df)*100:.1f}%)")
    print(f"Total spend (ZMW): {df['total_spend_ZMW'].sum():,.0f}")
    print(f"Top categories:\n{df['customer_category'].value_counts().head()}")
    
    print("\nCustomer data generation completed!")

if __name__ == "__main__":
    main()
