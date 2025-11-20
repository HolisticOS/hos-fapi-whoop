# Testing Instructions - Recovery & Individual Tables Debug

## What Changed

I've added **extensive debugging logs** to track exactly why data isn't being stored in individual tables.

## How to Test

### 1. Restart the Server
```bash
python start.py
```

### 2. Run the Sync Test
```bash
python tests/interactive_test.py
# Enter 7 when asked for days
```

### 3. Watch for These Critical Log Messages

#### Recovery Data Debug
```
🔍 Recovery data_response has X records
🔍 Recovery record 0: has_raw_data=True/False, raw_data_type=<class 'dict'>, raw_data_empty=True/False
🔍 Recovery record 1: has_raw_data=True/False, raw_data_type=<class 'dict'>, raw_data_empty=True/False
💾 Extracted X recovery records with raw_data (from Y total)
```

**Key Question**: Is `raw_data_empty=True`? If so, that's why data isn't storing!

#### Sleep Data Debug
```
🔍 Sleep data_response has X records
🔍 Sleep record 0: has_raw_data=True/False, raw_data_type=<class 'dict'>, raw_data_empty=True/False
💾 Extracted X sleep records with raw_data (from Y total)
```

#### Workout Data Debug
```
🔍 Workout data_response has X records
🔍 Workout record 0: has_raw_data=True/False, raw_data_type=<class 'dict'>, raw_data_empty=True/False
💾 Extracted X workout records with raw_data (from Y total)
```

#### Expected vs Actual

**If working correctly**:
```
🔍 Recovery data_response has 6 records
🔍 Recovery record 0: has_raw_data=True, raw_data_type=<class 'dict'>, raw_data_empty=False
💾 Extracted 6 recovery records with raw_data (from 6 total)
💾 Storing 6 recovery records to whoop_recovery table
✅ Stored 6 recovery records
```

**If broken (likely scenario)**:
```
🔍 Recovery data_response has 6 records
🔍 Recovery record 0: has_raw_data=True, raw_data_type=<class 'dict'>, raw_data_empty=True  ← PROBLEM!
💾 Extracted 0 recovery records with raw_data (from 6 total)  ← FILTERED OUT!
⚠️ No recovery records to store - raw_data extraction returned empty list
```

## What to Share

After running the test, please share:

1. **All log lines with 🔍** - These show what's in the data models
2. **All log lines with 💾** - These show the extraction process
3. **All log lines with ⚠️** - These show why storage was skipped

## My Hypothesis

I believe the issue is:
- The `WhoopRecoveryData`, `WhoopSleepData`, `WhoopWorkoutData` models are being created
- But their `raw_data` field is an **empty dict `{}`** instead of containing the actual API response
- This causes the filter `if hasattr(r, 'raw_data') and r.raw_data` to fail (empty dict is falsy in Python)
- So no records pass the extraction filter

**If this is correct**, the fix is to ensure we properly populate `raw_data=record` when creating these models in `whoop_service.py`.

## Next Steps

Based on what the logs show, I'll know exactly where to fix the code:

- **If `raw_data_empty=True`**: Need to fix model creation in `get_recovery_data()`, `get_sleep_data()`, `get_workout_data()`
- **If `has_raw_data=False`**: Need to ensure the field is defined in the models
- **If extraction count = 0**: Need to adjust the filter logic

The logs will tell us everything we need to know! 🔍
