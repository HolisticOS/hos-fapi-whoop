# Recovery Database Fix - 2025-11-20

## Issue Identified ✅

**Error**:
```
Failed to store recovery record: {'message': 'invalid input syntax for type integer: "70.0"', 'code': '22P02'}
Failed to store recovery record: {'message': 'invalid input syntax for type integer: "53.0"', 'code': '22P02'}
```

**Root Cause**: WHOOP API v2 returns ALL numeric values as floats (70.0, 53.0, 94.0), but several database columns are defined as INTEGER:
- `recovery_score` - Should be DECIMAL (can have decimal precision like 53.5)
- `resting_heart_rate` - Should be INTEGER (but API returns 70.0 instead of 70)
- `spo2_percentage` - Should be INTEGER (but API returns 94.0 instead of 94)

## Two-Part Fix

### Part 1: Python Code ✅ (DONE - Already Fixed)

Updated `app/repositories/whoop_data_repository.py` to convert float to int for fields that should be integers:

```python
def safe_int(value):
    """Convert float to int, return None if value is None"""
    return int(value) if value is not None else None

data = {
    'resting_heart_rate': safe_int(record.get('score', {}).get('resting_heart_rate')),
    'spo2_percentage': safe_int(record.get('score', {}).get('spo2_percentage')),
    ...
}
```

This converts 70.0 → 70, 94.0 → 94 before database insertion.

**Result**: Heart rate and SpO2 values can now be stored in INTEGER columns.

### Part 2: Database Schema ⚠️ (TODO - Run SQL Migration)

Still need to fix `recovery_score` column type in the database.

## Database Schema Issue

**Current Schema** (WRONG):
```sql
whoop_recovery.recovery_score INTEGER
```

**Required Schema** (CORRECT):
```sql
whoop_recovery.recovery_score DECIMAL(5,2)
```

This allows values like 53.0, 76.5, 99.25, etc.

## Fix: Run SQL Migration

### Step 1: Access Supabase SQL Editor

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Navigate to **SQL Editor** in the left sidebar
4. Click **New Query**

### Step 2: Run the Migration

Copy and paste this SQL:

```sql
-- Fix recovery_score column type from INTEGER to DECIMAL
-- Migration: 003_fix_recovery_score_type
-- Date: 2025-11-20

BEGIN;

ALTER TABLE whoop_recovery
  ALTER COLUMN recovery_score TYPE DECIMAL(5,2);

COMMENT ON COLUMN whoop_recovery.recovery_score IS 'Recovery score percentage (0-100) from WHOOP API - stored as decimal';

COMMIT;
```

### Step 3: Verify the Fix

Run this verification query:

```sql
SELECT column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_name = 'whoop_recovery' AND column_name = 'recovery_score';
```

**Expected Result**:
```
column_name     | data_type | numeric_precision | numeric_scale
----------------|-----------|-------------------|---------------
recovery_score  | numeric   | 5                 | 2
```

### Step 4: Restart Server and Test

**Restart the server** (Python code fix is already applied):

```bash
# Stop server (Ctrl+C)
python start.py
```

**Run sync test**:
```bash
python tests/interactive_test.py
# Enter 7 when asked for days
```

## Expected Results After Fix

### Sync Output:
```
✓ Data sync completed!
  Recovery records: 6  ← Should now show 6 instead of 0!
  Sleep records: 7
  Workout records: 25
  Cycle records: 8
  Total stored: 46
```

### Database Verification:
```sql
-- Check recovery records in database
SELECT
  id,
  user_id,
  recovery_score,
  hrv_rmssd_milli,
  resting_heart_rate,
  created_at
FROM whoop_recovery
WHERE user_id = 'a57f70b4-d0a4-4aef-b721-a4b526f64869'
ORDER BY created_at DESC
LIMIT 10;
```

**Expected**: You should see 6 recovery records with decimal scores like 53.0, 76.0, 31.0, etc.

## Why This Happened

The database schema file (`planning/whoop-mvp-database-schema.sql`) correctly defines:
```sql
recovery_score DECIMAL(5,2)  -- Correct!
```

But the actual `whoop_recovery` table in Supabase was created with:
```sql
recovery_score INTEGER  -- Wrong!
```

This mismatch caused the insert failures.

## Files Created

1. **migrations/003_fix_recovery_score_type.sql**
   - SQL migration to fix the column type

2. **RECOVERY_DATABASE_FIX.md** (this file)
   - Documentation and instructions

## Summary

✅ **Issue**: Database column type mismatch (INTEGER vs DECIMAL)

✅ **Fix**: Run SQL migration to change column type

✅ **Verification**: Recovery records will now be stored successfully

Run the migration in Supabase SQL Editor, then test the sync! 🎯
