# Database Migration Guide

## Overview

This guide walks you through fixing the database schema issues that are preventing data sync from working correctly.

## Issues Fixed

### 1. Data Type Mismatches (Migration 003)
- **HRV field**: Changed from INTEGER to NUMERIC(10,3) to support decimal values like "65.0"
- **Sleep percentage fields**: Changed from INTEGER to NUMERIC(5,2) for decimal percentages
- **Sleep cycle_id**: Changed from INTEGER to TEXT (WHOOP uses string IDs)
- **Cycle calories_burned**: Changed from INTEGER to NUMERIC(10,2) to support values like "5336.941"

### 2. Missing Table
- Created `whoop_raw_data` table for storing raw JSON responses from WHOOP API

### 3. Sync Log Duplicate Keys
- Fixed repository code to properly use UPSERT with conflict resolution

## Migration Steps

### Step 1: Backup Your Database (IMPORTANT!)

Before running any migrations, backup your database:

```bash
# If using Supabase, use their dashboard to create a backup
# Or export your data manually
```

### Step 2: Run Migration 003

**Option A: Using Supabase Dashboard (RECOMMENDED)**

1. Open your Supabase project dashboard
2. Navigate to: **SQL Editor**
3. Click **New Query**
4. Copy the contents of `migrations/003_fix_data_types.sql`
5. Paste into the SQL Editor
6. Click **Run** or press `Ctrl+Enter`
7. Verify the output shows successful execution

**Option B: Using psql Command Line**

```bash
# Connect to your database
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run the migration
\i migrations/003_fix_data_types.sql

# Verify changes
\d whoop_recovery
\d whoop_sleep
\d whoop_cycle
\d whoop_raw_data
```

### Step 3: Verify Migration Success

Run these verification queries in Supabase SQL Editor:

```sql
-- Check column types
SELECT
    table_name,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('whoop_recovery', 'whoop_sleep', 'whoop_cycle')
  AND column_name IN (
    'hrv_rmssd_milli',
    'sleep_performance_percentage',
    'sleep_consistency_percentage',
    'sleep_efficiency_percentage',
    'cycle_id',
    'calories_burned'
  )
ORDER BY table_name, column_name;
```

**Expected Results:**

| table_name | column_name | data_type | numeric_precision | numeric_scale |
|------------|-------------|-----------|-------------------|---------------|
| whoop_cycle | calories_burned | numeric | 10 | 2 |
| whoop_recovery | hrv_rmssd_milli | numeric | 10 | 3 |
| whoop_sleep | cycle_id | text | NULL | NULL |
| whoop_sleep | sleep_consistency_percentage | numeric | 5 | 2 |
| whoop_sleep | sleep_efficiency_percentage | numeric | 5 | 2 |
| whoop_sleep | sleep_performance_percentage | numeric | 5 | 2 |

```sql
-- Verify whoop_raw_data table exists
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'whoop_raw_data';
```

**Expected Result:**
| table_name | table_type |
|------------|------------|
| whoop_raw_data | BASE TABLE |

### Step 4: Restart Server

After running the migration, restart the WHOOP API server:

```bash
# Stop the server (Ctrl+C if running in terminal)

# Start the server
python start.py
```

### Step 5: Test Data Sync

Run the interactive test script to verify everything works:

```bash
python tests/interactive_test.py
```

**What to expect:**
1. ✅ Authentication should succeed
2. ✅ WHOOP status check should work
3. ✅ Data sync should complete WITHOUT errors
4. ✅ You should see records stored for recovery, sleep, workouts, and cycles

### Step 6: Verify Data in Database

Check that data was actually stored:

```sql
-- Check recovery records
SELECT COUNT(*) as recovery_count FROM whoop_recovery;

-- Check sleep records
SELECT COUNT(*) as sleep_count FROM whoop_sleep;

-- Check workout records
SELECT COUNT(*) as workout_count FROM whoop_workout;

-- Check cycle records
SELECT COUNT(*) as cycle_count FROM whoop_cycle;

-- Check raw data
SELECT COUNT(*) as raw_data_count FROM whoop_raw_data;

-- View sample recovery data
SELECT
    recovery_score,
    hrv_rmssd_milli,
    resting_heart_rate,
    created_at
FROM whoop_recovery
ORDER BY created_at DESC
LIMIT 5;
```

## Troubleshooting

### Migration Fails with "column does not exist"

**Cause**: You might be running migration 003 before migration 002.

**Solution**: Run migrations in order:
1. `002_whoop_data_tables_supabase.sql` (creates tables)
2. `003_fix_data_types.sql` (fixes data types)

### Still Getting "invalid input syntax" Errors

**Cause**: Migration didn't run successfully or server wasn't restarted.

**Solution**:
1. Verify migration ran: Check column types in Supabase dashboard
2. Restart the server: `Ctrl+C` then `python start.py`
3. Clear any cached connections

### Duplicate Key Errors Continue

**Cause**: Old server process still running with old code.

**Solution**:
1. Make sure you have the latest code changes
2. Completely stop all Python processes: `pkill -f "python.*start.py"`
3. Restart: `python start.py`

### Data Not Appearing in Database

**Cause**: RLS (Row Level Security) policies might be blocking access.

**Solution**: Verify you're using the SERVICE_KEY (not anon key) in `.env`:
```bash
# Check your .env file
SUPABASE_SERVICE_KEY=eyJhbGc...  # Should be service_role key, not anon key
```

## Rollback (If Needed)

If you need to rollback the migration:

```sql
-- Revert column types (WARNING: May lose decimal precision!)
ALTER TABLE whoop_recovery ALTER COLUMN hrv_rmssd_milli TYPE INTEGER;
ALTER TABLE whoop_sleep ALTER COLUMN sleep_performance_percentage TYPE INTEGER;
ALTER TABLE whoop_sleep ALTER COLUMN sleep_consistency_percentage TYPE INTEGER;
ALTER TABLE whoop_sleep ALTER COLUMN sleep_efficiency_percentage TYPE INTEGER;
ALTER TABLE whoop_sleep ALTER COLUMN cycle_id TYPE INTEGER USING cycle_id::INTEGER;
ALTER TABLE whoop_cycle ALTER COLUMN calories_burned TYPE INTEGER USING calories_burned::INTEGER;

-- Drop whoop_raw_data table
DROP TABLE IF EXISTS whoop_raw_data;
```

## Summary of Changes

### Files Modified

1. **migrations/003_fix_data_types.sql** (NEW)
   - Fixes all data type mismatches
   - Creates whoop_raw_data table
   - Includes verification queries

2. **app/repositories/whoop_data_repository.py**
   - Line 64-67: Fixed upsert to specify conflict columns

### No Changes Required

The following files were already correct:
- `app/api/internal.py` - Already fixed in previous session
- `app/services/whoop_service.py` - Already fixed in previous session
- `tests/interactive_test.py` - Already working correctly

## Next Steps After Migration

1. **Run Regular Syncs**: Test syncing data multiple times to ensure stability
2. **Monitor Logs**: Watch for any new errors in the server logs
3. **Check Data Quality**: Verify decimal values are stored correctly
4. **Set Up Automated Syncs**: Consider scheduling regular data syncs

## Support

If you encounter issues not covered in this guide:

1. Check server logs for specific error messages
2. Verify all environment variables are set correctly
3. Ensure Supabase service key has proper permissions
4. Check Supabase dashboard for RLS policy issues
