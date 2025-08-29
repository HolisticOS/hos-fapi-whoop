# WHOOP API v2 Migration Plan

## 🚨 CRITICAL DEADLINE: October 1, 2025 (35 days remaining)

**WHOOP API v1 Complete Removal:**
- All v1 endpoints will be permanently disabled
- All v1 webhooks will stop functioning  
- No grace period or backward compatibility
- Migration is MANDATORY for continued service

---

## Executive Summary

This migration plan addresses the mandatory transition from WHOOP API v1 to v2, focusing on the **primary breaking change: UUID identifiers** for Sleep and Workout resources. The migration includes database schema updates, API client modifications, and comprehensive testing procedures.

### Key Changes Required:
1. **Sleep Resources**: Integer IDs → UUID identifiers
2. **Workout Resources**: Integer IDs → UUID identifiers  
3. **Database Schema**: Add UUID columns with backward compatibility
4. **API Client**: Update base URLs from `/v1/` to `/v2/`
5. **Webhook Processing**: Handle UUID identifiers in webhook events

---

## Phase 1: Configuration and Infrastructure Updates

### 1.1 Environment Configuration Updates

**File: `app/config/settings.py`**
```python
# Update base URL configuration
WHOOP_API_BASE_URL = "https://api.prod.whoop.com/developer/v2/"  # Changed from /v1/

# Add v2-specific configurations
WHOOP_API_VERSION = "v2"
WHOOP_SUPPORTS_UUIDS = True
WHOOP_BACKWARD_COMPATIBILITY = True  # During migration period
```

**File: `.env`**
```env
# Update environment variables
WHOOP_API_VERSION=v2
WHOOP_API_BASE_URL=https://api.prod.whoop.com/developer/v2/
```

### 1.2 API Client Base URL Updates

**File: `app/services/whoop_service.py`**
```python
class WhoopService:
    def __init__(self):
        self.base_url = "https://api.prod.whoop.com/developer/v2/"  # Updated
        self.session = httpx.AsyncClient(timeout=30.0)
    
    # Update all endpoint methods to use v2 URLs
    async def get_sleep_data(self, start_date: str, end_date: str, next_token: str = None):
        """Updated for v2 API with UUID support"""
        url = f"{self.base_url}activity/sleep"  # v2 endpoint
        # Rest of implementation handles UUID responses
```

---

## Phase 2: Database Schema Migration

### 2.1 Execute v2 Migration Script

The comprehensive migration script has already been created: `migrations/002_whoop_v2_migration.sql`

**Key Migration Features:**
- Creates backup tables before migration
- Adds UUID columns to existing tables
- Creates new v2-specific tables with UUID support
- Maintains backward compatibility with v1 integer IDs
- Includes migration helper functions

**Execute Migration:**
```bash
# Apply the migration script to your database
psql -d your_database -f migrations/002_whoop_v2_migration.sql
```

### 2.2 New Database Tables Created

1. **`whoop_data_v2`**: Unified data storage with UUID support
2. **`whoop_sleep_v2`**: Sleep data with UUID identifiers
3. **`whoop_workout_v2`**: Workout data with UUID identifiers  
4. **`whoop_recovery_v2`**: Recovery data (structure unchanged)
5. **`whoop_migration_log`**: Migration tracking and audit

### 2.3 Backward Compatibility Strategy

The migration maintains both v1 and v2 identifiers:
```sql
-- Sleep table structure example
CREATE TABLE whoop_sleep_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    sleep_uuid TEXT UNIQUE NOT NULL,        -- v2 UUID identifier
    sleep_v1_id INTEGER,                    -- v1 integer ID preserved
    -- other columns...
);
```

---

## Phase 3: API Client Implementation Updates

### 3.1 Update Data Models for UUID Support

**File: `app/models/whoop_models.py`**
```python
from pydantic import BaseModel, Field
from typing import Optional
import uuid

class SleepDataV2(BaseModel):
    """v2 Sleep data model with UUID support"""
    id: str = Field(..., description="UUID identifier")
    activity_v1_id: Optional[int] = Field(None, description="Backward compatibility v1 ID")
    user_id: int
    start: str
    end: str
    timezone_offset: Optional[str] = None
    # Sleep metrics...
    total_sleep_time_milli: Optional[int] = None
    sleep_efficiency: Optional[float] = None
    # Raw data storage
    raw_data: dict = Field(default_factory=dict)

class WorkoutDataV2(BaseModel):
    """v2 Workout data model with UUID support"""
    id: str = Field(..., description="UUID identifier") 
    activity_v1_id: Optional[int] = Field(None, description="Backward compatibility v1 ID")
    user_id: int
    sport_id: int
    start: str
    end: str
    strain: Optional[float] = None
    # Performance metrics...
    average_heart_rate: Optional[int] = None
    calories: Optional[int] = None
    # Raw data storage
    raw_data: dict = Field(default_factory=dict)
```

### 3.2 Update API Service Methods

**File: `app/services/whoop_service.py`**
```python
class WhoopService:
    async def get_sleep_data_v2(self, start_date: str, end_date: str, next_token: str = None):
        """Fetch sleep data from v2 API with UUID handling"""
        url = f"{self.base_url}activity/sleep"
        
        params = {
            "start": start_date,
            "end": end_date
        }
        
        if next_token:
            params["nextToken"] = next_token
            
        response = await self._make_request("GET", url, params=params)
        
        # Process v2 response with UUIDs
        sleep_records = []
        for record in response.get("records", []):
            sleep_data = SleepDataV2(
                id=record["id"],  # This is now a UUID
                activity_v1_id=record.get("activityV1Id"),  # Backward compatibility
                user_id=record["userId"],
                start=record["start"],
                end=record["end"],
                timezone_offset=record.get("timezoneOffset"),
                # Map all other fields...
                raw_data=record
            )
            sleep_records.append(sleep_data)
            
        return {
            "records": sleep_records,
            "next_token": response.get("next_token")
        }
    
    async def get_workout_data_v2(self, start_date: str, end_date: str, next_token: str = None):
        """Fetch workout data from v2 API with UUID handling"""
        url = f"{self.base_url}activity/workout"
        
        params = {
            "start": start_date, 
            "end": end_date
        }
        
        if next_token:
            params["nextToken"] = next_token
            
        response = await self._make_request("GET", url, params=params)
        
        # Process v2 response with UUIDs
        workout_records = []
        for record in response.get("records", []):
            workout_data = WorkoutDataV2(
                id=record["id"],  # This is now a UUID
                activity_v1_id=record.get("activityV1Id"),  # Backward compatibility
                user_id=record["userId"],
                sport_id=record["sportId"],
                start=record["start"],
                end=record["end"],
                strain=record.get("strain"),
                # Map all other fields...
                raw_data=record
            )
            workout_records.append(workout_data)
            
        return {
            "records": workout_records,
            "next_token": response.get("next_token")
        }
```

### 3.3 UUID Validation Utilities

**File: `app/utils/uuid_utils.py`**
```python
import uuid
from typing import Union, Optional
import re

def is_valid_uuid(uuid_string: str) -> bool:
    """Validate UUID format"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError):
        return False

def normalize_whoop_id(whoop_id: Union[str, int]) -> dict:
    """Normalize WHOOP ID to support both v1 and v2 formats"""
    if isinstance(whoop_id, int):
        # v1 integer ID
        return {
            "uuid": None,
            "v1_id": whoop_id,
            "version": "v1"
        }
    elif isinstance(whoop_id, str) and is_valid_uuid(whoop_id):
        # v2 UUID
        return {
            "uuid": whoop_id,
            "v1_id": None, 
            "version": "v2"
        }
    else:
        raise ValueError(f"Invalid WHOOP ID format: {whoop_id}")

def convert_v1_response_to_v2(v1_data: dict) -> dict:
    """Convert v1 response format to v2-compatible format"""
    # This is for migration period compatibility
    v2_data = v1_data.copy()
    if "id" in v1_data and isinstance(v1_data["id"], int):
        v2_data["activityV1Id"] = v1_data["id"]
        v2_data["id"] = str(uuid.uuid4())  # Generate UUID for compatibility
    return v2_data
```

---

## Phase 4: Database Repository Updates

### 4.1 Update Repository Classes for UUID Support

**File: `app/models/database.py`**
```python
class SleepRepository:
    async def store_sleep_data_v2(self, user_id: str, sleep_data: SleepDataV2):
        """Store v2 sleep data with UUID support"""
        query = """
        INSERT INTO whoop_sleep_v2 (
            user_id, sleep_uuid, sleep_v1_id, start_time, end_time,
            timezone_offset, total_sleep_time_milli, sleep_efficiency,
            raw_data, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW()
        ) ON CONFLICT (sleep_uuid) 
        DO UPDATE SET
            sleep_v1_id = EXCLUDED.sleep_v1_id,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            raw_data = EXCLUDED.raw_data,
            updated_at = NOW()
        RETURNING id;
        """
        
        return await self.db.fetchval(
            query,
            user_id,
            sleep_data.id,  # UUID
            sleep_data.activity_v1_id,  # v1 ID for compatibility
            sleep_data.start,
            sleep_data.end,
            sleep_data.timezone_offset,
            sleep_data.total_sleep_time_milli,
            sleep_data.sleep_efficiency,
            sleep_data.raw_data
        )
    
    async def get_sleep_by_uuid(self, sleep_uuid: str):
        """Retrieve sleep data by UUID"""
        query = """
        SELECT * FROM whoop_sleep_v2 
        WHERE sleep_uuid = $1;
        """
        return await self.db.fetchrow(query, sleep_uuid)
    
    async def get_sleep_by_v1_id(self, v1_id: int):
        """Retrieve sleep data by v1 ID for backward compatibility"""
        query = """
        SELECT * FROM whoop_sleep_v2 
        WHERE sleep_v1_id = $1;
        """
        return await self.db.fetchrow(query, v1_id)

class WorkoutRepository:
    async def store_workout_data_v2(self, user_id: str, workout_data: WorkoutDataV2):
        """Store v2 workout data with UUID support"""
        query = """
        INSERT INTO whoop_workout_v2 (
            user_id, workout_uuid, workout_v1_id, sport_id, start_time, end_time,
            timezone_offset, strain_score, average_heart_rate, max_heart_rate,
            calories_burned, raw_data, created_at, updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW()
        ) ON CONFLICT (workout_uuid)
        DO UPDATE SET
            workout_v1_id = EXCLUDED.workout_v1_id,
            sport_id = EXCLUDED.sport_id,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            strain_score = EXCLUDED.strain_score,
            raw_data = EXCLUDED.raw_data,
            updated_at = NOW()
        RETURNING id;
        """
        
        return await self.db.fetchval(
            query,
            user_id,
            workout_data.id,  # UUID
            workout_data.activity_v1_id,  # v1 ID for compatibility
            workout_data.sport_id,
            workout_data.start,
            workout_data.end,
            workout_data.timezone_offset,
            workout_data.strain,
            workout_data.average_heart_rate,
            workout_data.max_heart_rate,
            workout_data.calories,
            workout_data.raw_data
        )
```

---

## Phase 5: Complete Database Storage Implementation

### 5.1 Fix TODO in Sync Endpoint

**File: `app/api/internal.py` (Lines 426-428)**

Replace the current TODO with complete v2 implementation:

```python
@router.post("/sync")
async def sync_whoop_data(current_user: dict = Depends(get_current_user)):
    """
    Sync WHOOP data for the current user using v2 API
    """
    try:
        user_id = current_user["id"]
        
        # Initialize repositories
        sleep_repo = SleepRepository()
        workout_repo = WorkoutRepository()
        recovery_repo = RecoveryRepository()
        sync_repo = SyncRepository()
        
        # Initialize WHOOP service
        whoop_service = WhoopService()
        
        # Get date range for sync (last 30 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        sync_results = {
            "sleep": {"synced": 0, "errors": []},
            "workouts": {"synced": 0, "errors": []},
            "recovery": {"synced": 0, "errors": []}
        }
        
        # Create sync job record
        sync_job = await sync_repo.create_sync_job(user_id, "manual", "whoop_v2")
        
        try:
            # Sync Sleep Data with v2 API
            logger.info(f"🛏️ Syncing sleep data for user {user_id}")
            sleep_response = await whoop_service.get_sleep_data_v2(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            for sleep_record in sleep_response["records"]:
                try:
                    await sleep_repo.store_sleep_data_v2(user_id, sleep_record)
                    sync_results["sleep"]["synced"] += 1
                    logger.info(f"✅ Stored sleep record: {sleep_record.id}")
                except Exception as e:
                    logger.error(f"❌ Failed to store sleep record {sleep_record.id}: {e}")
                    sync_results["sleep"]["errors"].append(str(e))
            
            # Sync Workout Data with v2 API  
            logger.info(f"💪 Syncing workout data for user {user_id}")
            workout_response = await whoop_service.get_workout_data_v2(
                start_date.isoformat(), 
                end_date.isoformat()
            )
            
            for workout_record in workout_response["records"]:
                try:
                    await workout_repo.store_workout_data_v2(user_id, workout_record)
                    sync_results["workouts"]["synced"] += 1
                    logger.info(f"✅ Stored workout record: {workout_record.id}")
                except Exception as e:
                    logger.error(f"❌ Failed to store workout record {workout_record.id}: {e}")
                    sync_results["workouts"]["errors"].append(str(e))
            
            # Sync Recovery Data (unchanged structure)
            logger.info(f"❤️ Syncing recovery data for user {user_id}")
            recovery_response = await whoop_service.get_recovery_data(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            for recovery_record in recovery_response["records"]:
                try:
                    await recovery_repo.store_recovery_data(user_id, recovery_record)
                    sync_results["recovery"]["synced"] += 1
                    logger.info(f"✅ Stored recovery record: {recovery_record['cycle']['id']}")
                except Exception as e:
                    logger.error(f"❌ Failed to store recovery record: {e}")
                    sync_results["recovery"]["errors"].append(str(e))
            
            # Update sync job as completed
            await sync_repo.complete_sync_job(
                sync_job["id"], 
                "completed",
                sync_results
            )
            
            return {
                "status": "success",
                "message": "WHOOP data synchronized successfully",
                "results": sync_results,
                "sync_job_id": sync_job["id"]
            }
            
        except Exception as e:
            # Update sync job as failed
            await sync_repo.complete_sync_job(
                sync_job["id"],
                "failed", 
                {"error": str(e)}
            )
            raise
            
    except Exception as e:
        logger.error(f"❌ Sync failed for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync WHOOP data: {str(e)}"
        )
```

---

## Phase 6: Webhook Updates for v2

### 6.1 Update Webhook Processing for UUIDs

**File: `app/api/webhooks.py`**
```python
@router.post("/whoop/webhook")
async def handle_whoop_webhook(
    request: Request,
    webhook_data: dict = Body(...)
):
    """
    Handle WHOOP v2 webhook events with UUID identifiers
    """
    try:
        # Verify webhook signature (unchanged)
        await verify_whoop_webhook_signature(request)
        
        event_type = webhook_data.get("type")
        resource_id = webhook_data.get("id")  # Now UUID in v2
        user_id = webhook_data.get("user_id")
        
        logger.info(f"📨 Received WHOOP v2 webhook: {event_type} for resource {resource_id}")
        
        if event_type == "sleep.updated":
            await handle_sleep_webhook_v2(user_id, resource_id)
        elif event_type == "workout.created" or event_type == "workout.updated":
            await handle_workout_webhook_v2(user_id, resource_id)
        elif event_type == "recovery.updated":
            await handle_recovery_webhook_v2(user_id, resource_id)
        else:
            logger.warning(f"⚠️ Unknown webhook event type: {event_type}")
        
        return {"status": "success", "message": "Webhook processed"}
        
    except Exception as e:
        logger.error(f"❌ Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def handle_sleep_webhook_v2(user_id: int, sleep_uuid: str):
    """Handle sleep webhook with UUID identifier"""
    try:
        # Validate UUID format
        if not is_valid_uuid(sleep_uuid):
            raise ValueError(f"Invalid sleep UUID: {sleep_uuid}")
        
        whoop_service = WhoopService()
        sleep_repo = SleepRepository()
        
        # Fetch specific sleep record by UUID
        sleep_data = await whoop_service.get_sleep_by_uuid(sleep_uuid)
        
        if sleep_data:
            # Store/update in database
            await sleep_repo.store_sleep_data_v2(user_id, sleep_data)
            logger.info(f"✅ Updated sleep record from webhook: {sleep_uuid}")
        else:
            logger.warning(f"⚠️ Sleep record not found: {sleep_uuid}")
            
    except Exception as e:
        logger.error(f"❌ Failed to handle sleep webhook: {e}")
        raise

async def handle_workout_webhook_v2(user_id: int, workout_uuid: str):
    """Handle workout webhook with UUID identifier"""
    try:
        # Validate UUID format
        if not is_valid_uuid(workout_uuid):
            raise ValueError(f"Invalid workout UUID: {workout_uuid}")
        
        whoop_service = WhoopService()
        workout_repo = WorkoutRepository()
        
        # Fetch specific workout record by UUID
        workout_data = await whoop_service.get_workout_by_uuid(workout_uuid)
        
        if workout_data:
            # Store/update in database
            await workout_repo.store_workout_data_v2(user_id, workout_data)
            logger.info(f"✅ Updated workout record from webhook: {workout_uuid}")
        else:
            logger.warning(f"⚠️ Workout record not found: {workout_uuid}")
            
    except Exception as e:
        logger.error(f"❌ Failed to handle workout webhook: {e}")
        raise
```

---

## Phase 7: Migration and Data Transition

### 7.1 Data Migration Utilities

**File: `app/utils/migration_utils.py`**
```python
from app.models.database import SleepRepository, WorkoutRepository
from app.services.whoop_service import WhoopService
import asyncio
import logging

logger = logging.getLogger(__name__)

class WhoopV2Migrator:
    def __init__(self):
        self.sleep_repo = SleepRepository()
        self.workout_repo = WorkoutRepository()
        self.whoop_service = WhoopService()
    
    async def migrate_user_data(self, user_id: str, days_back: int = 90):
        """
        Migrate user's historical data to v2 format
        """
        logger.info(f"🔄 Starting v2 migration for user {user_id}")
        
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)
            
            migration_results = {
                "sleep_migrated": 0,
                "workout_migrated": 0,
                "errors": []
            }
            
            # Migrate Sleep Data
            logger.info(f"🛏️ Migrating sleep data for user {user_id}")
            await self._migrate_sleep_data(user_id, start_date, end_date, migration_results)
            
            # Migrate Workout Data
            logger.info(f"💪 Migrating workout data for user {user_id}")
            await self._migrate_workout_data(user_id, start_date, end_date, migration_results)
            
            # Log migration summary
            logger.info(f"✅ Migration completed for user {user_id}: {migration_results}")
            
            return migration_results
            
        except Exception as e:
            logger.error(f"❌ Migration failed for user {user_id}: {e}")
            raise
    
    async def _migrate_sleep_data(self, user_id: str, start_date, end_date, results):
        """Migrate sleep data to v2 format"""
        try:
            sleep_response = await self.whoop_service.get_sleep_data_v2(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            for sleep_record in sleep_response["records"]:
                try:
                    await self.sleep_repo.store_sleep_data_v2(user_id, sleep_record)
                    results["sleep_migrated"] += 1
                except Exception as e:
                    error_msg = f"Failed to migrate sleep record {sleep_record.id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Failed to fetch sleep data for migration: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
    
    async def _migrate_workout_data(self, user_id: str, start_date, end_date, results):
        """Migrate workout data to v2 format"""
        try:
            workout_response = await self.whoop_service.get_workout_data_v2(
                start_date.isoformat(),
                end_date.isoformat()
            )
            
            for workout_record in workout_response["records"]:
                try:
                    await self.workout_repo.store_workout_data_v2(user_id, workout_record)
                    results["workout_migrated"] += 1
                except Exception as e:
                    error_msg = f"Failed to migrate workout record {workout_record.id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Failed to fetch workout data for migration: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

# Migration CLI Command
async def migrate_all_users():
    """Migration command to update all users to v2"""
    migrator = WhoopV2Migrator()
    
    # Get all active users
    user_repo = UserRepository()
    users = await user_repo.get_all_active_users()
    
    logger.info(f"🔄 Starting v2 migration for {len(users)} users")
    
    for user in users:
        try:
            await migrator.migrate_user_data(user["id"])
            await asyncio.sleep(1)  # Rate limiting
        except Exception as e:
            logger.error(f"❌ Failed to migrate user {user['id']}: {e}")
    
    logger.info("✅ Migration completed for all users")

if __name__ == "__main__":
    asyncio.run(migrate_all_users())
```

### 7.2 Migration Command Endpoint

**File: `app/api/admin.py`**
```python
@router.post("/migrate/v2/{user_id}")
async def migrate_user_to_v2(
    user_id: str,
    days_back: int = 90,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Admin endpoint to migrate specific user to v2
    """
    try:
        migrator = WhoopV2Migrator()
        results = await migrator.migrate_user_data(user_id, days_back)
        
        return {
            "status": "success",
            "message": f"User {user_id} migrated to v2",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )
```

---

## Phase 8: Testing and Validation

### 8.1 Comprehensive Testing Suite

**File: `tests/test_whoop_v2_migration.py`**
```python
import pytest
import asyncio
from app.services.whoop_service import WhoopService
from app.models.whoop_models import SleepDataV2, WorkoutDataV2
from app.utils.uuid_utils import is_valid_uuid, normalize_whoop_id
from app.utils.migration_utils import WhoopV2Migrator

class TestWhoopV2Migration:
    
    @pytest.fixture
    async def whoop_service(self):
        return WhoopService()
    
    async def test_v2_api_connectivity(self, whoop_service):
        """Test v2 API base URL and connectivity"""
        assert whoop_service.base_url == "https://api.prod.whoop.com/developer/v2/"
        
        # Test API connectivity with a simple request
        try:
            response = await whoop_service._make_request("GET", "user/profile/basic")
            assert response is not None
        except Exception as e:
            pytest.fail(f"v2 API connectivity failed: {e}")
    
    async def test_sleep_data_v2_format(self, whoop_service):
        """Test sleep data returns UUID identifiers"""
        sleep_response = await whoop_service.get_sleep_data_v2(
            "2024-08-01T00:00:00Z",
            "2024-08-02T00:00:00Z"
        )
        
        assert "records" in sleep_response
        
        for record in sleep_response["records"]:
            # Verify UUID format
            assert is_valid_uuid(record.id), f"Invalid UUID format: {record.id}"
            
            # Verify backward compatibility field exists
            assert hasattr(record, 'activity_v1_id'), "Missing activityV1Id field"
            
            # Verify required fields
            assert record.user_id is not None
            assert record.start is not None
            assert record.end is not None
    
    async def test_workout_data_v2_format(self, whoop_service):
        """Test workout data returns UUID identifiers"""
        workout_response = await whoop_service.get_workout_data_v2(
            "2024-08-01T00:00:00Z", 
            "2024-08-02T00:00:00Z"
        )
        
        assert "records" in workout_response
        
        for record in workout_response["records"]:
            # Verify UUID format
            assert is_valid_uuid(record.id), f"Invalid UUID format: {record.id}"
            
            # Verify backward compatibility field exists
            assert hasattr(record, 'activity_v1_id'), "Missing activityV1Id field"
            
            # Verify required fields
            assert record.user_id is not None
            assert record.sport_id is not None
            assert record.start is not None
            assert record.end is not None
    
    def test_uuid_validation_utilities(self):
        """Test UUID validation functions"""
        # Valid UUIDs
        valid_uuid = "ecfc6a15-4661-442f-a9a4-f160dd7afae8"
        assert is_valid_uuid(valid_uuid) == True
        
        # Invalid UUIDs
        invalid_uuid = "not-a-uuid"
        assert is_valid_uuid(invalid_uuid) == False
        
        # Test normalize_whoop_id function
        v1_result = normalize_whoop_id(12345)
        assert v1_result["version"] == "v1"
        assert v1_result["v1_id"] == 12345
        assert v1_result["uuid"] is None
        
        v2_result = normalize_whoop_id(valid_uuid)
        assert v2_result["version"] == "v2"
        assert v2_result["uuid"] == valid_uuid
        assert v2_result["v1_id"] is None
    
    async def test_database_uuid_storage(self):
        """Test database can store and retrieve UUID identifiers"""
        from app.models.database import SleepRepository
        
        sleep_repo = SleepRepository()
        
        # Create test sleep data
        test_sleep = SleepDataV2(
            id="ecfc6a15-4661-442f-a9a4-f160dd7afae8",
            activity_v1_id=12345,
            user_id=1,
            start="2024-08-28T23:30:00Z",
            end="2024-08-29T07:30:00Z",
            raw_data={"test": "data"}
        )
        
        # Store in database
        record_id = await sleep_repo.store_sleep_data_v2("user_123", test_sleep)
        assert record_id is not None
        
        # Retrieve by UUID
        retrieved = await sleep_repo.get_sleep_by_uuid(test_sleep.id)
        assert retrieved is not None
        assert retrieved["sleep_uuid"] == test_sleep.id
        
        # Retrieve by v1 ID (backward compatibility)
        retrieved_v1 = await sleep_repo.get_sleep_by_v1_id(test_sleep.activity_v1_id)
        assert retrieved_v1 is not None
        assert retrieved_v1["sleep_v1_id"] == test_sleep.activity_v1_id
    
    async def test_migration_functionality(self):
        """Test data migration from v1 to v2"""
        migrator = WhoopV2Migrator()
        
        # Test migration for specific user
        results = await migrator.migrate_user_data("test_user", days_back=7)
        
        assert "sleep_migrated" in results
        assert "workout_migrated" in results  
        assert "errors" in results
        
        # Verify counts are reasonable
        assert isinstance(results["sleep_migrated"], int)
        assert isinstance(results["workout_migrated"], int)
        assert isinstance(results["errors"], list)

# Integration test for complete workflow
class TestWhoopV2Integration:
    
    async def test_complete_sync_workflow(self):
        """Test complete sync workflow with v2 API"""
        from app.api.internal import sync_whoop_data
        
        # Mock current user
        mock_user = {"id": "test_user_123"}
        
        # This should work without errors in v2
        try:
            result = await sync_whoop_data(current_user=mock_user)
            assert result["status"] == "success"
            assert "results" in result
            assert "sync_job_id" in result
        except Exception as e:
            pytest.fail(f"Complete sync workflow failed: {e}")
    
    async def test_webhook_processing_v2(self):
        """Test webhook processing handles UUID identifiers"""
        from app.api.webhooks import handle_sleep_webhook_v2
        
        test_uuid = "ecfc6a15-4661-442f-a9a4-f160dd7afae8"
        test_user_id = 12345
        
        try:
            await handle_sleep_webhook_v2(test_user_id, test_uuid)
            # If no exception, webhook processing succeeded
        except Exception as e:
            # Acceptable if record not found, but should handle UUID properly
            assert "Invalid" not in str(e), f"UUID validation failed: {e}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 8.2 Manual Testing Checklist

**Create file: `tests/manual_testing_checklist.md`**
```markdown
# WHOOP API v2 Manual Testing Checklist

## Pre-Migration Testing
- [ ] Verify v1 API still functional before migration
- [ ] Backup existing database
- [ ] Test database migration script on staging environment
- [ ] Verify all environment variables updated

## v2 API Connectivity Testing
- [ ] Test OAuth authentication with v2 endpoints
- [ ] Verify base URL change to `/v2/`
- [ ] Test rate limiting behavior (unchanged)
- [ ] Verify token validation still works

## UUID Identifier Testing
- [ ] Fetch sleep data and verify UUID format in response
- [ ] Fetch workout data and verify UUID format in response  
- [ ] Verify `activityV1Id` field present for backward compatibility
- [ ] Test UUID validation utilities

## Database Testing
- [ ] Verify new v2 tables created successfully
- [ ] Test storing sleep data with UUID identifiers
- [ ] Test storing workout data with UUID identifiers
- [ ] Test querying by UUID
- [ ] Test querying by v1 ID (backward compatibility)
- [ ] Verify migration function works correctly

## Sync Endpoint Testing
- [ ] Test complete sync workflow with v2 API
- [ ] Verify data is stored in v2 tables
- [ ] Check sync job tracking
- [ ] Verify error handling for failed syncs

## Webhook Testing
- [ ] Update webhook URL to v2 version in WHOOP dashboard
- [ ] Test webhook signature verification (unchanged)
- [ ] Test sleep webhook with UUID identifier
- [ ] Test workout webhook with UUID identifier
- [ ] Test recovery webhook (minimal changes)

## Integration Testing
- [ ] Test OAuth → Sync → Webhook complete workflow
- [ ] Verify no data loss during migration
- [ ] Test backward compatibility with existing data
- [ ] Verify performance impact is minimal
- [ ] Test error scenarios and recovery

## Production Readiness
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Monitoring and logging in place
- [ ] Rollback procedures tested
- [ ] Team trained on v2 changes
```

---

## Timeline and Execution Schedule

### Week 1 (Days 1-7): Foundation
- **Day 1**: Execute database migration script
- **Day 2-3**: Update configuration and base URLs  
- **Day 4-5**: Implement UUID utilities and validation
- **Day 6-7**: Update API client methods

### Week 2 (Days 8-14): Implementation  
- **Day 8-10**: Update database repositories with UUID support
- **Day 11-12**: Complete sync endpoint implementation (fix TODO)
- **Day 13-14**: Update webhook processing for UUIDs

### Week 3 (Days 15-21): Migration & Testing
- **Day 15-17**: Implement migration utilities
- **Day 18-19**: Run comprehensive testing suite
- **Day 20-21**: Manual testing and validation

### Week 4 (Days 22-28): Production Deployment
- **Day 22-24**: Deploy to staging environment
- **Day 25-26**: Final validation and performance testing  
- **Day 27-28**: Production deployment

### Week 5 (Days 29-35): Buffer & Monitoring
- **Day 29-32**: Monitor production system
- **Day 33-34**: Address any issues found
- **Day 35**: Final readiness before October 1 deadline

---

## Risk Mitigation and Rollback Plan

### High-Risk Areas
1. **UUID Parsing Errors**: Implement comprehensive validation
2. **Database Migration Issues**: Test thoroughly on staging first
3. **Webhook Event Loss**: Implement event replay mechanism
4. **Performance Impact**: Monitor response times closely

### Rollback Procedures
If migration fails:
1. **Immediate**: Revert base URLs to v1 endpoints
2. **Database**: Use backup tables created during migration
3. **Code**: Rollback to pre-migration commit
4. **Webhooks**: Revert webhook URL to v1 in WHOOP dashboard

**Note**: After October 1, 2025, rollback to v1 is NOT possible as the API will be removed.

---

## Success Metrics

### Technical Metrics
- [ ] 100% v1 endpoint elimination - No remaining v1 API calls
- [ ] Zero data loss - All historical data preserved and accessible  
- [ ] UUID validation - All sleep/workout identifiers properly formatted
- [ ] Webhook reliability - All events processed successfully
- [ ] Performance maintenance - No degradation in response times

### Business Metrics
- [ ] Service continuity - No service interruptions during migration
- [ ] User experience - No impact on user-facing functionality
- [ ] Timeline adherence - Migration completed before October 1, 2025

---

## Post-Migration Tasks

### Monitoring Setup
- Set up UUID format validation alerts
- Monitor v2 webhook event processing rates  
- Track v2 API response times and error rates
- Alert on any remaining v1 endpoint usage

### Documentation Updates
- Update API integration documentation
- Revise troubleshooting guides for UUID identifiers
- Update webhook event handling procedures
- Document migration lessons learned

### Cleanup Tasks (After 30-day validation period)
- Remove v1 compatibility code
- Drop backup tables
- Clean up migration utilities
- Update monitoring dashboards

---

## Emergency Support

### If Issues Arise During Migration
1. **Contact WHOOP Developer Support**: https://developer.whoop.com/docs/developing/support/
2. **Review Migration Logs**: Check all error messages and stack traces
3. **Use Backup Data**: Restore from pre-migration backup if necessary
4. **Community Support**: Stack Overflow tags: `whoop-api`, `api-migration`

### After October 1, 2025
- v1 API will be unavailable - no rollback option
- Focus on fixing v2 integration issues
- Use backup data for service restoration if needed

---

## Conclusion

This comprehensive migration plan addresses the mandatory transition to WHOOP API v2 before the **October 1, 2025 deadline**. The plan focuses on the critical breaking change of UUID identifiers for Sleep and Workout resources while maintaining backward compatibility during the transition period.

**Next Immediate Actions:**
1. ✅ Database schema migration (completed)
2. 🔄 Execute Phase 3: API client implementation updates
3. 🔄 Complete database storage implementation (fix TODO)
4. 🔄 Begin testing and validation procedures

The migration must be completed within the next 35 days to ensure continued WHOOP integration functionality.