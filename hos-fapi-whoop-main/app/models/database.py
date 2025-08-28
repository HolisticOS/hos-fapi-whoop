"""
Database models and Supabase integration for WHOOP microservice.
Provides comprehensive data access layer using Supabase client.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
import structlog
from supabase import Client
from postgrest.exceptions import APIError

from app.config.database import get_supabase_client
from app.models.schemas import (
    WhoopUser, WhoopRecoveryRecord, WhoopSleepRecord, 
    WhoopWorkoutRecord, WhoopSyncLog
)

logger = structlog.get_logger(__name__)


class WhoopUserRepository:
    """Repository for WHOOP user management"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_users"
    
    async def create_user(self, user_data: WhoopUser) -> Optional[WhoopUser]:
        """Create new WHOOP user connection"""
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            user_dict = user_data.model_dump(exclude_none=True)
            for key, value in user_dict.items():
                if isinstance(value, datetime):
                    user_dict[key] = value.isoformat()
            
            result = self.supabase.table(self.table_name).insert(user_dict).execute()
            
            if result.data:
                logger.info("✅ WHOOP user created", user_id=user_data.user_id)
                return WhoopUser(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to create WHOOP user", 
                        user_id=user_data.user_id, error=str(e))
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[WhoopUser]:
        """Get WHOOP user by internal user_id"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id  # Fixed: use internal user_id, not whoop_user_id
            ).execute()
            
            if result.data:
                return WhoopUser(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get WHOOP user", user_id=user_id, error=str(e))
            return None
    
    async def update_tokens(self, user_id: str, access_token: str, 
                          refresh_token: str, expires_at: datetime) -> bool:
        """Update user's OAuth tokens"""
        try:
            result = self.supabase.table(self.table_name).update({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expires_at": expires_at.isoformat() if expires_at else None,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()  # Fixed: use internal user_id
            
            logger.info("✅ WHOOP user tokens updated", user_id=user_id)
            return bool(result.data)
            
        except APIError as e:
            logger.error("❌ Failed to update WHOOP user tokens", 
                        user_id=user_id, error=str(e))
            return False
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate WHOOP user connection"""
        try:
            result = self.supabase.table(self.table_name).update({
                "is_active": False,
                "access_token": None,
                "refresh_token": None,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()  # Fixed: use internal user_id
            
            logger.info("✅ WHOOP user deactivated", user_id=user_id)
            return bool(result.data)
            
        except APIError as e:
            logger.error("❌ Failed to deactivate WHOOP user", 
                        user_id=user_id, error=str(e))
            return False


class WhoopRecoveryRepository:
    """Repository for WHOOP recovery data"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_recovery_data"
    
    async def upsert_recovery_data(self, recovery_data: WhoopRecoveryRecord) -> bool:
        """Upsert recovery data (insert or update if exists for user/date)"""
        try:
            result = self.supabase.table(self.table_name).upsert(
                recovery_data.model_dump(exclude_none=True),
                on_conflict="user_id,date"
            ).execute()
            
            logger.info("✅ Recovery data upserted", 
                       user_id=recovery_data.user_id, date=recovery_data.date)
            return bool(result.data)
            
        except APIError as e:
            logger.error("❌ Failed to upsert recovery data", 
                        user_id=recovery_data.user_id, error=str(e))
            return False
    
    async def get_recovery_data(self, user_id: str, start_date: date, 
                              end_date: date) -> List[WhoopRecoveryRecord]:
        """Get recovery data for date range"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).gte("date", start_date.isoformat()).lte(
                "date", end_date.isoformat()
            ).order("date", desc=True).execute()
            
            return [WhoopRecoveryRecord(**row) for row in result.data or []]
            
        except APIError as e:
            logger.error("❌ Failed to get recovery data", 
                        user_id=user_id, error=str(e))
            return []


class WhoopSleepRepository:
    """Repository for WHOOP sleep data"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_sleep_data"
    
    async def upsert_sleep_data(self, sleep_data: WhoopSleepRecord) -> bool:
        """Upsert sleep data (insert or update if exists for user/date)"""
        try:
            result = self.supabase.table(self.table_name).upsert(
                sleep_data.model_dump(exclude_none=True),
                on_conflict="user_id,date"
            ).execute()
            
            logger.info("✅ Sleep data upserted", 
                       user_id=sleep_data.user_id, date=sleep_data.date)
            return bool(result.data)
            
        except APIError as e:
            logger.error("❌ Failed to upsert sleep data", 
                        user_id=sleep_data.user_id, error=str(e))
            return False
    
    async def get_sleep_data(self, user_id: str, start_date: date, 
                           end_date: date) -> List[WhoopSleepRecord]:
        """Get sleep data for date range"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).gte("date", start_date.isoformat()).lte(
                "date", end_date.isoformat()
            ).order("date", desc=True).execute()
            
            return [WhoopSleepRecord(**row) for row in result.data or []]
            
        except APIError as e:
            logger.error("❌ Failed to get sleep data", 
                        user_id=user_id, error=str(e))
            return []


class WhoopWorkoutRepository:
    """Repository for WHOOP workout data"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_workout_data"
    
    async def create_workout_data(self, workout_data: WhoopWorkoutRecord) -> bool:
        """Create new workout data (multiple workouts per day allowed)"""
        try:
            result = self.supabase.table(self.table_name).insert(
                workout_data.model_dump(exclude_none=True)
            ).execute()
            
            logger.info("✅ Workout data created", 
                       user_id=workout_data.user_id, date=workout_data.date)
            return bool(result.data)
            
        except APIError as e:
            logger.error("❌ Failed to create workout data", 
                        user_id=workout_data.user_id, error=str(e))
            return False
    
    async def get_workout_data(self, user_id: str, start_date: date, 
                             end_date: date) -> List[WhoopWorkoutRecord]:
        """Get workout data for date range"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).gte("date", start_date.isoformat()).lte(
                "date", end_date.isoformat()
            ).order("date", desc=True).execute()
            
            return [WhoopWorkoutRecord(**row) for row in result.data or []]
            
        except APIError as e:
            logger.error("❌ Failed to get workout data", 
                        user_id=user_id, error=str(e))
            return []
    
    async def delete_workout_data_by_date(self, user_id: str, date: date) -> bool:
        """Delete all workout data for a specific date (for re-sync)"""
        try:
            result = self.supabase.table(self.table_name).delete().eq(
                "user_id", user_id
            ).eq("date", date.isoformat()).execute()
            
            logger.info("✅ Workout data deleted for re-sync", 
                       user_id=user_id, date=date)
            return True
            
        except APIError as e:
            logger.error("❌ Failed to delete workout data", 
                        user_id=user_id, error=str(e))
            return False


class WhoopSyncLogRepository:
    """Repository for sync tracking"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_sync_log"
    
    async def log_sync_attempt(self, sync_log: WhoopSyncLog) -> bool:
        """Log a sync attempt"""
        try:
            result = self.supabase.table(self.table_name).upsert(
                sync_log.model_dump(exclude_none=True),
                on_conflict="user_id,data_type,sync_date"
            ).execute()
            
            logger.info("✅ Sync attempt logged", 
                       user_id=sync_log.user_id, 
                       data_type=sync_log.data_type,
                       status=sync_log.status)
            return bool(result.data)
            
        except APIError as e:
            logger.error("❌ Failed to log sync attempt", 
                        user_id=sync_log.user_id, error=str(e))
            return False
    
    async def get_last_sync(self, user_id: str, data_type: str) -> Optional[WhoopSyncLog]:
        """Get last successful sync for user and data type"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).eq("data_type", data_type).eq(
                "status", "success"
            ).order("sync_date", desc=True).limit(1).execute()
            
            if result.data:
                return WhoopSyncLog(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get last sync", 
                        user_id=user_id, data_type=data_type, error=str(e))
            return None
    
    async def needs_sync(self, user_id: str, data_type: str, 
                        target_date: date) -> bool:
        """Check if sync is needed for specific date"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).eq("data_type", data_type).eq(
                "sync_date", target_date.isoformat()
            ).eq("status", "success").execute()
            
            # No successful sync record means we need to sync
            return len(result.data or []) == 0
            
        except APIError as e:
            logger.error("❌ Failed to check sync status", 
                        user_id=user_id, error=str(e))
            return True  # Assume sync needed on error


# Convenience class for unified data access
class WhoopDataService:
    """Unified service for all WHOOP data operations"""
    
    def __init__(self):
        self.users = WhoopUserRepository()
        self.recovery = WhoopRecoveryRepository()
        self.sleep = WhoopSleepRepository()
        self.workouts = WhoopWorkoutRepository()
        self.sync_logs = WhoopSyncLogRepository()
    
    async def get_comprehensive_health_data(self, user_id: str, 
                                          start_date: date, end_date: date) -> Dict[str, Any]:
        """Get all health data for user in date range"""
        try:
            # Fetch all data types concurrently
            recovery_data = await self.recovery.get_recovery_data(user_id, start_date, end_date)
            sleep_data = await self.sleep.get_sleep_data(user_id, start_date, end_date)
            workout_data = await self.workouts.get_workout_data(user_id, start_date, end_date)
            
            # Get last sync timestamps
            last_recovery_sync = await self.sync_logs.get_last_sync(user_id, "recovery")
            last_sleep_sync = await self.sync_logs.get_last_sync(user_id, "sleep")
            last_workout_sync = await self.sync_logs.get_last_sync(user_id, "workout")
            
            return {
                "user_id": user_id,
                "date_range": {"start": start_date, "end": end_date},
                "recovery": [r.model_dump() for r in recovery_data],
                "sleep": [s.model_dump() for s in sleep_data],
                "workouts": [w.model_dump() for w in workout_data],
                "last_sync": {
                    "recovery": last_recovery_sync.last_sync_at if last_recovery_sync else None,
                    "sleep": last_sleep_sync.last_sync_at if last_sleep_sync else None,
                    "workouts": last_workout_sync.last_sync_at if last_workout_sync else None
                },
                "record_counts": {
                    "recovery": len(recovery_data),
                    "sleep": len(sleep_data),
                    "workouts": len(workout_data)
                }
            }
            
        except Exception as e:
            logger.error("❌ Failed to get comprehensive health data", 
                        user_id=user_id, error=str(e))
            return {
                "user_id": user_id,
                "error": str(e),
                "recovery": [],
                "sleep": [],
                "workouts": []
            }