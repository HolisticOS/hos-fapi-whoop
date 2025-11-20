# Data Sync Fix Summary

## Problem
You were seeing:
- **11 bulk entries** in `whoop_raw_data` table, each with `record_count: 25`
- Each entry contained an **array of 25 individual sleep records**
- You wanted **only 7 individual sleep records** (one per day)

## Root Causes
1. **Bulk raw storage** was enabled, storing entire API responses as single rows
2. **Hardcoded limit=10** in `get_comprehensive_data()` method
3. **include_all_pages=True** was fetching unlimited paginated data
4. Individual record storage was working, but you were looking at the wrong table

## Changes Made

### 1. Fixed Limit to Use days_back Parameter
**File**: `app/services/whoop_service.py:748-753`

**Before**:
```python
# Hardcoded limit
sleep_collection = await self.get_sleep_data(user_id, start_iso, end_iso, limit=10)
workout_collection = await self.get_workout_data(user_id, start_iso, end_iso, limit=10)
recovery_collection = await self.get_recovery_data(user_id, start_iso, end_iso, limit=10)
```

**After**:
```python
# Dynamic limit based on days requested
limit = min(days_back, 25)  # WHOOP API max is 25
sleep_collection = await self.get_sleep_data(user_id, start_iso, end_iso, limit=limit)
workout_collection = await self.get_workout_data(user_id, start_iso, end_iso, limit=limit * 3)
recovery_collection = await self.get_recovery_data(user_id, start_iso, end_iso, limit=limit)
```

**Impact**:
- Request 7 days → Get 7 sleep records, 7 recovery records, 21 workout records
- Request 10 days → Get 10 sleep records, 10 recovery records, 30 workout records

### 2. Disabled All-Pages Pagination
**File**: `app/api/internal.py:356-359`

**Before**:
```python
data_response = await whoop_client.get_comprehensive_data(
    user_id=str(user_uuid),
    days_back=days_back,
    include_all_pages=True  # Get ALL paginated data
)
```

**After**:
```python
data_response = await whoop_client.get_comprehensive_data(
    user_id=str(user_uuid),
    days_back=days_back,
    include_all_pages=False  # Respect the limit
)
```

**Impact**: Fetches only the requested number of records, not all historical data

### 3. Disabled Bulk Raw Data Storage
**File**: `app/services/whoop_service.py`

Disabled raw storage calls in:
- `get_sleep_data()` - Line 383-392 (commented out)
- `get_workout_data()` - Line 500-509 (commented out)
- `get_recovery_data()` - Line 601-610 (commented out)
- `get_cycle_data()` - Line 882-891 (commented out)

**Impact**: No more bulk entries in `whoop_raw_data` table

### 4. Fixed Repository UPSERT
**File**: `app/repositories/whoop_data_repository.py:64-67`

**Before**:
```python
self.db.table('whoop_sync_log').upsert(data).execute()
```

**After**:
```python
self.db.table('whoop_sync_log').upsert(
    data,
    on_conflict='user_id,data_type'
).execute()
```

**Impact**: No more duplicate key errors in sync log

## Database Storage Structure

### Individual Record Tables (WHAT YOU WANT)
These store **one row per record**:

| Table | Description | Example |
|-------|-------------|---------|
| `whoop_sleep` | One row per sleep session | 7 rows for 7 days |
| `whoop_workout` | One row per workout | Variable (multiple per day) |
| `whoop_recovery` | One row per recovery | 7 rows for 7 days |
| `whoop_cycle` | One row per cycle | 7 rows for 7 days |

### Sample `whoop_sleep` Record
```sql
SELECT
    id,
    start_time,
    end_time,
    sleep_performance_percentage,
    total_sleep_time_milli
FROM whoop_sleep
WHERE user_id = 'your-uuid'
ORDER BY end_time DESC
LIMIT 7;
```

### Bulk Raw Data Table (NOW DISABLED)
`whoop_raw_data` stored entire API responses:
- One row per API call
- Each row contained an array of 25 records
- This is now **disabled** - you won't see new entries here

## How to Test

### 1. Restart Server
```bash
# Stop server (Ctrl+C)
python start.py
```

### 2. Run Test Script
```bash
python tests/interactive_test.py
```

### 3. When Prompted for Days
```
How many days of data to sync?
Days (1-30, default 7): 7    # Enter 7
```

### 4. Expected Result
```
✅ Data sync completed!
  Recovery records: 7
  Sleep records: 7
  Workout records: 21 (or fewer depending on your activity)
  Cycle records: 7
  Total stored: 42
```

### 5. Verify in Database
```sql
-- Check individual sleep records
SELECT COUNT(*) FROM whoop_sleep WHERE user_id = 'your-uuid';
-- Should return 7 (or up to 7 if some days have no data)

-- View sleep records
SELECT
    end_time::date as sleep_date,
    sleep_performance_percentage,
    total_sleep_time_milli / 3600000.0 as hours_slept
FROM whoop_sleep
WHERE user_id = 'your-uuid'
ORDER BY end_time DESC
LIMIT 7;

-- Check that whoop_raw_data is empty (no new entries)
SELECT COUNT(*) FROM whoop_raw_data WHERE user_id = 'your-uuid';
-- Should be 0 or same count as before (no new entries)
```

## Understanding the Data

### One Sleep Record Per Day
Each row in `whoop_sleep` represents **one sleep session** with all its details:

```json
{
  "id": "adf6f156-8b61-4023-9369-8ab291e3a231",
  "user_id": "your-uuid",
  "start_time": "2025-11-09T05:36:48.792Z",
  "end_time": "2025-11-09T14:26:53.147Z",
  "sleep_performance_percentage": 77.00,
  "sleep_efficiency_percentage": 89.80,
  "total_sleep_time_milli": 31804355,
  "rem_sleep_milli": 7329448,
  "light_sleep_milli": 13151793,
  "slow_wave_sleep_milli": 8079807,
  "cycle_id": "1146779781",
  "raw_data": { /* complete JSON for reference */ }
}
```

### Fetching Your Data via API
```bash
# Get last 7 days of sleep data
curl -X GET "http://localhost:8001/api/v1/data/sleep?days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get last 7 days of recovery data
curl -X GET "http://localhost:8001/api/v1/data/recovery?days=7" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Next Steps

### If You Want to Adjust Limits

**For Sleep/Recovery** (typically 1 per day):
- Edit `app/services/whoop_service.py:751,753`
- Change `limit=limit` to your desired value

**For Workouts** (multiple per day):
- Edit `app/services/whoop_service.py:752`
- Change `limit=limit * 3` to your desired multiplier

### If You Want to Re-enable Raw Storage

Uncomment the storage calls in:
- `app/services/whoop_service.py` lines 383-392, 500-509, 601-610, 882-891

### If You Want to Clean Up Old Raw Data

```sql
-- Delete all entries from whoop_raw_data
DELETE FROM whoop_raw_data WHERE user_id = 'your-uuid';
```

## Troubleshooting

### Still seeing bulk entries?
- Make sure you restarted the server after making changes
- Check that you're querying `whoop_sleep` table, not `whoop_raw_data`

### Not getting 7 records?
- WHOOP only returns data for days where you actually wore the device
- Check the date range in your test: some days may have no sleep data

### Getting duplicate key errors?
- Make sure you ran migration 003 to fix the repository UPSERT
- Check that `migrations/003_fix_data_types.sql` was applied

## Files Modified

1. `app/services/whoop_service.py` - Fixed limits and disabled raw storage
2. `app/api/internal.py` - Disabled include_all_pages
3. `app/repositories/whoop_data_repository.py` - Fixed UPSERT conflict resolution
4. `tests/interactive_test.py` - Added clarifying message
5. `migrations/003b_recreate_whoop_raw_data.sql` - Fixed table schema (if needed)
