#!/usr/bin/env python
import sys
sys.path.insert(0, r'c:\Users\WESLEY\Desktop\2026-Capstone Projects\MKija\agentic_whatsapp_bot')

print("=== Testing new ticket ID format ===")
from backend.storage import create_complaint, get_complaint

for i in range(3):
    tid = create_complaint(name=f'TestUser{i}', area='TestArea', issue='Test issue')
    print(f"Generated ticket ID: {tid}")
    complaint = get_complaint(tid)
    print(f"  Retrieved: {complaint.ticket_id} - {complaint.name}")
    print()

print("\n=== Testing OpenRouter model config ===")
print("(Removed) OpenRouter config: project is Groq-only now")
