@echo off
echo 🚀 Starting WhatsApp Bot Deployment...
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

REM Build customer chat frontend
echo 🔨 Building customer chat frontend...
cd frontend\aqua-chat-modern-main
if not exist "node_modules" (
    npm install
)
npm run build
if %errorlevel% neq 0 (
    echo ❌ Failed to build customer chat frontend
    cd ..\..
    pause
    exit /b 1
)

REM Build admin panel
echo 🔨 Building admin panel...
cd ..\admin
if not exist "node_modules" (
    npm install
)
npm run build
if %errorlevel% neq 0 (
    echo ❌ Failed to build admin panel
    cd ..\..
    pause
    exit /b 1
)

cd ..\..

REM Create production directories
if not exist "production" mkdir production
if not exist "production\frontend-customer" mkdir production\frontend-customer
if not exist "production\frontend-admin" mkdir production\frontend-admin

REM Copy built frontends
xcopy frontend\aqua-chat-modern-main\dist\* production\frontend-customer\ /E /I /H /Y
xcopy frontend\admin\dist\* production\frontend-admin\ /E /I /H /Y

echo ✅ Build complete!
echo.
echo 🎯 Deployment Summary:
echo   Backend API: Ready to run with 'python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000'
echo   Customer Chat: Available in production\frontend-customer\
echo   Admin Panel: Available in production\frontend-admin\
echo.
echo 💡 Next steps:
echo   1. Configure your web server ^(nginx/apache^) to serve the frontend directories
echo   2. Set up the backend as a Windows service or use a process manager
echo   3. Configure SSL certificates for HTTPS
echo   4. Set up monitoring and logging
echo.
pause