@echo off
echo 🚀 Starting WhatsApp Bot in Development Mode...
cd /d "%~dp0"

REM Check if .env exists
if not exist ".env" (
    echo ❌ Error: .env file not found. Please create it with your configuration.
    pause
    exit /b 1
)

REM Install Python dependencies
echo 📦 Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install Python dependencies
    pause
    exit /b 1
)

REM Install frontend dependencies and start dev servers
echo 🔨 Starting frontend development servers...

REM Start customer chat frontend (port 5173)
start "Customer Chat Frontend" cmd /c "cd frontend\aqua-chat-modern-main && npm install && npm run dev"

REM Start admin panel frontend (port 5174)
start "Admin Panel Frontend" cmd /c "cd frontend\admin && npm install && npm run dev"

REM Wait a moment for frontends to start
timeout /t 5 /nobreak > nul

REM Start backend API
echo 🌐 Starting backend API server on http://localhost:8000...
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 --log-level info

pause