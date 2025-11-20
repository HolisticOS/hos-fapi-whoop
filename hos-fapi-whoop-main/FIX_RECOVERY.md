# Fix Recovery 404 Issue

## Problem
Recovery endpoint returns 404 because WHOOP API v2 uses different base URLs for different endpoints.

## Solution
Add this to your `.env` file:

```bash
# Use v1 base URL (works for all endpoints in WHOOP API v2)
WHOOP_API_BASE_URL=https://api.prod.whoop.com/developer/v1
```

## Why This Works
WHOOP API v2 actually still uses `/v1/` for most endpoints:
- Sleep: `https://api.prod.whoop.com/developer/v1/activity/sleep` ✅
- Workout: `https://api.prod.whoop.com/developer/v1/activity/workout` ✅
- Recovery: `https://api.prod.whoop.com/developer/v1/recovery` ✅
- Cycle: `https://api.prod.whoop.com/developer/v1/cycle` ✅

The "v2" refers to the API version (data structure), not the URL path.

## Steps to Fix

1. **Add to .env file**:
```bash
echo "WHOOP_API_BASE_URL=https://api.prod.whoop.com/developer/v1" >> .env
```

2. **Restart server**:
```bash
# Stop (Ctrl+C)
python start.py
```

3. **Test**:
```bash
python tests/interactive_test.py
```

## Expected Results After Fix

```
✅ Data sync completed!
  Recovery records: 7     ← Should now work!
  Sleep records: 7
  Workout records: varies (all workouts in 7 days)
  Cycle records: 7
```
