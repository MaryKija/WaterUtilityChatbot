#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify flexible account number and ticket ID extraction
"""

import sys
import io
sys.path.insert(0, '.')

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.agent import _extract_account_number, _extract_ticket_id

def test_account_number_extraction():
    """Test various account number formats"""
    test_cases = [
        ("account_number: 123456", "123456"),
        ("2437684093", "2437684093"),
        ("My account is 123456", "123456"),
        ("account 987654", "987654"),
        ("My name is John and my account_number: 555666", "555666"),
        ("account_number: 123456 please help", "123456"),
    ]
    
    print("Testing Account Number Extraction:")
    print("=" * 60)
    
    for message, expected in test_cases:
        session = {}
        result = _extract_account_number(message, session)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} Input: '{message}'")
        print(f"  Expected: {expected}, Got: {result}")
        print()

def test_ticket_id_extraction():
    """Test various ticket ID formats"""
    test_cases = [
        ("ticket_id: WC-1234ABCD", "WC-1234ABCD"),
        ("WC-5678EFGH", "WC-5678EFGH"),
        ("My ticket is WC-9999ZZZZ", "WC-9999ZZZZ"),
        ("reference WC-1111AAAA", "WC-1111AAAA"),
        ("ticket WC-2222BBBB please check", "WC-2222BBBB"),
        ("ref: wc-3333cccc", "WC-3333CCCC"),
    ]
    
    print("\nTesting Ticket ID Extraction:")
    print("=" * 60)
    
    for message, expected in test_cases:
        session = {}
        result = _extract_ticket_id(message, session)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} Input: '{message}'")
        print(f"  Expected: {expected}, Got: {result}")
        print()

if __name__ == "__main__":
    test_account_number_extraction()
    test_ticket_id_extraction()
    print("\n" + "=" * 60)
    print("Test completed!")
