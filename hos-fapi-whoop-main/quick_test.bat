@echo off
REM Quick test script for WHOOP daily data (Windows)

echo ==================================
echo WHOOP Daily Data Test - Quick Start
echo ==================================
echo.

REM Check if .env exists
if not exist .env (
    echo ❌ .env file not found!
    echo Please create .env file with WHOOP credentials
    echo.
    echo Required variables:
    echo   WHOOP_CLIENT_ID=your_client_id
    echo   WHOOP_CLIENT_SECRET=your_client_secret
    echo   WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback
    echo   SUPABASE_URL=your_supabase_url
    echo   SUPABASE_KEY=your_supabase_key
    exit /b 1
)

echo ✅ .env file found
echo.

REM Check if virtual environment is active
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  Virtual environment not active
    echo Consider activating it first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo.
)

REM Check if dependencies are installed
echo 🔍 Checking dependencies...
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Dependencies not installed
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo ✅ Dependencies ready
echo.

REM Create test_output directory if it doesn't exist
if not exist test_output mkdir test_output

REM Run the test
echo 🚀 Starting WHOOP daily data test...
echo.
python tests\test_user_daily_data.py
