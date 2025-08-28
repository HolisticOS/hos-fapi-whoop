# 🚀 WHOOP API Testing - Quick Start Guide

## Prerequisites

1. **Your WHOOP API is running**: `python -m app.main` (should show "WHOOP Microservice started successfully")
2. **Supabase tables created**: Run the migration script if not done yet
3. **Environment variables set**: WHOOP credentials, Supabase config, API keys

## 1. 🎮 Interactive Manual Testing (Recommended for First Test)

```bash
cd /mnt/c/dev_skoth/health-agent-main/hos-fapi-whoop-main
python tests/manual_testing_suite.py
```

**Select from the menu:**
- `1` - **Run All Tests** (comprehensive validation)
- `2` - **Test Basic Endpoints** (quick health check)
- `3` - **Test OAuth Flow** (WHOOP authorization simulation)
- `4` - **Test Data Endpoints** (user data retrieval)

## 2. 🔧 Quick Health Check

```bash
# Test if your API is responding
curl http://localhost:8001/

# Test health endpoints
curl http://localhost:8001/health/ready
curl http://localhost:8001/health/live
```

Expected responses:
```json
{
  "message": "WHOOP Health Metrics API",
  "version": "1.0.0-mvp"
}
```

## 3. 🔐 Test OAuth Configuration

```bash
# Get OAuth configuration
curl http://localhost:8001/api/v1/whoop/auth/oauth-config
```

Expected response:
```json
{
  "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth",
  "pkce_supported": true,
  "pkce_required": true,
  "default_scopes": ["offline", "read:profile", "read:cycles", "read:recovery", "read:sleep", "read:workouts"]
}
```

## 4. 🧪 Test with Real User Data

### Step 1: Start OAuth Flow
```bash
curl -X POST "http://localhost:8001/api/v1/whoop/auth/authorize" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "redirect_uri": "http://localhost:8001/callback",
    "scopes": ["read:profile", "read:recovery", "offline"]
  }'
```

### Step 2: Check User Auth Status
```bash
curl -X GET "http://localhost:8001/api/v1/auth/status/test_user_123" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

### Step 3: Test Data Retrieval (will show no data until OAuth is completed)
```bash
curl -X GET "http://localhost:8001/api/v1/data/recovery/test_user_123?days=7" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

## 5. 🎯 Test Client Status

```bash
curl -X GET "http://localhost:8001/api/v1/client-status" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

Expected response:
```json
{
  "service_status": "operational",
  "whoop_client": {
    "status": "operational",
    "base_url": "https://api.prod.whoop.com/developer/v1",
    "rate_limiting": {
      "minute_limit": 100,
      "daily_limit": 10000,
      "current_delay": 0.6
    }
  }
}
```

## 6. ⚡ Automated Test Suite

```bash
# Run all automated tests
pytest tests/automated_test_suite.py -v

# Run specific test categories
pytest tests/automated_test_suite.py::TestBasicEndpoints -v
pytest tests/automated_test_suite.py::TestOAuthFlow -v
pytest tests/automated_test_suite.py::TestDataEndpoints -v
```

## 7. 📊 Performance Testing

```bash
# Test rate limiting compliance
python tests/performance_load_tests.py
# Select option 1: "Rate Limiting Compliance Test"
```

## 8. 🔄 Complete Integration Test

```bash
# Test end-to-end workflows
python tests/end_to_end_integration_tests.py
```

## 🎯 What to Expect

### ✅ **Successful Results:**
- All health endpoints return `200 OK`
- OAuth config shows proper WHOOP API URLs
- Client status shows `operational`
- Database connection established (if tables exist)

### ⚠️ **Expected "Failures" (Normal for MVP):**
- Data endpoints return empty results (no real WHOOP tokens yet)
- Auth status shows `not_connected` (no OAuth completed)
- Some database operations may fail if using development mode

### 🚨 **Actual Errors to Investigate:**
- `500 Internal Server Error` responses
- Connection refused to `localhost:8001`
- Authentication failures with proper API keys
- Database connection errors after migration

## 🔧 Troubleshooting

### API Not Starting
```bash
# Check if running
curl http://localhost:8001/
# If connection refused, check:
python -m app.main  # Look for error messages
```

### Database Errors
```bash
# Check migration status
# Go to Supabase Dashboard → SQL Editor
# Verify tables exist: whoop_users, whoop_oauth_tokens, whoop_data, whoop_sync_jobs
```

### Environment Issues
```bash
# Verify .env file has:
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your_key
# WHOOP_CLIENT_ID=your_client_id
# SERVICE_API_KEY=dev-api-key-change-in-production
```

## 🎉 Next Steps

1. **Complete OAuth Flow**: Use real WHOOP credentials to authorize a test user
2. **Test Real Data**: After OAuth, test data endpoints with actual WHOOP data
3. **Integration Testing**: Connect with `hos-fapi-hm-sahha-main` for sequential calls
4. **Production Deployment**: Use testing suite to validate production environment

## 📞 Quick Test Commands Summary

```bash
# Health check
curl http://localhost:8001/health/ready

# OAuth config
curl http://localhost:8001/api/v1/whoop/auth/oauth-config

# Interactive testing
python tests/manual_testing_suite.py

# Automated testing
pytest tests/automated_test_suite.py -v

# Performance testing
python tests/performance_load_tests.py
```

Your WHOOP API is ready for comprehensive testing! 🚀