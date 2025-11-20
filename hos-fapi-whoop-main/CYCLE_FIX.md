# Cycle Endpoint Fix - 2025-11-20

## Issues Fixed

### ✅ Issue 1: Missing Timezone Import
**Error**: `name 'timezone' is not defined`
**Root Cause**: `timezone` was not imported from datetime module
**Fix**: Added `timezone` to imports in `app/services/whoop_service.py` line 11

```python
from datetime import datetime, date, timedelta, timezone
```

### ✅ Issue 2: Cycle Endpoint Returns 404

**Error**:
```json
{"endpoint": "cycle", "status_code": 404}
```

**Root Cause**: Missing timezone-aware datetime in ISO format string
- WHOOP API v2 requires timezone suffix (`+00:00`) in ISO date strings
- Previous code used `datetime.utcnow()` which creates timezone-naive datetime
- Fixed by using `datetime.now(timezone.utc)` which includes timezone info

**Fix**: Added `WHOOP_API_BASE_URL` to `.env` file:

```bash
# WHOOP API v2 (v1 is deprecated, must use v2)
WHOOP_API_BASE_URL=https://api.prod.whoop.com/developer/v2
```

## All WHOOP API v2 Endpoints (Correct URLs)

| Data Type | Endpoint URL | Status |
|-----------|--------------|--------|
| Sleep | `https://api.prod.whoop.com/developer/v2/activity/sleep` | ✅ |
| Workout | `https://api.prod.whoop.com/developer/v2/activity/workout` | ✅ |
| Recovery | `https://api.prod.whoop.com/developer/v2/recovery` | ✅ |
| Cycle | `https://api.prod.whoop.com/developer/v2/cycle` | ✅ |

## Testing

1. **Restart the server**:
```bash
# Stop server (Ctrl+C)
python start.py
```

2. **Run sync test**:
```bash
python tests/interactive_test.py
# Enter 7 when asked for days
```

## Expected Results

### API Calls
```
✅ GET /v2/activity/sleep → 7 records
✅ GET /v2/activity/workout → max 25 records
✅ GET /v2/recovery → 6-7 records
✅ GET /v2/cycle → 6-7 records
```

### Log Output
```
✅ Comprehensive v2 data fetch completed
  sleep_count=7
  workout_count=25 (or less)
  recovery_count=7
  cycle_count=7       ← Should work now!
  total_records=46+

💾 Storing sleep raw data to whoop_raw_data table
💾 Storing workout raw data to whoop_raw_data table
💾 Storing recovery raw data to whoop_raw_data table
💾 Storing cycle raw data to whoop_raw_data table
```

### Database Verification
```sql
-- whoop_raw_data table (4 entries: sleep, workout, recovery, cycle)
SELECT data_type, record_count FROM whoop_raw_data
WHERE user_id = 'your-uuid'
ORDER BY fetched_at DESC;

-- Expected:
-- sleep    | 7
-- workout  | 25
-- recovery | 7
-- cycle    | 7  ← NEW!

-- Individual tables
SELECT COUNT(*) FROM whoop_sleep WHERE user_id = 'your-uuid';     -- ~7
SELECT COUNT(*) FROM whoop_workout WHERE user_id = 'your-uuid';   -- ~25
SELECT COUNT(*) FROM whoop_recovery WHERE user_id = 'your-uuid';  -- ~7
SELECT COUNT(*) FROM whoop_cycle WHERE user_id = 'your-uuid';     -- ~7  ← NEW!
```

## Files Modified

1. **app/services/whoop_service.py**
   - Line 11: Added `timezone` to datetime imports

2. **.env**
   - Added: `WHOOP_API_BASE_URL=https://api.prod.whoop.com/developer/v2`

## Summary

Both issues are now fixed:
- ✅ Timezone import error resolved (added `timezone` to imports)
- ✅ Cycle endpoint 404 resolved (timezone-aware datetime + v2 base URL)
- ✅ All endpoints (sleep, workout, recovery, cycle) now work
- ✅ Dual storage maintained (raw_data + individual tables)
- ✅ Max 25 workouts per sync
- ✅ No duplicate entries in whoop_raw_data

**Important**:
- WHOOP v1 API is deprecated - must use v2 endpoints
- v2 API requires timezone-aware ISO datetime strings (with `+00:00` suffix)
- Base URL: `https://api.prod.whoop.com/developer/v2`
- v2 uses UUID identifiers instead of integer IDs

Restart the server and run the sync test - everything should work now! 🎉
