"""
Database repositories for WHOOP API with UUID support
Handles UUID identifiers for Sleep and Workout resources
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
import structlog
from supabase import Client
from postgrest.exceptions import APIError

from app.config.database import get_supabase_client
from app.models.schemas import (
    WhoopSleepRecord, WhoopWorkoutRecord, WhoopRecoveryRecord,
    WhoopMigrationMapping
)
from app.utils.uuid_utils import is_valid_uuid, normalize_whoop_id

logger = structlog.get_logger(__name__)


class WhoopSleepRepository:
    """Repository for WHOOP sleep data with UUID support"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_sleep_v2"
    
    async def store_sleep_data(self, user_id: str, sleep_data) -> Optional[str]:
        """
        Store sleep data with UUID support
        
        Args:
            user_id: Internal user identifier
            sleep_data: WhoopSleepData instance
            
        Returns:
            Database record ID if successful, None otherwise
        """
        try:
            # Validate UUID format
            if not is_valid_uuid(sleep_data.id):
                logger.error("Invalid sleep UUID format", 
                           sleep_uuid=sleep_data.id, user_id=user_id)
                return None
            
            # Convert datetime strings to datetime objects
            start_time = sleep_data.start_datetime
            end_time = sleep_data.end_datetime
            
            record_data = {
                "user_id": user_id,
                "sleep_uuid": sleep_data.id,
                "sleep_v1_id": sleep_data.activity_v1_id,
                "cycle_id": sleep_data.cycle_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "timezone_offset": sleep_data.timezone_offset,
                "total_sleep_time_milli": sleep_data.total_sleep_time_milli,
                "time_in_bed_milli": sleep_data.time_in_bed_milli,
                "raw_data": sleep_data.raw_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Extract sleep stages if available
            if sleep_data.sleep_stages:
                record_data.update({
                    "awake_time_milli": sleep_data.sleep_stages.awake_time_milli,
                    "light_sleep_milli": sleep_data.sleep_stages.light_sleep_milli,
                    "slow_wave_sleep_milli": sleep_data.sleep_stages.slow_wave_sleep_milli,
                    "rem_sleep_milli": sleep_data.sleep_stages.rem_sleep_milli
                })
            
            # Extract sleep scores if available
            if sleep_data.sleep_score:
                record_data.update({
                    "sleep_efficiency": sleep_data.sleep_score.sleep_efficiency,
                    "sleep_consistency": sleep_data.sleep_score.sleep_consistency,
                    "sleep_performance_percentage": sleep_data.sleep_score.sleep_performance_percentage,
                    "respiratory_rate": sleep_data.sleep_score.respiratory_rate
                })
            
            # Upsert based on sleep_uuid (handles both insert and update)
            result = self.supabase.table(self.table_name).upsert(
                record_data,
                on_conflict="sleep_uuid"
            ).execute()
            
            if result.data:
                record_id = result.data[0].get("id")
                logger.info("✅ Sleep data v2 stored", 
                           user_id=user_id,
                           sleep_uuid=sleep_data.id,
                           record_id=record_id,
                           v1_id=sleep_data.activity_v1_id)
                return record_id
            
            return None
            
        except APIError as e:
            logger.error("❌ Failed to store sleep data v2", 
                        user_id=user_id,
                        sleep_uuid=getattr(sleep_data, 'id', 'unknown'),
                        error=str(e))
            return None
        except Exception as e:
            logger.error("❌ Unexpected error storing sleep data", 
                        user_id=user_id, error=str(e))
            return None
    
    async def get_sleep_by_uuid(self, sleep_uuid: str) -> Optional[WhoopSleepRecord]:
        """Retrieve sleep data by UUID"""
        try:
            if not is_valid_uuid(sleep_uuid):
                logger.error("Invalid sleep UUID format", sleep_uuid=sleep_uuid)
                return None
            
            result = self.supabase.table(self.table_name).select("*").eq(
                "sleep_uuid", sleep_uuid
            ).execute()
            
            if result.data:
                return WhoopSleepRecord(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get sleep by UUID", 
                        sleep_uuid=sleep_uuid, error=str(e))
            return None
    
    async def get_sleep_by_v1_id(self, v1_id: int, user_id: str) -> Optional[WhoopSleepRecord]:
        """Retrieve sleep data by v1 ID for backward compatibility"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "sleep_v1_id", v1_id
            ).eq("user_id", user_id).execute()
            
            if result.data:
                return WhoopSleepRecord(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get sleep by v1 ID", 
                        v1_id=v1_id, user_id=user_id, error=str(e))
            return None
    
    async def get_user_sleep_data(self, user_id: str, start_date: date, 
                                   end_date: date) -> List[WhoopSleepRecord]:
        """Get sleep data for user in date range"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).gte("start_time", start_date.isoformat()).lte(
                "start_time", (end_date + datetime.timedelta(days=1)).isoformat()
            ).order("start_time", desc=True).execute()
            
            return [WhoopSleepRecord(**row) for row in result.data or []]
            
        except APIError as e:
            logger.error("❌ Failed to get user sleep data", 
                        user_id=user_id, error=str(e))
            return []


class WhoopWorkoutRepository:
    """Repository for WHOOP workout data with UUID support"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_workout_v2"
    
    async def store_workout_data(self, user_id: str, workout_data) -> Optional[str]:
        """
        Store workout data with UUID support
        
        Args:
            user_id: Internal user identifier
            workout_data: WhoopWorkoutData instance
            
        Returns:
            Database record ID if successful, None otherwise
        """
        try:
            # Validate UUID format
            if not is_valid_uuid(workout_data.id):
                logger.error("Invalid workout UUID format", 
                           workout_uuid=workout_data.id, user_id=user_id)
                return None
            
            # Convert datetime strings to datetime objects
            start_time = workout_data.start_datetime
            end_time = workout_data.end_datetime
            
            record_data = {
                "user_id": user_id,
                "workout_uuid": workout_data.id,
                "workout_v1_id": workout_data.activity_v1_id,
                "sport_id": workout_data.sport_id,
                "sport_name": workout_data.sport_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "timezone_offset": workout_data.timezone_offset,
                "strain_score": workout_data.strain_score,
                "average_heart_rate": workout_data.average_heart_rate,
                "max_heart_rate": workout_data.max_heart_rate,
                "calories_burned": workout_data.calories_burned,
                "distance_meters": workout_data.distance_meters,
                "raw_data": workout_data.raw_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Extract heart rate zones if available
            if workout_data.heart_rate_zones:
                record_data.update({
                    "zone_zero_milli": workout_data.heart_rate_zones.zone_zero_milli,
                    "zone_one_milli": workout_data.heart_rate_zones.zone_one_milli,
                    "zone_two_milli": workout_data.heart_rate_zones.zone_two_milli,
                    "zone_three_milli": workout_data.heart_rate_zones.zone_three_milli,
                    "zone_four_milli": workout_data.heart_rate_zones.zone_four_milli,
                    "zone_five_milli": workout_data.heart_rate_zones.zone_five_milli
                })
            
            # Upsert based on workout_uuid
            result = self.supabase.table(self.table_name).upsert(
                record_data,
                on_conflict="workout_uuid"
            ).execute()
            
            if result.data:
                record_id = result.data[0].get("id")
                logger.info("✅ Workout data v2 stored", 
                           user_id=user_id,
                           workout_uuid=workout_data.id,
                           record_id=record_id,
                           sport_id=workout_data.sport_id,
                           v1_id=workout_data.activity_v1_id)
                return record_id
            
            return None
            
        except APIError as e:
            logger.error("❌ Failed to store workout data v2", 
                        user_id=user_id,
                        workout_uuid=getattr(workout_data, 'id', 'unknown'),
                        error=str(e))
            return None
        except Exception as e:
            logger.error("❌ Unexpected error storing workout data", 
                        user_id=user_id, error=str(e))
            return None
    
    async def get_workout_by_uuid(self, workout_uuid: str) -> Optional[WhoopWorkoutRecord]:
        """Retrieve workout data by UUID"""
        try:
            if not is_valid_uuid(workout_uuid):
                logger.error("Invalid workout UUID format", workout_uuid=workout_uuid)
                return None
            
            result = self.supabase.table(self.table_name).select("*").eq(
                "workout_uuid", workout_uuid
            ).execute()
            
            if result.data:
                return WhoopWorkoutRecord(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get workout by UUID", 
                        workout_uuid=workout_uuid, error=str(e))
            return None
    
    async def get_workout_by_v1_id(self, v1_id: int, user_id: str) -> Optional[WhoopWorkoutRecord]:
        """Retrieve workout data by v1 ID for backward compatibility"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "workout_v1_id", v1_id
            ).eq("user_id", user_id).execute()
            
            if result.data:
                return WhoopWorkoutRecord(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get workout by v1 ID", 
                        v1_id=v1_id, user_id=user_id, error=str(e))
            return None
    
    async def get_user_workout_data(self, user_id: str, start_date: date, 
                                     end_date: date) -> List[WhoopWorkoutRecord]:
        """Get workout data for user in date range"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).gte("start_time", start_date.isoformat()).lte(
                "start_time", (end_date + datetime.timedelta(days=1)).isoformat()
            ).order("start_time", desc=True).execute()
            
            return [WhoopWorkoutRecord(**row) for row in result.data or []]
            
        except APIError as e:
            logger.error("❌ Failed to get user workout data", 
                        user_id=user_id, error=str(e))
            return []


class WhoopRecoveryRepository:
    """Repository for WHOOP recovery data (structure mostly unchanged)"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_recovery_v2"
    
    async def store_recovery_data(self, user_id: str, recovery_data) -> Optional[str]:
        """
        Store recovery data
        
        Args:
            user_id: Internal user identifier
            recovery_data: WhoopRecoveryData instance
            
        Returns:
            Database record ID if successful, None otherwise
        """
        try:
            recorded_at = recovery_data.recorded_datetime
            
            record_data = {
                "user_id": user_id,
                "cycle_id": recovery_data.cycle_id,
                "recovery_score": recovery_data.recovery_score,
                "hrv_rmssd": recovery_data.hrv_rmssd,
                "resting_heart_rate": recovery_data.resting_heart_rate,
                "respiratory_rate": recovery_data.respiratory_rate,
                "hrv_score": recovery_data.hrv_score,
                "rhr_score": recovery_data.rhr_score,
                "respiratory_score": recovery_data.respiratory_score,
                "recorded_at": recorded_at.isoformat(),
                "raw_data": recovery_data.raw_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Upsert based on user_id and cycle_id
            result = self.supabase.table(self.table_name).upsert(
                record_data,
                on_conflict="user_id,cycle_id"
            ).execute()
            
            if result.data:
                record_id = result.data[0].get("id")
                logger.info("✅ Recovery data v2 stored", 
                           user_id=user_id,
                           cycle_id=recovery_data.cycle_id,
                           record_id=record_id,
                           recovery_score=recovery_data.recovery_score)
                return record_id
            
            return None
            
        except APIError as e:
            logger.error("❌ Failed to store recovery data v2", 
                        user_id=user_id,
                        cycle_id=getattr(recovery_data, 'cycle_id', 'unknown'),
                        error=str(e))
            return None
        except Exception as e:
            logger.error("❌ Unexpected error storing recovery data", 
                        user_id=user_id, error=str(e))
            return None
    
    async def get_recovery_by_cycle_id(self, cycle_id: str, user_id: str) -> Optional[WhoopRecoveryRecord]:
        """Retrieve recovery data by cycle ID"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "cycle_id", cycle_id
            ).eq("user_id", user_id).execute()
            
            if result.data:
                return WhoopRecoveryRecord(**result.data[0])
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get recovery by cycle ID", 
                        cycle_id=cycle_id, user_id=user_id, error=str(e))
            return None
    
    async def get_user_recovery_data(self, user_id: str, start_date: date, 
                                      end_date: date) -> List[WhoopRecoveryRecord]:
        """Get recovery data for user in date range"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "user_id", user_id
            ).gte("recorded_at", start_date.isoformat()).lte(
                "recorded_at", (end_date + datetime.timedelta(days=1)).isoformat()
            ).order("recorded_at", desc=True).execute()
            
            return [WhoopRecoveryRecord(**row) for row in result.data or []]
            
        except APIError as e:
            logger.error("❌ Failed to get user recovery data", 
                        user_id=user_id, error=str(e))
            return []


class WhoopMigrationRepository:
    """Repository for tracking v1 to v2 migrations"""
    
    def __init__(self):
        self.supabase: Client = get_supabase_client()
        self.table_name = "whoop_migration_log"
    
    async def create_migration_record(self, migration_data: WhoopMigrationMapping) -> Optional[str]:
        """Create migration tracking record"""
        try:
            record_data = migration_data.model_dump(exclude_none=True)
            
            result = self.supabase.table(self.table_name).insert(record_data).execute()
            
            if result.data:
                record_id = result.data[0].get("id")
                logger.info("✅ Migration record created", 
                           resource_type=migration_data.resource_type,
                           v1_id=migration_data.v1_id,
                           v2_uuid=migration_data.v2_uuid,
                           user_id=migration_data.user_id)
                return record_id
            
            return None
            
        except APIError as e:
            logger.error("❌ Failed to create migration record", 
                        resource_type=migration_data.resource_type,
                        error=str(e))
            return None
    
    async def get_v2_uuid_for_v1_id(self, resource_type: str, v1_id: int, user_id: str) -> Optional[str]:
        """Get v2 UUID for a v1 ID"""
        try:
            result = self.supabase.table(self.table_name).select("v2_uuid").eq(
                "resource_type", resource_type
            ).eq("v1_id", v1_id).eq("user_id", user_id).eq(
                "migration_status", "completed"
            ).execute()
            
            if result.data:
                return result.data[0]["v2_uuid"]
            return None
            
        except APIError as e:
            logger.error("❌ Failed to get v2 UUID for v1 ID", 
                        resource_type=resource_type, v1_id=v1_id, error=str(e))
            return None
    
    async def get_migration_stats(self, user_id: str) -> Dict[str, Any]:
        """Get migration statistics for user"""
        try:
            result = self.supabase.table(self.table_name).select(
                "resource_type, migration_status"
            ).eq("user_id", user_id).execute()
            
            stats = {}
            for row in result.data or []:
                resource_type = row["resource_type"]
                status = row["migration_status"]
                
                if resource_type not in stats:
                    stats[resource_type] = {"completed": 0, "pending": 0, "failed": 0}
                
                stats[resource_type][status] = stats[resource_type].get(status, 0) + 1
            
            return stats
            
        except APIError as e:
            logger.error("❌ Failed to get migration stats", user_id=user_id, error=str(e))
            return {}


# Unified v2 data service
class WhoopDataService:
    """Unified service for all WHOOP data operations"""
    
    def __init__(self):
        self.sleep = WhoopSleepRepository()
        self.workouts = WhoopWorkoutRepository()
        self.recovery = WhoopRecoveryRepository()
        self.migration = WhoopMigrationRepository()
    
    async def get_comprehensive_health_data(self, user_id: str, start_date: date, 
                                            end_date: date) -> Dict[str, Any]:
        """
        Backwards-compatible alias for comprehensive data fetch.
        
        This keeps older callers working while the new v2 method name
        remains `get_comprehensive_data`.
        """
        return await self.get_comprehensive_data(user_id, start_date, end_date)
    
    async def store_comprehensive_data(self, user_id: str, response) -> Dict[str, Any]:
        """
        Store comprehensive health data
        
        Args:
            user_id: Internal user identifier
            response: WhoopDataResponse with all health data
            
        Returns:
            Summary of storage results
        """
        results = {
            "sleep": {"stored": 0, "errors": []},
            "workouts": {"stored": 0, "errors": []},
            "recovery": {"stored": 0, "errors": []}
        }
        
        try:
            # Store sleep data
            for sleep_record in response.sleep_data:
                try:
                    record_id = await self.sleep.store_sleep_data(user_id, sleep_record)
                    if record_id:
                        results["sleep"]["stored"] += 1
                    else:
                        results["sleep"]["errors"].append(f"Failed to store sleep {sleep_record.id}")
                except Exception as e:
                    results["sleep"]["errors"].append(f"Sleep {sleep_record.id}: {str(e)}")
            
            # Store workout data
            for workout_record in response.workout_data:
                try:
                    record_id = await self.workouts.store_workout_data(user_id, workout_record)
                    if record_id:
                        results["workouts"]["stored"] += 1
                    else:
                        results["workouts"]["errors"].append(f"Failed to store workout {workout_record.id}")
                except Exception as e:
                    results["workouts"]["errors"].append(f"Workout {workout_record.id}: {str(e)}")
            
            # Store recovery data
            for recovery_record in response.recovery_data:
                try:
                    record_id = await self.recovery.store_recovery_data(user_id, recovery_record)
                    if record_id:
                        results["recovery"]["stored"] += 1
                    else:
                        results["recovery"]["errors"].append(f"Failed to store recovery {recovery_record.cycle_id}")
                except Exception as e:
                    results["recovery"]["errors"].append(f"Recovery {recovery_record.cycle_id}: {str(e)}")
            
            logger.info("✅ Comprehensive data storage completed", 
                       user_id=user_id,
                       sleep_stored=results["sleep"]["stored"],
                       workout_stored=results["workouts"]["stored"],
                       recovery_stored=results["recovery"]["stored"],
                       total_errors=len(results["sleep"]["errors"]) + 
                                   len(results["workouts"]["errors"]) + 
                                   len(results["recovery"]["errors"]))
            
            return results
            
        except Exception as e:
            logger.error("❌ Failed to store comprehensive data", 
                        user_id=user_id, error=str(e))
            results["storage_error"] = str(e)
            return results
    
    async def get_comprehensive_data(self, user_id: str, start_date: date, 
                                      end_date: date) -> Dict[str, Any]:
        """Get comprehensive health data for user"""
        try:
            sleep_data = await self.sleep.get_user_sleep_data(user_id, start_date, end_date)
            workout_data = await self.workouts.get_user_workout_data(user_id, start_date, end_date)
            recovery_data = await self.recovery.get_user_recovery_data(user_id, start_date, end_date)
            migration_stats = await self.migration.get_migration_stats(user_id)
            
            return {
                "user_id": user_id,
                "date_range": {"start": start_date, "end": end_date},
                "sleep": [s.model_dump() for s in sleep_data],
                "workouts": [w.model_dump() for w in workout_data],
                "recovery": [r.model_dump() for r in recovery_data],
                "migration_stats": migration_stats,
                "record_counts": {
                    "sleep": len(sleep_data),
                    "workouts": len(workout_data),
                    "recovery": len(recovery_data)
                },
                "api_version": "v2"
            }
            
        except Exception as e:
            logger.error("❌ Failed to get comprehensive v2 data", 
                        user_id=user_id, error=str(e))
            return {
                "user_id": user_id,
                "error": str(e),
                "api_version": "v2"
            }


# Export repositories and service
__all__ = [
    "WhoopSleepRepository",
    "WhoopWorkoutRepository", 
    "WhoopRecoveryRepository",
    "WhoopMigrationRepository",
    "WhoopDataService"
]
