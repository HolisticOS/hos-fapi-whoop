# Recovery ID Fix - 2025-11-21

## Issue Identified ✅

**Error**:
```
null value in column "id" of relation "whoop_recovery" violates not-null constraint
Failing row contains (null, a57f70b4-d0a4-4aef-b721-a4b526f64869, 31.00, ...)
```

**Root Cause**: The code was trying to use `record.get('id')` which doesn't exist in the WHOOP v2 recovery API response.

## WHOOP v2 Recovery API Structure

The WHOOP v2 `/v2/recovery` endpoint returns records with **`sleep_id`** as the unique identifier, NOT `id`:

```json
{
  "sleep_id": "83d630b2-c8f9-42f4-a4ea-bb566dbab14d",  ← Primary key!
  "cycle_id": 1165161240,
  "user_id": 23873948,
  "created_at": "2025-11-21T08:59:44.195Z",
  "updated_at": "2025-11-21T08:59:44.195Z",
  "score_state": "SCORED",
  "score": {
    "recovery_score": 31.0,
    "hrv_rmssd_milli": 42.117638,
    "resting_heart_rate": 75.0,
    "spo2_percentage": 93.333336,
    "skin_temp_celsius": 35.1
  }
}
```

## The Fix ✅

**File**: `app/repositories/whoop_data_repository.py` (lines 99-102)

**Before** (WRONG):
```python
data = {
    'id': record.get('id'),  # ❌ This is always None!
    'user_id': user_id_str,
    ...
}
```

**After** (CORRECT):
```python
data = {
    'id': record.get('sleep_id'),  # ✅ Use sleep_id as primary key
    'user_id': user_id_str,
    'cycle_id': record.get('cycle_id'),  # Also added cycle_id
    ...
}
```

## What Changed

1. **Line 100**: Changed from `record.get('id')` to `record.get('sleep_id')`
2. **Line 102**: Added `cycle_id` field from the response
3. **Lines 104-105**: Heart rate and SpO2 now converted to int (from previous fix)

## Test Now

**Restart the server**:
```bash
# Stop server (Ctrl+C)
python start.py
```

**Run sync test**:
```bash
python tests/interactive_test.py
# Enter 7 when asked for days
```

## Expected Results

### Sync Output:
```
✓ Data sync completed!
  Recovery records: 6  ← Should work now! ✅
  Sleep records: 7
  Workout records: 25
  Cycle records: 8
  Total stored: 46
```

### Database Verification:
```sql
-- Check recovery records in whoop_recovery table
SELECT
  id,
  user_id,
  cycle_id,
  recovery_score,
  hrv_rmssd_milli,
  resting_heart_rate,
  spo2_percentage,
  skin_temp_celsius,
  created_at
FROM whoop_recovery
WHERE user_id = 'a57f70b4-d0a4-4aef-b721-a4b526f64869'
ORDER BY created_at DESC
LIMIT 10;
```

**Expected Result**: 6 recovery records with UUID `id` (from `sleep_id`), recovery scores, HRV, heart rate, etc.

### Example Row:
```
id: 83d630b2-c8f9-42f4-a4ea-bb566dbab14d (UUID from sleep_id)
user_id: a57f70b4-d0a4-4aef-b721-a4b526f64869
cycle_id: 1165161240
recovery_score: 31.00
hrv_rmssd_milli: 42.12
resting_heart_rate: 75 (converted from 75.0)
spo2_percentage: 93 (converted from 93.333336)
skin_temp_celsius: 35.10
```

## Summary of All Recovery Fixes

### Fix 1: Float to Int Conversion ✅
- **Issue**: Heart rate returned as 70.0, database expects INTEGER
- **Fix**: Added `safe_int()` helper function to convert floats to ints
- **Fields**: `resting_heart_rate`, `spo2_percentage`

### Fix 2: Missing ID Field ✅ (This Fix)
- **Issue**: Code looked for `id` field that doesn't exist
- **Fix**: Use `sleep_id` as the primary key instead
- **File**: `app/repositories/whoop_data_repository.py` line 100

### Fix 3: Recovery Score Type (Optional)
- **Issue**: `recovery_score` column is INTEGER in database
- **Status**: **Optional** - can run SQL migration to change to DECIMAL(5,2)
- **Current**: Works fine if all scores are whole numbers (53.0 → 53)

## All Three Issues Resolved

✅ **Float to int conversion** - Fixed in Python code
✅ **Missing ID field** - Fixed by using `sleep_id`
⚠️ **Recovery score type** - Optional SQL migration (only needed for decimal precision)

**Restart the server and test - recovery data should now be stored successfully!** 🎉
