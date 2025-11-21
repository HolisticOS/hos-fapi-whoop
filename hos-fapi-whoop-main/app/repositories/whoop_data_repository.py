"""
WHOOP Data Repository
Handles all database operations for WHOOP health data with incremental sync support
Uses UUID for user_id to integrate with Supabase authentication
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID
from supabase import Client
import structlog

logger = structlog.get_logger(__name__)


class WhoopDataRepository:
    """Repository for WHOOP health data with incremental sync"""

    def __init__(self, supabase_client: Client):
        self.db = supabase_client

    # ========================================================================
    # SYNC LOG OPERATIONS
    # ========================================================================

    async def get_last_sync_time(self, user_id: UUID, data_type: str) -> Optional[datetime]:
        """Get the last successful sync time for a specific data type"""
        try:
            # Convert UUID to string for Supabase query
            user_id_str = str(user_id)
            response = self.db.table('whoop_sync_log').select('last_sync_at').eq(
                'user_id', user_id_str
            ).eq('data_type', data_type).eq('sync_status', 'success').single().execute()

            if response.data:
                return datetime.fromisoformat(response.data['last_sync_at'])
            return None
        except Exception as e:
            logger.warning(f"No previous sync found for {user_id}/{data_type}: {e}")
            return None

    async def update_sync_log(
        self,
        user_id: UUID,
        data_type: str,
        records_synced: int,
        status: str = 'success',
        error_message: Optional[str] = None
    ):
        """Update sync log with latest sync information"""
        try:
            # Convert UUID to string for Supabase
            user_id_str = str(user_id)
            data = {
                'user_id': user_id_str,
                'data_type': data_type,
                'last_sync_at': datetime.utcnow().isoformat(),
                'sync_status': status,
                'records_synced': records_synced,
                'error_message': error_message,
                'updated_at': datetime.utcnow().isoformat()
            }

            # Upsert: insert or update based on unique constraint (user_id, data_type)
            self.db.table('whoop_sync_log').upsert(
                data,
                on_conflict='user_id,data_type'
            ).execute()

            logger.info(
                f"Sync log updated",
                user_id=user_id,
                data_type=data_type,
                records_synced=records_synced,
                status=status
            )
        except Exception as e:
            logger.error(f"Failed to update sync log: {e}", user_id=user_id, data_type=data_type)

    # ========================================================================
    # RECOVERY DATA OPERATIONS
    # ========================================================================

    async def store_recovery_records(self, user_id: UUID, records: List[Dict[str, Any]]) -> int:
        """Store recovery records, skip duplicates based on WHOOP ID"""
        if not records:
            return 0

        # Convert UUID to string
        user_id_str = str(user_id)
        stored_count = 0
        for record in records:
            try:
                # Helper function to convert float to int safely
                def safe_int(value):
                    """Convert float to int, return None if value is None"""
                    return int(value) if value is not None else None

                # WHOOP v2 recovery API uses 'sleep_id' as the unique identifier, not 'id'
                data = {
                    'id': record.get('sleep_id'),  # Use sleep_id as the primary key
                    'user_id': user_id_str,
                    # Note: cycle_id is stored in raw_data but not in a separate column
                    'recovery_score': record.get('score', {}).get('recovery_score'),
                    'hrv_rmssd_milli': record.get('score', {}).get('hrv_rmssd_milli'),
                    'resting_heart_rate': safe_int(record.get('score', {}).get('resting_heart_rate')),
                    'spo2_percentage': safe_int(record.get('score', {}).get('spo2_percentage')),
                    'skin_temp_celsius': record.get('score', {}).get('skin_temp_celsius'),
                    'calibration_state': record.get('score', {}).get('state'),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at'),
                    'raw_data': record  # Store complete response (includes cycle_id)
                }

                # Upsert: insert or skip if ID exists
                self.db.table('whoop_recovery').upsert(data, on_conflict='id').execute()
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store recovery record: {e}", record_id=record.get('id'))

        logger.info(f"Stored {stored_count}/{len(records)} recovery records", user_id=user_id)
        return stored_count

    async def get_recovery_by_date(self, user_id: UUID, target_date: date) -> Optional[Dict[str, Any]]:
        """Get latest recovery record for a specific date"""
        try:
            user_id_str = str(user_id)
            response = self.db.table('whoop_recovery').select('*').eq(
                'user_id', user_id_str
            ).gte(
                'created_at', f"{target_date}T00:00:00"
            ).lt(
                'created_at', f"{target_date}T23:59:59"
            ).order('created_at', desc=True).limit(1).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get recovery by date: {e}", user_id=user_id, date=target_date)
            return None

    # ========================================================================
    # SLEEP DATA OPERATIONS
    # ========================================================================

    async def store_sleep_records(self, user_id: UUID, records: List[Dict[str, Any]]) -> int:
        """Store sleep records, skip duplicates based on WHOOP ID"""
        if not records:
            return 0

        user_id_str = str(user_id)
        stored_count = 0
        for record in records:
            try:
                score = record.get('score', {}) or {}
                data = {
                    'id': record.get('id'),
                    'user_id': user_id_str,
                    'total_sleep_time_milli': score.get('total_sleep_time_milli'),
                    'sleep_performance_percentage': score.get('sleep_performance_percentage'),
                    'sleep_consistency_percentage': score.get('sleep_consistency_percentage'),
                    'sleep_efficiency_percentage': score.get('sleep_efficiency_percentage'),
                    'rem_sleep_milli': score.get('stage_summary', {}).get('rem_sleep_duration_milli'),
                    'slow_wave_sleep_milli': score.get('stage_summary', {}).get('slow_wave_sleep_duration_milli'),
                    'light_sleep_milli': score.get('stage_summary', {}).get('light_sleep_duration_milli'),
                    'awake_milli': score.get('stage_summary', {}).get('total_awake_time_milli'),
                    'start_time': record.get('start'),
                    'end_time': record.get('end'),
                    'cycle_id': record.get('cycle_id'),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at'),
                    'raw_data': record
                }

                self.db.table('whoop_sleep').upsert(data, on_conflict='id').execute()
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store sleep record: {e}", record_id=record.get('id'))

        logger.info(f"Stored {stored_count}/{len(records)} sleep records", user_id=user_id)
        return stored_count

    async def get_sleep_by_date(self, user_id: UUID, target_date: date) -> Optional[Dict[str, Any]]:
        """Get latest sleep record ending on a specific date"""
        try:
            user_id_str = str(user_id)
            response = self.db.table('whoop_sleep').select('*').eq(
                'user_id', user_id_str
            ).gte(
                'end_time', f"{target_date}T00:00:00"
            ).lt(
                'end_time', f"{target_date}T23:59:59"
            ).order('end_time', desc=True).limit(1).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get sleep by date: {e}", user_id=user_id, date=target_date)
            return None

    # ========================================================================
    # WORKOUT DATA OPERATIONS
    # ========================================================================

    async def store_workout_records(self, user_id: UUID, records: List[Dict[str, Any]]) -> int:
        """Store workout records, skip duplicates based on WHOOP ID"""
        if not records:
            return 0

        user_id_str = str(user_id)
        stored_count = 0
        for record in records:
            try:
                score = record.get('score', {}) or {}
                data = {
                    'id': record.get('id'),
                    'user_id': user_id_str,
                    'strain_score': score.get('strain'),
                    'average_heart_rate': score.get('average_heart_rate'),
                    'max_heart_rate': score.get('max_heart_rate'),
                    'calories_burned': score.get('kilojoule'),
                    'distance_meters': score.get('distance_meter'),
                    'sport_id': record.get('sport_id'),
                    'sport_name': record.get('sport_name', 'Activity'),
                    'start_time': record.get('start'),
                    'end_time': record.get('end'),
                    'duration_milli': score.get('duration_milli'),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at'),
                    'raw_data': record
                }

                self.db.table('whoop_workout').upsert(data, on_conflict='id').execute()
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store workout record: {e}", record_id=record.get('id'))

        logger.info(f"Stored {stored_count}/{len(records)} workout records", user_id=user_id)
        return stored_count

    async def get_workouts_by_date(self, user_id: UUID, target_date: date) -> List[Dict[str, Any]]:
        """Get all workout records for a specific date"""
        try:
            user_id_str = str(user_id)
            response = self.db.table('whoop_workout').select('*').eq(
                'user_id', user_id_str
            ).gte(
                'start_time', f"{target_date}T00:00:00"
            ).lt(
                'start_time', f"{target_date}T23:59:59"
            ).order('start_time', desc=False).execute()

            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to get workouts by date: {e}", user_id=user_id, date=target_date)
            return []

    # ========================================================================
    # CYCLE DATA OPERATIONS
    # ========================================================================

    async def store_cycle_records(self, user_id: UUID, records: List[Dict[str, Any]]) -> int:
        """Store cycle records, skip duplicates based on WHOOP ID"""
        if not records:
            return 0

        user_id_str = str(user_id)
        stored_count = 0
        for record in records:
            try:
                score = record.get('score', {}) or {}
                data = {
                    'id': record.get('id'),
                    'user_id': user_id_str,
                    'day_strain': score.get('strain'),
                    'calories_burned': score.get('kilojoule'),
                    'average_heart_rate': score.get('average_heart_rate'),
                    'max_heart_rate': score.get('max_heart_rate'),
                    'start_time': record.get('start'),
                    'end_time': record.get('end'),
                    'created_at': record.get('created_at'),
                    'updated_at': record.get('updated_at'),
                    'raw_data': record
                }

                self.db.table('whoop_cycle').upsert(data, on_conflict='id').execute()
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store cycle record: {e}", record_id=record.get('id'))

        logger.info(f"Stored {stored_count}/{len(records)} cycle records", user_id=user_id)
        return stored_count

    async def get_cycle_by_date(self, user_id: UUID, target_date: date) -> Optional[Dict[str, Any]]:
        """Get cycle record for a specific date"""
        try:
            user_id_str = str(user_id)
            response = self.db.table('whoop_cycle').select('*').eq(
                'user_id', user_id_str
            ).gte(
                'start_time', f"{target_date}T00:00:00"
            ).lt(
                'start_time', f"{target_date}T23:59:59"
            ).order('start_time', desc=True).limit(1).execute()

            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get cycle by date: {e}", user_id=user_id, date=target_date)
            return None

    # ========================================================================
    # AGGREGATED DATA QUERIES
    # ========================================================================

    async def get_daily_summary(self, user_id: UUID, target_date: date) -> Dict[str, Any]:
        """Get aggregated daily summary from database"""
        recovery = await self.get_recovery_by_date(user_id, target_date)
        sleep = await self.get_sleep_by_date(user_id, target_date)
        workouts = await self.get_workouts_by_date(user_id, target_date)
        cycle = await self.get_cycle_by_date(user_id, target_date)

        return {
            'date': target_date.isoformat(),
            'recovery': recovery,
            'sleep': sleep,
            'workouts': workouts,  # List of workouts
            'cycle': cycle,
            'has_data': any([recovery, sleep, workouts, cycle])
        }

    async def check_data_exists(self, user_id: UUID, data_type: str, target_date: date) -> bool:
        """Check if data already exists for a specific date"""
        if data_type == 'recovery':
            data = await self.get_recovery_by_date(user_id, target_date)
        elif data_type == 'sleep':
            data = await self.get_sleep_by_date(user_id, target_date)
        elif data_type == 'workout':
            data = await self.get_workouts_by_date(user_id, target_date)
        elif data_type == 'cycle':
            data = await self.get_cycle_by_date(user_id, target_date)
        else:
            return False

        return bool(data)
