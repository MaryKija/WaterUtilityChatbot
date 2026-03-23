@echo off
echo Starting agentic WhatsApp bot quietly...
python -m pip install -q -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo Dependencies install failed.
    pause
    exit /b 1
)
echo Dependencies OK. Starting server...
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 --log-level warning

