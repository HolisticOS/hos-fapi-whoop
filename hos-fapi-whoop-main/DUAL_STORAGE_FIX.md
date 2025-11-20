# Dual Storage Fix - Raw Data + Individual Tables

## What Was Fixed

### Issue 1: Duplicate Raw Data Entries
**Problem**: Workouts had 2 entries with 25 records each in `whoop_raw_data`

**Root Cause**: Raw data was being stored inside `get_workout_data()`, so when we paginated to get all workouts, each API call created a separate raw_data entry.

**Solution**: Moved raw data storage from individual methods to `get_comprehensive_data()` after all pagination is complete.

**Result**: Now you get ONE entry per data type in `whoop_raw_data` with ALL records for that type.

### Issue 2: Too Many Workout Records
**Problem**: Workout pagination was fetching all historical workouts (151 records) instead of limiting to requested timeframe

**Root Cause**: Complex date-filtering pagination logic was fetching ALL workouts without proper limits.

**Solution**: Simplified to fetch max 25 workout records total per sync (user requirement).

**Result**: Workouts now limited to 25 records max, matching user requirements.

### Issue 3: Recovery Data Not Storing
**Problem**: Recovery data not updating in either `whoop_raw_data` or `whoop_recovery` tables

**Root Cause**: ⚠️ **UPDATE**: API IS returning data (6 recovery records), but storage is failing

**Status**: Investigating - likely issue with `raw_data` field not being populated in `WhoopRecoveryData` models

**Next Steps**:
- Added detailed logging to check if `raw_data` field is populated
- Logs will show: `has_raw_data`, `raw_data_type`, `raw_data_empty` for each record
- Likely need to fix how we populate `raw_data` when creating `WhoopRecoveryData` models

### Issue 4: Individual Tables Not Populating (Sleep/Workout)
**Problem**: Only `whoop_raw_data` and `whoop_cycle` tables were being updated, not `whoop_sleep`, `whoop_workout`

**Root Cause**: Unknown - needs debugging with new logging

**Solution**: Added detailed logging to track what's happening:
- Logs when storing to individual tables
- Logs when skipping storage
- Shows counts of records being stored
- Shows raw_data extraction process

## Current Storage Flow

### 1. Fetch Data (`get_comprehensive_data`)
```
GET /v2/activity/sleep (up to 7 records for 7 days)
GET /v2/activity/workout (max 25 records, no pagination)
GET /v2/recovery (⚠️ Currently returns 404 - needs investigation)
```

### 2. Store Raw Data (`whoop_raw_data` table)
```
One row per data type with complete array:
- sleep: [up to 7 sleep JSON objects]
- workout: [up to 25 workout JSON objects]
- recovery: [EMPTY - API returns 404] ⚠️
```

**Note**: Recovery will not be stored in raw_data until the 404 issue is resolved.

### 3. Store Individual Records (parsed tables)
```
whoop_sleep: up to 7 rows (one per sleep session) - ⚠️ Currently not populating (investigating)
whoop_workout: up to 25 rows (limited to max 25) - ⚠️ Currently not populating (investigating)
whoop_recovery: 0 rows (API returns 404) - ⚠️ KNOWN ISSUE
whoop_cycle: up to 7 rows (fetched separately) - ✅ Working
```

**Status**: Only `whoop_cycle` and `whoop_raw_data` tables are currently being populated. Sleep and workout individual tables need debugging with new logs.

## Files Modified

1. **app/services/whoop_service.py**
   - Lines 383-385: Removed raw storage from `get_sleep_data()`
   - Lines 491-493: Removed raw storage from `get_workout_data()`
   - Lines 587-589: Removed raw storage from `get_recovery_data()`
   - Lines 873-875: Removed raw storage from `get_cycle_data()`
   - Lines 728-733: **SIMPLIFIED workout pagination** - removed complex date filtering, now just fetches max 25 records
   - Lines 794-832: Added consolidated raw storage in `get_comprehensive_data()` with detailed logging
   - Lines 551-556: Added logging for recovery 404 errors
   - Lines 558-561: Added logging for recovery API response processing

2. **app/api/internal.py**
   - Lines 369-406: Added detailed logging for storage operations (sleep, workout, recovery)
   - Shows when storing records and when skipping storage with reasons

3. **DUAL_STORAGE_FIX.md**
   - Updated to document all issues and their status
   - Added recovery 404 issue as known limitation
   - Updated workout pagination behavior (max 25 records)

## How to Test

### 1. Restart Server
```bash
python start.py
```

### 2. Watch Logs Carefully
Look for these log messages:

**Workout Limit Check**:
```
✅ Comprehensive v2 data fetch completed
  workout_count=25  ← Should be MAX 25 (not 151)
```

**Recovery 404 Issue**:
```
⚠️ No recovery response data from API
  endpoint="recovery"
  note="May need to fetch recovery through /v2/cycle endpoint instead"
```

**Raw Data Storage**:
```
💾 Storing sleep raw data to whoop_raw_data table
  count=7

💾 Storing workout raw data to whoop_raw_data table
  count=25  ← Should be MAX 25

⚠️ No recovery data to store in raw_data table  ← EXPECTED DUE TO 404
```

**Individual Table Storage** (from internal.py):
```
💾 Storing X sleep records to whoop_sleep table
✅ Stored X sleep records

💾 Storing X workout records to whoop_workout table
✅ Stored X workout records

⚠️ Skipping recovery storage
  in_sync_types=True
  has_data=False  ← EXPECTED - API returns 404
```

### 3. Run Test
```bash
python tests/interactive_test.py
# Enter 7 when asked for days
```

### 4. Verify in Database

**Individual Tables:**
```sql
-- Check actual counts
SELECT COUNT(*) FROM whoop_sleep WHERE user_id = 'your-uuid';      -- ⚠️ Currently 0 (investigating)
SELECT COUNT(*) FROM whoop_workout WHERE user_id = 'your-uuid';    -- ⚠️ Currently 0 (investigating)
SELECT COUNT(*) FROM whoop_recovery WHERE user_id = 'your-uuid';   -- ❌ Will be 0 (API 404)
SELECT COUNT(*) FROM whoop_cycle WHERE user_id = 'your-uuid';      -- ✅ Should be ~7

-- View actual records
SELECT end_time::date, sleep_performance_percentage
FROM whoop_sleep
WHERE user_id = 'your-uuid'
ORDER BY end_time DESC
LIMIT 7;
```

**Raw Data Table:**
```sql
-- Should have ONE entry per data type (not duplicates)
SELECT
    data_type,
    record_count,
    fetched_at
FROM whoop_raw_data
WHERE user_id = 'your-uuid'
ORDER BY fetched_at DESC;

-- Expected result (UPDATED):
-- sleep    | 7     | 2025-11-20 ... ✅
-- workout  | 25    | 2025-11-20 ... ✅ (max 25, not 151)
-- recovery | NONE  | -              ❌ (API 404 - won't appear)
```

**Note**: If you see duplicate entries for workout (e.g., 2 rows with 25 each), delete old data and re-sync.

## Expected Behavior

### Dual Storage System (UPDATED)

**Scenario**: Sync 7 days

**whoop_raw_data table:**
```
id    | data_type | record_count | records
------|-----------|--------------|--------
uuid1 | sleep     | 7            | [7 complete JSON objects] ✅
uuid2 | workout   | 25 (max)     | [25 complete JSON objects] ✅
(no recovery row - API 404) ❌
```

**whoop_sleep table:**
```
⚠️ Currently 0 rows (investigating with new logs)
Expected: 7 individual rows with parsed fields:
- id, user_id, start_time, end_time
- sleep_performance_percentage
- total_sleep_time_milli
- rem_sleep_milli, light_sleep_milli, slow_wave_sleep_milli
- etc.
```

**whoop_workout table:**
```
⚠️ Currently 0 rows (investigating with new logs)
Expected: up to 25 individual rows with parsed fields:
- id, user_id, start_time, end_time
- strain_score
- average_heart_rate, max_heart_rate
- calories_burned
- sport_name
- etc.
```

**whoop_recovery table:**
```
❌ Will be 0 rows (API returns 404)
Needs alternative implementation via /v2/cycle endpoint
```

## Troubleshooting

### Recovery Data Not Storing (KNOWN ISSUE)

**Symptom**: No recovery data in `whoop_raw_data` or `whoop_recovery` tables

**Logs to Look For**:
```
⚠️ No recovery response data from API
  endpoint="recovery"
  note="May need to fetch recovery through /v2/cycle endpoint instead"
```

**Root Cause**: WHOOP v2 API's `/v2/recovery` endpoint returns 404

**Solution**: This is a known limitation. Recovery data may need to be fetched through `/v2/cycle/{cycle_id}` endpoint. This requires code changes to:
1. Fetch cycle data first
2. For each cycle, fetch associated recovery data
3. Alternative: Check if WHOOP API documentation provides a different recovery endpoint

### If Individual Tables Are Still Empty (Sleep/Workout)

**Symptom**: `whoop_sleep` and `whoop_workout` tables are empty, but `whoop_raw_data` has data

**Logs to Look For**:
```
⚠️ Skipping sleep storage
  in_sync_types=True
  has_data=False  ← This means data_response.sleep_data is empty!
```

If `has_data=False`, check earlier logs:
```
✅ Comprehensive v2 data fetch completed
  sleep_count=7  ← If this is > 0 but individual table is empty, there's a data flow issue
  workout_count=25
```

**Debug Steps**:
1. Check if `data_response.sleep_data` contains models with `raw_data` field
2. Verify the line `sleep_records = [s.raw_data for s in data_response.sleep_data if hasattr(s, 'raw_data')]` is extracting data correctly
3. Check repository method `store_sleep_records()` for errors

### If Raw Data Has Duplicates

This should be fixed now, but if you still see duplicates:
1. Clear old data: `DELETE FROM whoop_raw_data WHERE user_id = 'your-uuid';`
2. Restart server
3. Sync again

### Workout Count Limit

**UPDATED BEHAVIOR**: Workouts are now limited to max 25 records per sync (user requirement)

Check logs for:
```
✅ Comprehensive v2 data fetch completed
  sleep_count=7
  workout_count=25  ← MAX 25 (not 151 like before!)
  recovery_count=0  ← Will be 0 due to API 404
```

If you see `workout_count=151` or any number > 25, the fix wasn't applied correctly. Should be MAX 25.

## Next Steps

### 1. Test the Fixes

**What's Fixed**:
- ✅ Workout limit is now MAX 25 records (not 151)
- ✅ Duplicate raw_data entries fixed (consolidated storage)
- ✅ Added comprehensive logging for debugging

**What's Still Broken**:
- ⚠️ Individual tables (`whoop_sleep`, `whoop_workout`) not populating - needs log analysis
- ❌ Recovery data returns 404 from API - needs alternative implementation

**Action Required**:
1. **Restart server**: `python start.py`
2. **Run sync test**: `python tests/interactive_test.py` (enter 7 days)
3. **Watch logs carefully** - Look for the log messages documented above
4. **Share log output** - Especially:
   - The "✅ Comprehensive v2 data fetch completed" message (workout_count should be ≤25)
   - Any "⚠️ Skipping" messages for sleep/workout storage
   - The "💾 Storing" messages for raw_data
5. **Check database**:
   - `whoop_raw_data` should have 2 entries (sleep, workout) - NO recovery
   - `whoop_cycle` should have ~7 entries
   - `whoop_sleep`, `whoop_workout` will likely be empty (investigating)

### 2. Recovery API Investigation

The recovery endpoint returns 404. Next steps:
1. Check WHOOP API v2 documentation for correct recovery endpoint
2. Consider implementing recovery fetch through `/v2/cycle/{cycle_id}` endpoint
3. Alternative: Check if recovery data is included in cycle response

### 3. Debug Individual Table Population

If logs show `has_data=False` for sleep/workout:
1. The issue is data flow between `get_comprehensive_data()` and `internal.py`
2. Check if `WhoopSleepData` and `WhoopWorkoutData` models have `raw_data` populated
3. May need to add more logging to show the actual model structure

**The detailed logs will tell us exactly what's happening and where the data flow breaks!**
