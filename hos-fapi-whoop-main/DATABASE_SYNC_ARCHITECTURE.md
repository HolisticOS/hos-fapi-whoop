# WHOOP Database-First Sync Architecture

## Overview

This document describes the **database-first** architecture for WHOOP data syncing with **incremental sync** to prevent duplicates and minimize API calls.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Flutter App (hos_mvp_2)                 │
│                                                               │
│  - Health Screen shows data from database                   │
│  - 4x daily background sync triggers                        │
│  - NO mock data fallback                                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ HTTP GET /api/v1/whoop/daily-data/{user_id}?date=YYYY-MM-DD
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            FastAPI Backend (hos-fapi-whoop)                 │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Endpoints (Database-First)                      │   │
│  │  - Check database first                              │   │
│  │  - Fetch from WHOOP only if data missing/stale       │   │
│  │  - Always store fetched data                         │   │
│  └────────────┬──────────────────────────────┬─────────┘   │
│               │                                │              │
│               ↓                                ↓              │
│  ┌──────────────────────┐         ┌──────────────────────┐ │
│  │  Whoop Service       │         │  Data Repository     │ │
│  │  - API calls         │←────────│  - Store/retrieve    │ │
│  │  - Token refresh     │         │  - Incremental sync  │ │
│  │  - Rate limiting     │         │  - Deduplication     │ │
│  └──────────────────────┘         └─────────┬────────────┘ │
│               │                              │               │
└───────────────┼──────────────────────────────┼───────────────┘
                │                              │
                ↓                              ↓
        ┌──────────────┐           ┌──────────────────────┐
        │  WHOOP API   │           │  Supabase/PostgreSQL │
        │  (External)  │           │  - whoop_recovery    │
        └──────────────┘           │  - whoop_sleep       │
                                    │  - whoop_workout     │
                                    │  - whoop_cycle       │
                                    │  - whoop_sync_log    │
                                    └──────────────────────┘
```

## Key Principles

### 1. Database-First Approach
- **Always check database before calling WHOOP API**
- **Only fetch from WHOOP if**:
  - Data doesn't exist in database
  - Data is stale (> 24 hours old)
  - User explicitly triggers refresh

### 2. Incremental Sync
- **Prevent duplicates**: Use WHOOP record IDs as primary keys
- **Track sync times**: `whoop_sync_log` table records last sync per data type
- **Smart fetching**: Only fetch new data since last sync

### 3. No Mock Data
- **Flutter app shows "No data" if database is empty**
- **Forces user to connect WHOOP device**
- **Ensures data authenticity**

## Database Schema

### Core Data Tables

```sql
whoop_recovery       -- Daily recovery scores (1 per day)
whoop_sleep          -- Sleep sessions (1-2 per day typically)
whoop_workout        -- Individual workouts (0-N per day)
whoop_cycle          -- Daily physiological cycles (1 per day)
whoop_sync_log       -- Sync metadata (1 row per user per data type)
```

### Sync Log Table

```sql
CREATE TABLE whoop_sync_log (
    user_id TEXT,
    data_type TEXT,              -- 'recovery', 'sleep', 'workout', 'cycle'
    last_sync_at TIMESTAMPTZ,    -- When was last successful sync
    sync_status TEXT,             -- 'success', 'partial', 'failed'
    records_synced INTEGER,       -- Total records synced so far
    UNIQUE(user_id, data_type)    -- One row per user per type
);
```

## Sync Flow

### Initial Sync (User Connects WHOOP)

```
1. User authorizes WHOOP via OAuth
   └→ Tokens stored in whoop_users table

2. App triggers initial sync
   └→ POST /api/v1/whoop/sync/{user_id}

3. Backend checks whoop_sync_log
   └→ No previous sync found
   └→ Fetch last 30 days of data from WHOOP

4. Store all records in database
   ├→ whoop_recovery (30 records)
   ├→ whoop_sleep (~30-60 records)
   ├→ whoop_workout (~0-90 records)
   └→ whoop_cycle (30 records)

5. Update whoop_sync_log
   └→ Set last_sync_at = NOW()

6. Return data from database to app
```

### Scheduled Sync (4x Daily)

```
Morning Sync (8 AM)
├→ Check last_sync_at for each data type
├→ Fetch only NEW records since last sync
├→ Store new records (skip duplicates via UPSERT)
└→ Update sync log

Afternoon Sync (2 PM)
├→ Same process
└→ Focus on workouts/cycles

Evening Sync (8 PM)
├→ Same process
└→ Fetch end-of-day data

Night Sync (11 PM)
├→ Final sync before next recovery score
└→ Ensure complete daily data
```

### User Requests Data (Anytime)

```
1. Flutter app requests data for specific date
   └→ GET /api/v1/whoop/daily-data/{user_id}?date=2025-01-20

2. Backend queries database FIRST
   ├→ SELECT * FROM whoop_recovery WHERE user_id=X AND DATE(created_at)='2025-01-20'
   ├→ SELECT * FROM whoop_sleep WHERE user_id=X AND DATE(end_time)='2025-01-20'
   ├→ SELECT * FROM whoop_workout WHERE user_id=X AND DATE(start_time)='2025-01-20'
   └→ SELECT * FROM whoop_cycle WHERE user_id=X AND DATE(start_time)='2025-01-20'

3. If data exists in database
   └→ Return immediately (FAST - no WHOOP API call)

4. If data missing
   └→ Check if date is recent (< 7 days ago)
   └→ If yes: trigger sync for that date range
   └→ If no: return empty (old data not worth fetching)

5. Return aggregated data to app
```

## API Endpoints

### Database-First Endpoints (NEW)

```python
# Primary endpoint - fetches from database, syncs if needed
GET /api/v1/whoop/daily-data/{user_id}?date=YYYY-MM-DD
Response:
{
  "date": "2025-01-20",
  "recovery": {...},      # From whoop_recovery table
  "sleep": {...},         # From whoop_sleep table
  "workouts": [{...}],    # From whoop_workout table
  "cycle": {...},         # From whoop_cycle table
  "last_sync": "2025-01-20T08:00:00Z",
  "data_source": "database"  # or "whoop_api" if freshly synced
}

# Explicit sync trigger (for manual refresh)
POST /api/v1/whoop/sync/{user_id}
Body: {
  "data_types": ["recovery", "sleep", "workout", "cycle"],  # optional
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-01-20"
  }
}
Response:
{
  "synced": {
    "recovery": 20,
    "sleep": 40,
    "workout": 15,
    "cycle": 20
  },
  "total_api_calls": 4
}

# Get sync status
GET /api/v1/whoop/sync-status/{user_id}
Response:
{
  "recovery": {
    "last_sync_at": "2025-01-20T08:00:00Z",
    "records_synced": 100,
    "status": "success"
  },
  "sleep": {...},
  "workout": {...},
  "cycle": {...}
}
```

## Incremental Sync Logic

### Preventing Duplicates

**Method 1: Primary Key (WHOOP Record ID)**

```python
# Each WHOOP record has a unique ID
record_id = "whoop-recovery-abc-123"

# Use UPSERT in database
INSERT INTO whoop_recovery (id, user_id, recovery_score, ...)
VALUES ('whoop-recovery-abc-123', 'user1', 85, ...)
ON CONFLICT (id) DO NOTHING;  # Skip if already exists
```

**Method 2: Check Last Sync Time**

```python
# Get last successful sync time
last_sync = get_last_sync_time(user_id, 'recovery')
# Example: 2025-01-20 08:00:00

# Only fetch records created after last sync
whoop_api.get_recovery(
    user_id=user_id,
    start_date=last_sync,  # Only new records
    end_date=datetime.now()
)
```

### Sync Algorithm

```python
async def incremental_sync(user_id: str, data_type: str):
    """
    Incremental sync algorithm
    """
    # 1. Get last sync time from database
    last_sync = await repository.get_last_sync_time(user_id, data_type)

    # 2. Determine date range to fetch
    if last_sync is None:
        # Initial sync - fetch last 30 days
        start_date = datetime.now() - timedelta(days=30)
    else:
        # Incremental sync - fetch only new data
        start_date = last_sync

    end_date = datetime.now()

    # 3. Fetch from WHOOP API
    records = await whoop_api.get_data(
        user_id=user_id,
        data_type=data_type,
        start_date=start_date,
        end_date=end_date
    )

    # 4. Store in database (duplicates automatically skipped)
    stored_count = await repository.store_records(user_id, data_type, records)

    # 5. Update sync log
    await repository.update_sync_log(
        user_id=user_id,
        data_type=data_type,
        records_synced=stored_count,
        status='success'
    )

    logger.info(f"Synced {stored_count} new {data_type} records for {user_id}")
```

## Scheduled Sync Implementation

### Option 1: Backend Cron Job (Recommended)

**Pros**: Centralized, consistent, works even if app is closed
**Cons**: Requires background worker setup

```python
# app/tasks/scheduled_sync.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=8, minute=0)  # 8:00 AM
async def morning_sync():
    """Morning sync - recovery + sleep"""
    active_users = await get_active_whoop_users()
    for user_id in active_users:
        await incremental_sync(user_id, 'recovery')
        await incremental_sync(user_id, 'sleep')

@scheduler.scheduled_job('cron', hour=14, minute=0)  # 2:00 PM
async def afternoon_sync():
    """Afternoon sync - workouts + cycles"""
    active_users = await get_active_whoop_users()
    for user_id in active_users:
        await incremental_sync(user_id, 'workout')
        await incremental_sync(user_id, 'cycle')

@scheduler.scheduled_job('cron', hour=20, minute=0)  # 8:00 PM
async def evening_sync():
    """Evening sync - workouts + cycles"""
    active_users = await get_active_whoop_users()
    for user_id in active_users:
        await incremental_sync(user_id, 'workout')
        await incremental_sync(user_id, 'cycle')

@scheduler.scheduled_job('cron', hour=23, minute=0)  # 11:00 PM
async def night_sync():
    """Final sync - all data types"""
    active_users = await get_active_whoop_users()
    for user_id in active_users:
        await incremental_sync(user_id, 'recovery')
        await incremental_sync(user_id, 'sleep')
        await incremental_sync(user_id, 'workout')
        await incremental_sync(user_id, 'cycle')

# Start scheduler
scheduler.start()
```

### Option 2: Flutter Background Sync

**Pros**: Simpler backend, user-centric
**Cons**: Doesn't work if app is closed, battery intensive

```dart
// Use WorkManager for Android, BackgroundTasks for iOS
import 'package:workmanager/workmanager.dart';

void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    // Trigger sync endpoint
    await WhoopService().triggerSync(userId);
    return Future.value(true);
  });
}

// Register periodic task (4x daily)
Workmanager().registerPeriodicTask(
  "whoop-sync",
  "whoopSyncTask",
  frequency: Duration(hours: 6),  // Every 6 hours
);
```

## Flutter App Changes

### Remove Mock Data

```dart
// OLD (with mock data fallback)
Future<void> _loadData() async {
  if (_selectedSource == DeviceSourceType.whoop && _isWhoopConnected) {
    await _loadWhoopData();
  } else {
    // Fallback to mock data ❌ REMOVE THIS
    setState(() {
      _scores = HealthScore.generateSampleScores();
    });
  }
}

// NEW (database-first, no mock)
Future<void> _loadData() async {
  if (!_isWhoopConnected) {
    // Show "Connect WHOOP" message
    setState(() {
      _scores = [];
      _showConnectPrompt = true;
    });
    return;
  }

  // Always fetch from backend (which checks database first)
  await _loadWhoopDataFromDatabase();
}

Future<void> _loadWhoopDataFromDatabase() async {
  try {
    // Backend will check database first, sync if needed
    final data = await _whoopService.getDailyData(
      userId: _userId,
      date: widget.selectedDate,
    );

    if (!data.hasData) {
      // No data in database for this date
      setState(() {
        _scores = [];
        _showNoDataMessage = true;
      });
      return;
    }

    setState(() {
      _scores = _convertWhoopDataToScores(data);
      _showNoDataMessage = false;
    });
  } catch (e) {
    // Show error, don't fallback to mock
    setState(() {
      _errorMessage = 'Failed to load data: $e';
    });
  }
}
```

### Add "Connect WHOOP" Prompt

```dart
Widget _buildConnectPrompt() {
  return Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.fitness_center, size: 64, color: AppColors.tertiaryText),
        SizedBox(height: 16),
        Text(
          'Connect your WHOOP device',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppColors.primaryText,
          ),
        ),
        SizedBox(height: 8),
        Text(
          'Tap the devices icon to get started',
          style: TextStyle(
            fontSize: 14,
            color: AppColors.secondaryText,
          ),
        ),
        SizedBox(height: 24),
        ElevatedButton(
          onPressed: () => _showDeviceConnectionModal(),
          child: Text('Connect WHOOP'),
        ),
      ],
    ),
  );
}
```

## Implementation Steps

### Phase 1: Database Setup ✅

1. ✅ Run migration: `migrations/002_whoop_data_tables.sql`
2. ✅ Verify tables created
3. ✅ Test helper functions

### Phase 2: Backend Implementation (NEXT)

1. Create `app/repositories/__init__.py`
2. Modify `app/services/whoop_service.py` to use repository
3. Add new database-first endpoints
4. Add sync trigger endpoint
5. Test with Postman/curl

### Phase 3: Sync Scheduler

1. Install `apscheduler`: `pip install apscheduler`
2. Create `app/tasks/scheduled_sync.py`
3. Start scheduler in `main.py`
4. Monitor logs for sync execution

### Phase 4: Flutter Updates

1. Remove all mock data fallbacks
2. Add "Connect WHOOP" UI
3. Add "No Data" UI for empty dates
4. Test with real WHOOP connection

### Phase 5: Testing

1. Connect WHOOP device
2. Trigger initial sync
3. Verify data in database
4. Check Flutter UI shows database data
5. Wait for scheduled sync
6. Verify incremental sync works

## Troubleshooting

### Issue: Duplicate Records

**Solution**: Check that WHOOP record IDs are being used as primary keys

```sql
-- Verify no duplicates
SELECT id, COUNT(*)
FROM whoop_recovery
GROUP BY id
HAVING COUNT(*) > 1;
```

### Issue: Sync Not Triggering

**Solution**: Check sync log status

```sql
-- Check sync log
SELECT * FROM whoop_sync_log
WHERE user_id = 'your_user_id'
ORDER BY last_sync_at DESC;
```

### Issue: Old Data Not Syncing

**Solution**: Manually trigger sync for specific date range

```bash
curl -X POST http://localhost:8009/api/v1/whoop/sync/user123 \
  -H "Content-Type: application/json" \
  -d '{
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-01-20"
    }
  }'
```

## Next Steps

See `IMPLEMENTATION_GUIDE.md` for step-by-step instructions on:
1. Running database migrations
2. Updating backend services
3. Testing the sync flow
4. Deploying to production

