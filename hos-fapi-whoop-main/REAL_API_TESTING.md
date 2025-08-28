# 🔴 Real WHOOP API Testing (No Mocking)

## The Difference

**❌ Mocked Testing**: Uses fake data, doesn't hit real WHOOP API
**✅ Real API Testing**: Makes actual calls to WHOOP's servers with real credentials

## Prerequisites for Real Testing

1. **Real WHOOP Developer Account**:
   - Go to [WHOOP Developer Portal](https://developer.whoop.com/)
   - Create an application
   - Get your `CLIENT_ID` and `CLIENT_SECRET`

2. **Real WHOOP User Account**:
   - You need a WHOOP account with data (recovery, sleep, workouts)
   - Or a test WHOOP account provided by WHOOP

3. **Your Environment Variables** (`.env` file):
   ```env
   WHOOP_CLIENT_ID=your_real_client_id_here
   WHOOP_CLIENT_SECRET=your_real_client_secret_here
   WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback
   SUPABASE_URL=your_real_supabase_url
   SUPABASE_KEY=your_real_supabase_key
   SERVICE_API_KEY=your_secure_api_key
   ```

## 🎯 Real API Testing Steps

### Step 1: Test Your API is Working
```bash
# Make sure your WHOOP API is running
python -m app.main

# In another terminal, test basic connectivity
curl http://localhost:8001/health/ready
```

### Step 2: Real OAuth Flow (Browser Required)

**Start the OAuth flow:**
```bash
curl -X POST "http://localhost:8001/api/v1/whoop/auth/authorize" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "my_real_test_user",
    "redirect_uri": "http://localhost:8001/api/v1/whoop/auth/callback",
    "scopes": ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"]
  }'
```

**Response will give you a real WHOOP authorization URL:**
```json
{
  "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth?client_id=YOUR_REAL_CLIENT_ID&...",
  "state": "some_generated_state"
}
```

**Complete the authorization:**
1. Copy the `authorization_url`
2. Open it in your browser
3. **Log in with your real WHOOP account**
4. Click "Authorize" to grant permission
5. WHOOP redirects back to your API with a real authorization code
6. Your API exchanges the code for a real access token

### Step 3: Verify Real Token Storage

```bash
curl -X GET "http://localhost:8001/api/v1/auth/status/my_real_test_user" \
  -H "X-API-Key: your_secure_api_key"
```

**Real response (after successful OAuth):**
```json
{
  "user_id": "my_real_test_user",
  "connection_status": {
    "connected": true,
    "status": "active",
    "token_expires_at": "2024-12-28T10:30:00Z",
    "scopes": ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"],
    "last_sync": null
  }
}
```

### Step 4: Fetch Real WHOOP Data

**Get your actual recovery data:**
```bash
curl -X GET "http://localhost:8001/api/v1/data/recovery/my_real_test_user?days=7" \
  -H "X-API-Key: your_secure_api_key"
```

**Real response with your actual WHOOP data:**
```json
{
  "user_id": "my_real_test_user",
  "data_type": "recovery",
  "records": [
    {
      "date": "2024-08-28",
      "recovery_score": 72,        // Your actual recovery score
      "hrv_rmssd": 45.3,          // Your actual HRV
      "resting_heart_rate": 52,    // Your actual RHR
      "skin_temp_celsius": 33.9,   // Your actual skin temp
      "respiratory_rate": 14.8     // Your actual respiratory rate
    },
    {
      "date": "2024-08-27",
      "recovery_score": 68,
      "hrv_rmssd": 41.2,
      "resting_heart_rate": 54,
      "skin_temp_celsius": 34.1,
      "respiratory_rate": 15.2
    }
  ],
  "total_records": 7,
  "sync_timestamp": "2024-08-28T14:30:00Z"
}
```

**Get your actual sleep data:**
```bash
curl -X GET "http://localhost:8001/api/v1/data/sleep/my_real_test_user?days=3" \
  -H "X-API-Key: your_secure_api_key"
```

**Real response with your actual sleep:**
```json
{
  "user_id": "my_real_test_user",
  "data_type": "sleep",
  "records": [
    {
      "date": "2024-08-28",
      "sleep_score": 84,               // Your actual sleep score
      "duration_minutes": 456,         // Your actual sleep duration
      "efficiency_percentage": 87.2,   // Your actual sleep efficiency
      "deep_sleep_minutes": 98,        // Your actual deep sleep
      "rem_sleep_minutes": 87,         // Your actual REM sleep
      "light_sleep_minutes": 271,      // Your actual light sleep
      "awake_minutes": 23              // Your actual time awake
    }
  ]
}
```

## 🧪 Real API Testing Script

Create this simple script to test with real data:

```python
# real_api_test.py
import requests
import json
import time

# Your API base URL
BASE_URL = "http://localhost:8001"
API_KEY = "your_secure_api_key"  # From your .env file
USER_ID = "my_real_test_user"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_real_whoop_api():
    print("🔴 Testing with REAL WHOOP API (no mocking)")
    
    # 1. Test health
    print("\n1. Testing API health...")
    response = requests.get(f"{BASE_URL}/health/ready")
    print(f"Health: {response.status_code} - {response.json()}")
    
    # 2. Check if user is connected
    print(f"\n2. Checking auth status for {USER_ID}...")
    response = requests.get(f"{BASE_URL}/api/v1/auth/status/{USER_ID}", headers=headers)
    auth_status = response.json()
    print(f"Auth Status: {json.dumps(auth_status, indent=2)}")
    
    if not auth_status.get("connection_status", {}).get("connected"):
        print("❌ User not connected. Run OAuth flow first!")
        return
    
    # 3. Get real recovery data
    print(f"\n3. Fetching REAL recovery data for {USER_ID}...")
    response = requests.get(f"{BASE_URL}/api/v1/data/recovery/{USER_ID}?days=7", headers=headers)
    
    if response.status_code == 200:
        recovery_data = response.json()
        print(f"✅ Real Recovery Data Retrieved:")
        for record in recovery_data.get("records", [])[:2]:  # Show first 2 days
            print(f"  Date: {record['date']}")
            print(f"  Recovery Score: {record['recovery_score']}")
            print(f"  HRV: {record['hrv_rmssd']} ms")
            print(f"  RHR: {record['resting_heart_rate']} bpm")
            print()
    else:
        print(f"❌ Failed to get recovery data: {response.status_code}")
        print(response.text)
    
    # 4. Get real sleep data  
    print(f"\n4. Fetching REAL sleep data for {USER_ID}...")
    response = requests.get(f"{BASE_URL}/api/v1/data/sleep/{USER_ID}?days=3", headers=headers)
    
    if response.status_code == 200:
        sleep_data = response.json()
        print(f"✅ Real Sleep Data Retrieved:")
        for record in sleep_data.get("records", [])[:1]:  # Show first day
            print(f"  Date: {record['date']}")
            print(f"  Sleep Score: {record['sleep_score']}")
            print(f"  Duration: {record['duration_minutes']} minutes")
            print(f"  Efficiency: {record['efficiency_percentage']}%")
            print()
    else:
        print(f"❌ Failed to get sleep data: {response.status_code}")
    
    # 5. Test rate limiting with real API
    print(f"\n5. Testing REAL rate limiting...")
    response = requests.get(f"{BASE_URL}/api/v1/client-status", headers=headers)
    if response.status_code == 200:
        status = response.json()
        rate_info = status.get("whoop_client", {}).get("rate_limiting", {})
        print(f"✅ Rate Limiting Status:")
        print(f"  Minute Limit: {rate_info.get('minute_limit')}")
        print(f"  Daily Limit: {rate_info.get('daily_limit')}")
        print(f"  Current Usage: Check your WHOOP developer dashboard")

if __name__ == "__main__":
    test_real_whoop_api()
```

**Run the real API test:**
```bash
python real_api_test.py
```

## 🔄 Complete Real Data Workflow

### 1. First Time Setup (Do Once)
```bash
# Start your API
python -m app.main

# Run OAuth flow (opens browser)
curl -X POST "http://localhost:8001/api/v1/whoop/auth/authorize" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "my_real_user", "redirect_uri": "http://localhost:8001/api/v1/whoop/auth/callback", "scopes": ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"]}'

# Copy authorization_url and open in browser
# Complete WHOOP login and authorization
```

### 2. Daily Testing (Real Data)
```bash
# Test with real current data
curl -X GET "http://localhost:8001/api/v1/data/recovery/my_real_user?days=1" \
  -H "X-API-Key: your_key"

curl -X GET "http://localhost:8001/api/v1/data/sleep/my_real_user?days=1" \
  -H "X-API-Key: your_key"

curl -X GET "http://localhost:8001/api/v1/data/workouts/my_real_user?days=7" \
  -H "X-API-Key: your_key"
```

## ❌ What NOT to Use (Mocked Testing)

Don't use these for real API testing:
- `pytest` with mocked responses
- Test files with fake data
- Simulated OAuth flows
- Mock WHOOP API responses

## ✅ Real API Testing Checklist

- [ ] Real WHOOP developer credentials configured
- [ ] Real WHOOP user account with data
- [ ] OAuth flow completed in browser
- [ ] Real access tokens stored in database
- [ ] API calls return actual WHOOP data
- [ ] Rate limiting tested against real WHOOP limits
- [ ] Error handling tested with real API errors

## 🚨 Important Notes

1. **Rate Limits**: WHOOP enforces real rate limits (100/min, 10K/day)
2. **Data Availability**: You'll only get data if your WHOOP account has recent activity
3. **Token Expiry**: Real tokens expire and need refresh
4. **Cost**: Some WHOOP API calls may have usage costs
5. **Approval**: Your WHOOP app may need approval for production use

This is **real API testing** - you're making actual calls to WHOOP's production servers with real credentials and getting real data back! 🎯