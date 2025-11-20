#!/bin/bash
# Quick test script for WHOOP daily data

echo "=================================="
echo "WHOOP Daily Data Test - Quick Start"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with WHOOP credentials"
    echo ""
    echo "Required variables:"
    echo "  WHOOP_CLIENT_ID=your_client_id"
    echo "  WHOOP_CLIENT_SECRET=your_client_secret"
    echo "  WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback"
    echo "  SUPABASE_URL=your_supabase_url"
    echo "  SUPABASE_KEY=your_supabase_key"
    exit 1
fi

echo "✅ .env file found"
echo ""

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not active"
    echo "Consider activating it first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate  # or venv\\Scripts\\activate on Windows"
    echo ""
fi

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Dependencies not installed"
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies ready"
echo ""

# Create test_output directory if it doesn't exist
mkdir -p test_output

# Run the test
echo "🚀 Starting WHOOP daily data test..."
echo ""
python tests/test_user_daily_data.py
