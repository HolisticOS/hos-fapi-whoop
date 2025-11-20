# Final Sync Fixes Summary

## Issues Fixed

### 1. ✅ Recovery Returns 404
**Problem**: Recovery endpoint was using `/v2/recovery` but WHOOP API v2 uses `/v1/recovery`

**Solution**: Changed default base URL from `/v2/` to `/v1/`

**Files Changed**:
- `app/config/settings.py:37` - Changed default to `https://api.prod.whoop.com/developer/v1`
- `.env.example:37` - Added clarifying comment

### 2. ✅ Get ALL Workouts in 7-Day Period (Not Just 7 Records)
**Problem**: Was fetching only 7 workout records, but users want ALL workouts within 7 days

**Solution**: Added pagination for workouts to fetch all records within date range

**Files Changed**:
- `app/services/whoop_service.py:755-767` - Added workout pagination loop

### 3. ✅ Cycle End Time NULL Error
**Problem**: In-progress cycles have `end_time: null` but database required NOT NULL

**Solution**: Created migration to allow NULL end_time for cycles

**Files Changed**:
- `migrations/004_fix_cycle_end_time_nullable.sql` - New migration file

### 4. ✅ Re-enabled Raw Data Storage
**Problem**: User wanted both parsed records AND raw JSON storage

**Solution**: Re-enabled raw data storage in whoop_raw_data table

**Files Changed**:
- `app/services/whoop_service.py` - Uncommented raw storage calls (lines 383-392, 500-509, 601-610, 882-891)

### 5. ✅ Fixed Data Limits
**Problem**: Was fetching hardcoded limits instead of respecting days_back parameter

**Solution**: Made limits dynamic based on days_back parameter

**Files Changed**:
- `app/services/whoop_service.py:751-753` - Use `days_back` for limit calculation

## Action Required

### Step 1: Run Migrations in Supabase
Run these migrations in order:

```sql
-- 1. Fix whoop_raw_data table schema (if needed)
-- Run: migrations/003b_recreate_whoop_raw_data.sql

-- 2. Fix cycle end_time to allow NULL
-- Run: migrations/004_fix_cycle_end_time_nullable.sql
```

### Step 2: Restart Server
```bash
# Stop server (Ctrl+C)
python start.py
```

### Step 3: Test Sync
```bash
python tests/interactive_test.py
# Enter 7 when asked for days
```

## Expected Results

### Individual Tables
```sql
SELECT COUNT(*) FROM whoop_sleep WHERE user_id = 'your-uuid';
-- Expected: 7 (one per day)

SELECT COUNT(*) FROM whoop_recovery WHERE user_id = 'your-uuid';
-- Expected: 7 (one per day) ← Should now work!

SELECT COUNT(*) FROM whoop_cycle WHERE user_id = 'your-uuid';
-- Expected: 7 (one per day, including in-progress cycles)

SELECT COUNT(*) FROM whoop_workout WHERE user_id = 'your-uuid';
-- Expected: varies (ALL workouts in 7 days, not limited to 7)
```

### Raw Data Table
```sql
SELECT
    data_type,
    record_count,
    fetched_at
FROM whoop_raw_data
WHERE user_id = 'your-uuid'
ORDER BY fetched_at DESC;

-- Expected: 4 rows (one per data type) with varying record_count
```

## Data Storage Structure

### Dual Storage System

You now have **both**:

#### 1. Parsed Individual Records
**Tables**: `whoop_sleep`, `whoop_workout`, `whoop_recovery`, `whoop_cycle`
- ✅ One row per record
- ✅ Parsed fields for easy querying
- ✅ Use for analytics and dashboards

Example:
```sql
SELECT
    end_time::date as sleep_date,
    sleep_performance_percentage,
    total_sleep_time_milli / 3600000.0 as hours
FROM whoop_sleep
WHERE user_id = 'your-uuid'
ORDER BY end_time DESC
LIMIT 7;
```

#### 2. Raw Bulk Data
**Table**: `whoop_raw_data`
- ✅ One row per API call
- ✅ Complete JSON in `records` field
- ✅ Use for backup/auditing

Example:
```sql
SELECT
    data_type,
    records,
    record_count,
    fetched_at
FROM whoop_raw_data
WHERE user_id = 'your-uuid'
  AND data_type = 'sleep'
ORDER BY fetched_at DESC
LIMIT 1;
```

## Sync Behavior Summary

Request **7 days** of data:

| Data Type | Fetched | Storage |
|-----------|---------|---------|
| Sleep | 7 most recent | `whoop_sleep` (7 rows) + `whoop_raw_data` (1 row with array of 7) |
| Recovery | 7 most recent | `whoop_recovery` (7 rows) + `whoop_raw_data` (1 row with array of 7) |
| Workout | **ALL in 7 days** | `whoop_workout` (varies) + `whoop_raw_data` (1+ rows with arrays) |
| Cycle | 7 most recent | `whoop_cycle` (7 rows, some may have NULL end_time) + `whoop_raw_data` (1 row) |

## Verification Queries

### Check Everything Synced Correctly
```sql
-- Summary of individual records
SELECT
    'sleep' as type, COUNT(*) as count FROM whoop_sleep WHERE user_id = 'your-uuid'
UNION ALL
SELECT 'recovery', COUNT(*) FROM whoop_recovery WHERE user_id = 'your-uuid'
UNION ALL
SELECT 'workout', COUNT(*) FROM whoop_workout WHERE user_id = 'your-uuid'
UNION ALL
SELECT 'cycle', COUNT(*) FROM whoop_cycle WHERE user_id = 'your-uuid';

-- Summary of raw data
SELECT
    data_type,
    COUNT(*) as api_calls,
    SUM(record_count) as total_records
FROM whoop_raw_data
WHERE user_id = 'your-uuid'
GROUP BY data_type;
```

### Check In-Progress Cycles
```sql
SELECT
    id,
    start_time,
    end_time,
    day_strain,
    CASE
        WHEN end_time IS NULL THEN 'In Progress'
        ELSE 'Completed'
    END as status
FROM whoop_cycle
WHERE user_id = 'your-uuid'
ORDER BY start_time DESC;
```

## Troubleshooting

### Still Getting Recovery 404?
- Check your base URL: `python -c "from app.config.settings import settings; print(settings.WHOOP_API_BASE_URL)"`
- Should show: `https://api.prod.whoop.com/developer/v1`
- Restart server after checking

### Not Getting ALL Workouts?
- Check pagination is working: Look for multiple API calls in logs
- Verify: `SELECT COUNT(*) FROM whoop_raw_data WHERE data_type = 'workout'` - may have multiple rows if > 25 workouts

### Cycle End Time Errors?
- Make sure you ran migration 004
- Verify: `SELECT is_nullable FROM information_schema.columns WHERE table_name = 'whoop_cycle' AND column_name = 'end_time'`
- Should return: `YES`

## API Endpoints Reference

All endpoints now use base URL: `https://api.prod.whoop.com/developer/v1`

| Endpoint | Full URL |
|----------|----------|
| Recovery | `https://api.prod.whoop.com/developer/v1/recovery` ✅ |
| Sleep | `https://api.prod.whoop.com/developer/v1/activity/sleep` ✅ |
| Workout | `https://api.prod.whoop.com/developer/v1/activity/workout` ✅ |
| Cycle | `https://api.prod.whoop.com/developer/v1/cycle` ✅ |

## Files Modified

1. `app/config/settings.py` - Changed default base URL to v1
2. `app/services/whoop_service.py` - Fixed limits, added workout pagination, re-enabled raw storage
3. `.env.example` - Added comment about v1 base URL
4. `migrations/004_fix_cycle_end_time_nullable.sql` - New migration
5. `migrations/003b_recreate_whoop_raw_data.sql` - Created earlier for raw data table

## Success Indicators

✅ Recovery data syncs successfully (no more 404)
✅ All workouts within 7 days are fetched (not limited to 7)
✅ Cycles with NULL end_time are stored (in-progress cycles)
✅ Both individual records AND raw JSON are stored
✅ Limits respect the days_back parameter

Test output should show:
```
✅ Data sync completed!
  Recovery records: 7     ← Fixed!
  Sleep records: 7
  Workout records: X      ← All workouts in 7 days
  Cycle records: 7
  Total stored: 21+ records
```
