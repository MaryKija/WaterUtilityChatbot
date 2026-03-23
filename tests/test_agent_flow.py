import sys, json
sys.path.insert(0, r'c:\Users\WESLEY\Desktop\2026-Capstone Projects\MKija\agentic_whatsapp_bot')
from backend.main import ChatRequest, chat, sessions

def run_sequence(phone, seq):
    print(f"=== Conversation for {phone} ===")
    for m in seq:
        req = ChatRequest(phone=phone, message=m)
        out = chat(req)
        print('USER:', m)
        print('BOT:', out['reply'])
        print('INTENT:', out['intent'], 'CONF:', out['confidence'])
        print('SESSION:', sessions.get(phone))
        print('-'*50)

if __name__ == '__main__':
    # Combined fields in one message
    sessions.clear()
    run_sequence('+260100', ['Hi', 'Report a water fault', 'name: John, area: Makululu, issue: No water'])

    # Separate messages for each field
    sessions.clear()
    run_sequence('+260200', ['Report a water fault', 'Wesley', 'Makululu', 'No water'])
