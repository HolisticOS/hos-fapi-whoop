# Recovery Parsing Debug - 2025-11-20

## Current Status

### ✅ Working:
- Sleep data: Fetched and parsed into `whoop_sleep` table (7 records)
- Workout data: Fetched and parsed into `whoop_workout` table (25 records)
- Cycle data: Fetched and parsed into `whoop_cycle` table (8 records)
- Recovery raw data: Fetched and stored in `whoop_raw_data` table

### ❌ Not Working:
- Recovery parsed data: NOT being stored in `whoop_recovery` table (0 records)

## The Issue

Recovery data is being fetched from the WHOOP v2 API and stored as raw JSON in `whoop_raw_data`, but it's NOT being parsed into `WhoopRecoveryData` Pydantic models and stored in the individual `whoop_recovery` table.

**Symptoms:**
- Sync output shows: "Recovery records: 0"
- BUT recovery IS in `whoop_raw_data` table
- Direct recovery endpoint fetch works (shows 6 records)

## Root Cause Analysis

The issue is in `app/services/whoop_service.py` in the `get_recovery_data()` function (lines 563-596).

**Hypothesis**: Recovery records are failing to parse due to:
1. Missing required fields in API response
2. Field type mismatches (e.g., int vs str)
3. Pydantic validation errors
4. Exceptions being silently caught

## WHOOP v2 Recovery API Response Structure

Based on test data from `test_output/whoop_daily_data_test_user_002_20251120_100517.txt`:

```json
{
  "cycle_id": 1163828763,
  "sleep_id": "520a391a-e94e-47f2-bad5-8ea6264b36b9",
  "user_id": 23873948,
  "created_at": "2025-11-20T11:38:57.131Z",
  "updated_at": "2025-11-20T11:38:57.131Z",
  "score_state": "SCORED",
  "score": {
    "user_calibrating": false,
    "recovery_score": 53.0,
    "resting_heart_rate": 70.0,
    "hrv_rmssd_milli": 50.893276,
    "spo2_percentage": 94.0,
    "skin_temp_celsius": 35.2
  }
}
```

## Current Parsing Logic

```python
recovery_data = WhoopRecoveryData(
    cycle_id=record["cycle_id"],  # Required: int
    user_id=record["user_id"],  # Required: int
    recovery_score=record.get("score", {}).get("recovery_score"),  # Optional: float
    hrv_rmssd=record.get("score", {}).get("hrv_rmssd_milli"),  # Optional: float
    resting_heart_rate=record.get("score", {}).get("resting_heart_rate"),  # Optional: float
    respiratory_rate=None,  # Optional: float
    recorded_at=record.get("created_at"),  # Required: str
    raw_data=record  # Required: dict
)
```

## Debug Logging Added

Added comprehensive logging to `app/services/whoop_service.py` lines 566-596:

### Before Parsing (Info Level):
```python
logger.info("🔍 Parsing recovery record",
    user_id=user_id,
    cycle_id=record.get("cycle_id"),
    has_score=bool(record.get("score")),
    has_created_at=bool(record.get("created_at")))
```

### On Success (Info Level):
```python
logger.info("✅ Successfully parsed recovery record",
    user_id=user_id,
    cycle_id=record.get("cycle_id"))
```

### On Failure (Warning Level):
```python
logger.warning("❌ Failed to parse v2 recovery record",
    user_id=user_id,
    cycle_id=record.get("cycle_id"),
    has_cycle_id=bool(record.get("cycle_id")),
    has_user_id=bool(record.get("user_id")),
    has_created_at=bool(record.get("created_at")),
    error=str(parse_error),
    error_type=type(parse_error).__name__)
```

## Testing Steps

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

3. **Check server logs** for the new debug messages:

### Expected Logs if Parsing Succeeds:
```
🔍 Parsing recovery record cycle_id=1163828763 has_score=True has_created_at=True
✅ Successfully parsed recovery record cycle_id=1163828763
✅ Retrieved v2 recovery data count=6
💾 Extracted 6 recovery records with raw_data
💾 Storing 6 recovery records to whoop_recovery table
✅ Stored 6 recovery records
```

### Expected Logs if Parsing Fails:
```
🔍 Parsing recovery record cycle_id=1163828763 has_score=True has_created_at=True
❌ Failed to parse v2 recovery record
  cycle_id=1163828763
  has_cycle_id=True
  has_user_id=True
  has_created_at=True
  error="..."
  error_type="ValidationError"
```

## Possible Failure Scenarios

### Scenario 1: Missing `created_at` Field
**Symptom**: `has_created_at=False` in logs
**Fix**: Change `recorded_at` field to Optional in Pydantic model

### Scenario 2: Field Type Mismatch
**Symptom**: `error_type="ValidationError"` with type conversion error
**Fix**: Update Pydantic model field types to match API response

### Scenario 3: Required Field is None
**Symptom**: `error_type="ValidationError"` with "none is not an allowed value"
**Fix**: Change required fields to Optional

### Scenario 4: Entire Response is Empty
**Symptom**: No parsing logs at all
**Check**: `📦 Processing recovery API response records_count=0`
**Reason**: API returned empty records array

## Next Steps

1. Run the sync test with the new logging
2. Share the full server logs
3. Identify which scenario is causing the parsing failure
4. Apply the appropriate fix based on the error logs

## Files Modified

1. **app/services/whoop_service.py**
   - Lines 566-596: Added detailed logging for recovery record parsing

## Expected Outcome

After applying the fix based on the debug logs, recovery data should:
- ✅ Be fetched from `/v2/recovery` endpoint
- ✅ Be stored in `whoop_raw_data` table
- ✅ Be parsed into `WhoopRecoveryData` models
- ✅ Be stored in `whoop_recovery` individual table

Run the test and share the logs so we can identify the exact issue! 🔍
