import sys
sys.path.insert(0, r'c:\Users\WESLEY\Desktop\2026-Capstone Projects\MKija\agentic_whatsapp_bot')
from backend.main import ChatRequest, chat, sessions

sessions.clear()
phone='+260400'
seq=['Report water issue', 'Makululu', 'No water']

for m in seq:
    req=ChatRequest(phone=phone, message=m)
    out=chat(req)
    print('USER:', m)
    print('BOT:', out['reply'])
    print('INTENT:', out['intent'], 'CONF:', out['confidence'])
    print('SESSION:', sessions.get(phone))
    print('-'*60)
