# WHOOP API Test Suite

Comprehensive test scripts for testing the WHOOP API with Supabase authentication.

## Test Files Overview

### 1. interactive_test.py - Interactive Test Suite ⭐ **RECOMMENDED**
Complete interactive testing with guided flow and Supabase authentication

### 2. test_auth_flow.py - Automated Test Suite
End-to-end testing with colored output (requires manual Supabase JWT token)

### 3. quick_test.py - Quick API Tests
Simple script for testing individual endpoints

### 4. WHOOP_API_Postman_Collection.json - Postman Collection
Import into Postman for GUI-based testing

## Quick Start

```bash
# 1. Install dependencies
pip install requests supabase python-dotenv

# 2. Configure .env file (copy from .env.example and update)
# Make sure these variables are set:
#   SUPABASE_URL=https://your-project.supabase.co
#   SUPABASE_KEY=your_anon_key

# 3. Run interactive test (RECOMMENDED)
python tests/interactive_test.py

# The script will:
# - Load Supabase config from .env automatically
# - Prompt for WHOOP API URL (default: http://localhost:8001)
# - Prompt for your email and password
# - Guide you through WHOOP account linking
# - Help you sync and retrieve data
```

## Authentication Method

**Important:** The WHOOP API uses **Supabase authentication**, NOT the well-planned-api.

- The Flutter app (hos_mvp_2) authenticates directly with Supabase
- The test scripts authenticate directly with Supabase using the Supabase Python client
- After authentication, you get a JWT token to call the WHOOP API endpoints
- The well-planned-api is only for Google Calendar OAuth, not user authentication

## Detailed Usage Guide

See comments in each test file for detailed usage instructions.
