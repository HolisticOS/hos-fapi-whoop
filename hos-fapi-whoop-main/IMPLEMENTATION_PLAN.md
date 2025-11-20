# WHOOP Database-First Implementation Plan

## Executive Summary

**Goal**: Implement a database-backed WHOOP sync system where:
- All WHOOP data is stored in PostgreSQL/Supabase
- Flutter app fetches from database (not direct API calls)
- Backend syncs with WHOOP 4x daily automatically
- No duplicate data
- No mock data in UI

**Timeline**: ~3-4 hours of implementation + testing

---

## Current State vs. Target State

### Current State ❌
```
User opens Health tab
    ↓
App calls Backend API
    ↓
Backend calls WHOOP API (every time)
    ↓
Returns data to app
    ↓
If error → Show mock data
```

**Problems**:
- Wastes API calls (rate limited)
- Slow user experience
- Mock data is confusing
- No persistence between sessions

### Target State ✅
```
User opens Health tab
    ↓
App calls Backend API
    ↓
Backend checks DATABASE first
    ├→ Data exists? Return immediately (FAST)
    └→ Data missing? Sync from WHOOP → Store → Return

Background (4x daily):
    ↓
Scheduled task runs
    ↓
Fetch new WHOOP data for all users
    ↓
Store in database (skip duplicates)
    ↓
Users see fresh data next time they open app
```

**Benefits**:
- Fast response times (database query ~10ms)
- Reduced WHOOP API calls (60-80% reduction)
- No mock data confusion
- Data persists across sessions
- Works offline (shows last synced data)

---

## Architecture Overview

```
┌──────────────────┐
│  Flutter App     │  Shows data from database only
│  (hos_mvp_2)     │  4 sync triggers/day (optional)
└────────┬─────────┘
         │ GET /daily-data?date=X
         ↓
┌──────────────────┐
│  Backend API     │  Database-first logic
│  (FastAPI)       │  - Check DB → Return if exists
└────────┬─────────┘  - Missing? → Fetch from WHOOP
         │
         ├→ ┌────────────────┐
         │  │  PostgreSQL    │  Stores all WHOOP data
         │  │  (Supabase)    │  - whoop_recovery
         │  │                │  - whoop_sleep
         │  └────────────────┘  - whoop_workout
         │                      - whoop_cycle
         │                      - whoop_sync_log
         │
         └→ ┌────────────────┐
            │  WHOOP API     │  Only called when needed
            │  (External)    │  Triggered by:
            └────────────────┘  - Scheduled sync (4x/day)
                                - Missing data request
                                - Manual refresh
```

---

## Data Flow Examples

### Example 1: User Opens Health Tab (Data Exists)

```
1. User opens Health tab, selects date: 2025-01-20

2. Flutter calls:
   GET /api/v1/whoop/daily-data/user123?date=2025-01-20

3. Backend executes:
   - Query whoop_recovery WHERE user_id='user123' AND date='2025-01-20'
   - Query whoop_sleep WHERE user_id='user123' AND date='2025-01-20'
   - Query whoop_workout WHERE user_id='user123' AND date='2025-01-20'
   - Query whoop_cycle WHERE user_id='user123' AND date='2025-01-20'

4. Database returns data (10ms):
   {
     "recovery": { "score": 82, "hrv": 65, "rhr": 58 },
     "sleep": { "duration": "7h 32m", "performance": 74 },
     "cycle": { "strain": 14.2, "calories": 2847 }
   }

5. Backend returns to Flutter

6. UI updates with data

Total time: ~50ms (very fast!)
API calls to WHOOP: 0 ✅
```

### Example 2: User Opens Health Tab (Data Missing)

```
1. User opens Health tab, selects date: 2025-01-20

2. Flutter calls:
   GET /api/v1/whoop/daily-data/user123?date=2025-01-20

3. Backend queries database:
   - No data found for 2025-01-20

4. Backend checks:
   - Is date recent? (< 7 days old)
   - Yes → Trigger sync

5. Backend calls WHOOP API:
   - Fetch recovery for 2025-01-20
   - Fetch sleep for 2025-01-20
   - Fetch workouts for 2025-01-20
   - Fetch cycle for 2025-01-20

6. Backend stores in database:
   - INSERT INTO whoop_recovery (...)
   - INSERT INTO whoop_sleep (...)
   - INSERT INTO whoop_workout (...)
   - INSERT INTO whoop_cycle (...)

7. Backend updates sync log:
   - UPDATE whoop_sync_log SET last_sync_at = NOW()

8. Backend returns data to Flutter

9. UI updates with data

Total time: ~2-3 seconds (acceptable for first fetch)
API calls to WHOOP: 4 (only once per date)
```

### Example 3: Scheduled Sync (Background - 4x Daily)

```
8:00 AM - Morning Sync
├→ Get all active WHOOP users from database
├→ For each user:
│  ├→ Check last sync time for 'recovery'
│  │  └→ Last sync: 2025-01-19 23:00
│  ├→ Fetch NEW recovery data since last sync
│  │  └→ WHOOP API: GET /recovery?start=2025-01-19T23:00
│  ├→ Store new records (skip duplicates)
│  │  └→ INSERT ... ON CONFLICT DO NOTHING
│  └→ Update sync log
│     └→ UPDATE whoop_sync_log SET last_sync_at=NOW()
│
└→ Repeat for 'sleep' data

2:00 PM - Afternoon Sync
└→ Same process for 'workout' and 'cycle'

8:00 PM - Evening Sync
└→ Same process for 'workout' and 'cycle'

11:00 PM - Night Sync
└→ Full sync for all data types
```

**Result**: Users always have fresh data when they open the app!

---

## Database Schema (Simplified)

### whoop_recovery (Daily Recovery Scores)
```sql
id                  TEXT PRIMARY KEY    -- WHOOP record ID (prevents duplicates)
user_id             TEXT
recovery_score      INTEGER             -- 0-100
hrv_rmssd_milli     INTEGER             -- HRV value
resting_heart_rate  INTEGER             -- RHR in BPM
created_at          TIMESTAMPTZ         -- Date of recovery
```

### whoop_sleep (Sleep Sessions)
```sql
id                             TEXT PRIMARY KEY
user_id                        TEXT
total_sleep_time_milli         BIGINT          -- Duration in ms
sleep_performance_percentage   INTEGER         -- 0-100
start_time                     TIMESTAMPTZ
end_time                       TIMESTAMPTZ     -- Date to query by
```

### whoop_workout (Exercise Sessions)
```sql
id                  TEXT PRIMARY KEY
user_id             TEXT
strain_score        NUMERIC(5,2)     -- 0-21
calories_burned     NUMERIC(10,2)    -- Kilojoules
start_time          TIMESTAMPTZ      -- Date to query by
end_time            TIMESTAMPTZ
```

### whoop_cycle (Daily Strain Cycles)
```sql
id              TEXT PRIMARY KEY
user_id         TEXT
day_strain      NUMERIC(5,2)     -- 0-21 (daily cumulative)
calories_burned INTEGER
start_time      TIMESTAMPTZ      -- Date to query by
```

### whoop_sync_log (Sync Metadata)
```sql
user_id          TEXT
data_type        TEXT             -- 'recovery', 'sleep', 'workout', 'cycle'
last_sync_at     TIMESTAMPTZ      -- When last synced
records_synced   INTEGER          -- Total records ever synced
sync_status      TEXT             -- 'success', 'failed'

UNIQUE(user_id, data_type)        -- One row per user per type
```

**Key Point**: WHOOP record IDs are PRIMARY KEYS → automatic duplicate prevention!

---

## Implementation Steps (Detailed)

### Phase 1: Database Setup (15 minutes)

**Step 1.1**: Run migration script
```bash
cd hos-fapi-whoop/hos-fapi-whoop-main
psql -U your_user -d your_database -f migrations/002_whoop_data_tables.sql
```

**Step 1.2**: Verify tables created
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'whoop_%';

-- Should show:
-- whoop_recovery
-- whoop_sleep
-- whoop_workout
-- whoop_cycle
-- whoop_sync_log
```

**Step 1.3**: Test helper functions
```sql
-- Test getting daily summary
SELECT * FROM get_daily_summary('test_user_123', '2025-01-20');
```

**Deliverable**: ✅ Database schema ready

---

### Phase 2: Backend Repository Layer (30 minutes)

**Step 2.1**: Create repository package
```bash
cd app
mkdir -p repositories
touch repositories/__init__.py
```

**Step 2.2**: Add repository to `__init__.py`
```python
# app/repositories/__init__.py
from .whoop_data_repository import WhoopDataRepository

__all__ = ['WhoopDataRepository']
```

**Step 2.3**: Test repository (optional)
```python
# Test script
from app.repositories import WhoopDataRepository
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
repo = WhoopDataRepository(supabase)

# Test storing a record
test_record = {
    'id': 'test-recovery-123',
    'score': {'recovery_score': 85},
    'created_at': '2025-01-20T08:00:00Z'
}
await repo.store_recovery_records('user123', [test_record])

# Test retrieving
data = await repo.get_recovery_by_date('user123', date(2025, 1, 20))
print(data)  # Should show test record
```

**Deliverable**: ✅ Repository layer working

---

### Phase 3: Backend Service Layer (45 minutes)

**Step 3.1**: Modify whoop_service.py to add database-first logic

**Step 3.2**: Create new endpoints:
- `GET /api/v1/whoop/daily-data/{user_id}` - Database-first fetch
- `POST /api/v1/whoop/sync/{user_id}` - Manual sync trigger
- `GET /api/v1/whoop/sync-status/{user_id}` - Check sync status

**Step 3.3**: Add incremental sync function
```python
async def incremental_sync(user_id: str, data_type: str):
    # Get last sync time
    # Fetch only new records from WHOOP
    # Store in database
    # Update sync log
```

**Deliverable**: ✅ Database-first endpoints working

---

### Phase 4: Scheduled Sync (30 minutes)

**Step 4.1**: Install scheduler
```bash
pip install apscheduler
```

**Step 4.2**: Create sync tasks file
```python
# app/tasks/scheduled_sync.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=8)
async def morning_sync():
    # Sync recovery + sleep for all users
    pass
```

**Step 4.3**: Start scheduler in main.py
```python
from app.tasks.scheduled_sync import scheduler

@app.on_event("startup")
async def startup_event():
    scheduler.start()
```

**Deliverable**: ✅ Background sync running 4x daily

---

### Phase 5: Flutter App Updates (45 minutes)

**Step 5.1**: Remove mock data fallback in health_screen.dart

**Step 5.2**: Add "Connect WHOOP" UI when not connected

**Step 5.3**: Add "No Data" UI when database is empty

**Step 5.4**: Update _loadData() to only fetch from database

**Deliverable**: ✅ UI shows only real data

---

### Phase 6: Testing (30 minutes)

**Test 1**: Connect WHOOP device
```
1. Open Flutter app
2. Tap devices icon
3. Connect WHOOP
4. Verify OAuth completes
```

**Test 2**: Initial data load
```
1. After connecting, open Health tab
2. Should trigger sync (first time)
3. Wait ~3 seconds
4. Verify data appears
5. Check database has records
```

**Test 3**: Subsequent loads (should be fast)
```
1. Close and reopen Health tab
2. Should load in < 100ms (from database)
3. No WHOOP API call
```

**Test 4**: Scheduled sync
```
1. Wait for scheduled time (or manually trigger)
2. Check logs for sync execution
3. Verify new records in database
```

**Test 5**: Date navigation
```
1. Use date picker to select different dates
2. Verify correct data shows
3. Check "No data" appears for old dates
```

**Deliverable**: ✅ End-to-end flow working

---

## Expected Outcomes

### User Experience
- ✅ Health tab opens instantly (<100ms)
- ✅ Always shows latest synced data
- ✅ No confusing mock data
- ✅ Clear "Connect WHOOP" prompt when disconnected
- ✅ Works offline (shows last synced data)

### System Performance
- ✅ 80% reduction in WHOOP API calls
- ✅ Within free tier limits (10K requests/day)
- ✅ Support for 1,600+ users
- ✅ Database queries ~10ms avg
- ✅ No duplicate records

### Developer Experience
- ✅ Clear separation: UI → Backend → Database → WHOOP
- ✅ Easy debugging (check database directly)
- ✅ Incremental sync prevents data loss
- ✅ Sync logs track all activity

---

## Questions to Confirm Before Proceeding

1. **Database Access**: Do you have PostgreSQL/Supabase credentials ready?
   - [ ] Yes, I can connect to the database
   - [ ] No, need help setting up

2. **Current Tables**: Did you already run `setup_test_db.sql`?
   - [ ] Yes, I have whoop_users and whoop_oauth_states
   - [ ] No, starting fresh

3. **Sync Preference**: Which sync approach do you prefer?
   - [ ] Backend scheduled sync (recommended - works 24/7)
   - [ ] Flutter background sync (simpler, but only when app is open)

4. **Testing**: Do you have a WHOOP device to test with?
   - [ ] Yes, I can connect my device
   - [ ] No, will test with mock API responses

5. **Timeline**: When do you want to implement this?
   - [ ] Now (I'm ready)
   - [ ] Review plan first, then implement

---

## Next Steps

**Once you confirm the plan above, I will**:

1. Create remaining backend files:
   - `app/repositories/__init__.py`
   - Modified `app/services/whoop_service.py` with database-first logic
   - New endpoint implementations
   - Scheduled sync tasks

2. Create Flutter updates:
   - Remove mock data
   - Add "Connect WHOOP" UI
   - Add "No Data" UI
   - Update data loading logic

3. Provide testing script with step-by-step verification

**Total implementation time**: ~3-4 hours

Ready to proceed? Let me know if you have any questions about the plan!
