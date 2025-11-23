"""
Smart Sync Service for WHOOP Data
Manages intelligent caching and synchronization logic based on sync thresholds
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import UUID
import structlog
from app.db.supabase_client import get_supabase

logger = structlog.get_logger(__name__)


class SyncThreshold:
    """Time thresholds for automatic syncing (in hours)"""
    RECOVERY_THRESHOLD = timedelta(hours=2)   # Recovery updates frequently
    SLEEP_THRESHOLD = timedelta(hours=2)      # Sleep data once per day
    CYCLE_THRESHOLD = timedelta(hours=2)      # Cycle updates daily
    WORKOUT_THRESHOLD = timedelta(hours=1)    # Workouts are real-time


class SyncStatus(str, Enum):
    """Status of sync operation"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some records synced, some failed


class SmartSyncService:
    """
    Determines whether to fetch fresh data or use cached data
    based on last sync time and configured thresholds.

    Uses whoop_sync_log table to track sync history efficiently.
    """

    def __init__(self):
        self.supabase = get_supabase().get_client()

    async def should_sync(
        self,
        user_id: str,
        data_type: str,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Determine if data should be synced from WHOOP API based on last sync time.

        Args:
            user_id: User UUID as string
            data_type: 'cycle', 'recovery', 'sleep', 'workout'
            force_refresh: If True, always sync (user manual refresh)

        Returns:
            {
                'should_sync': bool,
                'reason': str,
                'time_since_last_sync_seconds': int,
                'threshold_seconds': int,
                'last_sync_at': str (ISO format),
                'cached_record_count': int,
                'last_sync_status': str,
            }
        """

        # If force refresh, always sync
        if force_refresh:
            logger.info(
                '🔄 Force refresh requested',
                user_id=user_id,
                data_type=data_type,
            )
            return {
                'should_sync': True,
                'reason': 'User force refresh requested',
                'force_refresh': True,
            }

        try:
            # Get last sync info from whoop_sync_log
            sync_log_response = self.supabase.table('whoop_sync_log').select(
                'last_sync_at, sync_status, records_synced'
            ).eq('user_id', user_id).eq(
                'data_type', data_type
            ).order('created_at', desc=True).limit(1).execute()

            if not sync_log_response.data:
                # Never synced before
                logger.info(
                    '🆕 No sync history found',
                    user_id=user_id,
                    data_type=data_type,
                )
                return {
                    'should_sync': True,
                    'reason': 'No sync history found - first time syncing',
                    'last_sync_at': None,
                    'cached_record_count': 0,
                }

            last_sync_record = sync_log_response.data[0]
            last_sync_at_str = last_sync_record['last_sync_at']

            # Parse last sync timestamp
            last_sync_at = datetime.fromisoformat(
                last_sync_at_str.replace('Z', '+00:00')
            )

            # Get threshold for this data type
            threshold = self._get_threshold(data_type)

            # Calculate time since last sync
            now = datetime.now(timezone.utc)
            time_since_sync = now - last_sync_at

            # Decision logic
            should_sync = time_since_sync > threshold

            time_since_hours = time_since_sync.total_seconds() / 3600
            threshold_hours = threshold.total_seconds() / 3600

            result = {
                'should_sync': should_sync,
                'reason': (
                    f'Last sync was {time_since_hours:.1f} hours ago (threshold: {threshold_hours} hours) - NEEDS REFRESH'
                    if should_sync
                    else f'Last sync was {time_since_hours:.1f} hours ago (threshold: {threshold_hours} hours) - FRESH ENOUGH'
                ),
                'last_sync_at': last_sync_at.isoformat(),
                'time_since_last_sync_seconds': int(time_since_sync.total_seconds()),
                'time_since_last_sync_hours': round(time_since_hours, 1),
                'threshold_seconds': int(threshold.total_seconds()),
                'threshold_hours': threshold_hours,
                'cached_record_count': last_sync_record.get('records_synced', 0),
                'last_sync_status': last_sync_record['sync_status'],
            }

            if should_sync:
                logger.info(
                    f'⏰ Sync needed for {data_type}',
                    user_id=user_id,
                    time_since_sync_hours=time_since_hours,
                    threshold_hours=threshold_hours,
                )
            else:
                logger.info(
                    f'✓ Using cached {data_type} data',
                    user_id=user_id,
                    time_since_sync_hours=time_since_hours,
                    cached_records=result['cached_record_count'],
                )

            return result

        except Exception as e:
            logger.error(
                f'Error checking sync status for {data_type}',
                user_id=user_id,
                data_type=data_type,
                error=str(e),
            )
            # On error, sync to be safe
            return {
                'should_sync': True,
                'reason': f'Error checking sync log: {str(e)} - syncing to be safe',
            }

    def _get_threshold(self, data_type: str) -> timedelta:
        """Get sync threshold for data type"""
        thresholds = {
            'recovery': SyncThreshold.RECOVERY_THRESHOLD,
            'sleep': SyncThreshold.SLEEP_THRESHOLD,
            'cycle': SyncThreshold.CYCLE_THRESHOLD,
            'workout': SyncThreshold.WORKOUT_THRESHOLD,
        }
        return thresholds.get(data_type, timedelta(hours=2))

    async def get_cached_data(
        self,
        user_id: str,
        data_type: str,
        limit: int = 30,
    ) -> Dict[str, Any]:
        """
        Retrieve cached data from database without hitting WHOOP API.

        Args:
            user_id: User UUID as string
            data_type: 'cycle', 'recovery', 'sleep', 'workout'
            limit: Maximum number of records to return

        Returns:
            {
                'data': List of records,
                'count': Number of records,
                'source': 'cache',
                'note': Message about data source
            }
        """
        table_map = {
            'cycle': 'whoop_cycle',
            'recovery': 'whoop_recovery',
            'sleep': 'whoop_sleep',
            'workout': 'whoop_workout',
        }

        table = table_map.get(data_type)
        if not table:
            logger.error(f'Unknown data type: {data_type}', user_id=user_id)
            return {
                'data': [],
                'count': 0,
                'error': f'Unknown data type: {data_type}',
            }

        try:
            result = self.supabase.table(table).select('*').eq(
                'user_id', user_id
            ).order('created_at', desc=True).limit(limit).execute()

            logger.info(
                f'✓ Retrieved cached {data_type} data',
                user_id=user_id,
                record_count=len(result.data),
            )

            return {
                'data': result.data,
                'count': len(result.data),
                'source': 'cache',
                'note': 'Data from local database (not from WHOOP API)',
            }

        except Exception as e:
            logger.error(
                f'Error fetching cached {data_type} data',
                user_id=user_id,
                data_type=data_type,
                error=str(e),
            )
            return {
                'data': [],
                'count': 0,
                'error': str(e),
            }

    async def log_sync_attempt(
        self,
        user_id: str,
        data_type: str,
        status: SyncStatus,
        records_synced: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Log sync attempt to whoop_sync_log table.
        Uses upsert to create or update sync log entry.

        Called after attempting to sync from WHOOP API.

        Args:
            user_id: User UUID as string
            data_type: 'cycle', 'recovery', 'sleep', 'workout'
            status: SyncStatus enum value
            records_synced: Number of records synced
            error_message: Error message if sync failed

        Returns:
            True if logging succeeded, False otherwise
        """
        try:
            # Prepare sync log entry
            sync_log_entry = {
                'user_id': user_id,
                'data_type': data_type,
                'last_sync_at': datetime.now(timezone.utc).isoformat(),
                'sync_status': status.value,
                'records_synced': records_synced,
                'error_message': error_message,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }

            # Upsert: Create if not exists, update if exists
            response = self.supabase.table('whoop_sync_log').upsert(
                sync_log_entry,
                on_conflict='user_id,data_type',
            ).execute()

            logger.info(
                f'✓ Logged {data_type} sync attempt',
                user_id=user_id,
                status=status.value,
                records_synced=records_synced,
            )

            return True

        except Exception as e:
            logger.error(
                f'Error logging sync for {data_type}',
                user_id=user_id,
                data_type=data_type,
                error=str(e),
            )
            return False

    async def get_sync_status_all(self, user_id: str) -> Dict[str, Any]:
        """
        Get sync status for all data types.

        Useful for UI to show sync state and determine next actions.

        Args:
            user_id: User UUID as string

        Returns:
            {
                'user_id': str,
                'sync_status': {
                    'cycle': {...},
                    'recovery': {...},
                    'sleep': {...},
                    'workout': {...}
                },
                'check_timestamp': ISO datetime
            }
        """
        try:
            sync_log_response = self.supabase.table('whoop_sync_log').select(
                'data_type, last_sync_at, sync_status, records_synced, error_message'
            ).eq('user_id', user_id).execute()

            status_by_type = {}

            for log in sync_log_response.data:
                data_type = log['data_type']
                last_sync_at_str = log['last_sync_at']

                last_sync_at = datetime.fromisoformat(
                    last_sync_at_str.replace('Z', '+00:00')
                )
                now = datetime.now(timezone.utc)
                time_since_sync = (now - last_sync_at).total_seconds()

                threshold = self._get_threshold(data_type)
                threshold_seconds = threshold.total_seconds()

                needs_sync = time_since_sync > threshold_seconds

                status_by_type[data_type] = {
                    'last_sync_at': log['last_sync_at'],
                    'sync_status': log['sync_status'],
                    'records_synced': log['records_synced'],
                    'time_since_sync_seconds': int(time_since_sync),
                    'time_since_sync_hours': round(time_since_sync / 3600, 1),
                    'threshold_seconds': int(threshold_seconds),
                    'threshold_hours': round(threshold_seconds / 3600, 1),
                    'needs_sync': needs_sync,
                    'error_message': log.get('error_message'),
                }

            logger.info(
                '✓ Retrieved sync status for all data types',
                user_id=user_id,
                data_types_checked=len(status_by_type),
            )

            return {
                'user_id': user_id,
                'sync_status': status_by_type,
                'check_timestamp': datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(
                'Error getting sync status',
                user_id=user_id,
                error=str(e),
            )
            raise

    async def has_data_for_type(
        self,
        user_id: str,
        data_type: str,
    ) -> bool:
        """
        Check if user has any cached data for a data type.

        Args:
            user_id: User UUID as string
            data_type: 'cycle', 'recovery', 'sleep', 'workout'

        Returns:
            True if cached data exists, False otherwise
        """
        table_map = {
            'cycle': 'whoop_cycle',
            'recovery': 'whoop_recovery',
            'sleep': 'whoop_sleep',
            'workout': 'whoop_workout',
        }

        table = table_map.get(data_type)
        if not table:
            return False

        try:
            result = self.supabase.table(table).select(
                'count', count='exact'
            ).eq('user_id', user_id).execute()

            has_data = result.count is not None and result.count > 0

            logger.debug(
                f'Checked for {data_type} data',
                user_id=user_id,
                has_data=has_data,
                record_count=result.count or 0,
            )

            return has_data

        except Exception as e:
            logger.error(
                f'Error checking for {data_type} data',
                user_id=user_id,
                data_type=data_type,
                error=str(e),
            )
            return False
