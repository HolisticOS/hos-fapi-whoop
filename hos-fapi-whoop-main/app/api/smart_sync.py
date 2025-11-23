"""
Smart Sync Endpoints for WHOOP Data
Implements intelligent caching based on last sync time and configured thresholds.
Returns cached data if recently synced, fetches fresh data if threshold exceeded.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
import structlog

from app.core.auth import get_current_user
from app.services.sync_service import SmartSyncService, SyncStatus
from app.services.whoop_service import WhoopAPIService
from app.repositories.whoop_data_repository import WhoopDataRepository
from app.db.supabase_client import get_supabase

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
sync_service = SmartSyncService()
whoop_client = WhoopAPIService()


@router.get("/recovery")
async def get_recovery_data_smart(
    current_user: str = Depends(get_current_user),
    force_refresh: bool = Query(False, description="Force fresh data from WHOOP API"),
    limit: int = Query(10, ge=1, le=100, description="Max records to return"),
):
    """
    Get recovery data with smart caching.

    Logic:
    - If synced < 2 hours ago: Return cached data (fast response, saves API quota)
    - If synced > 2 hours ago: Fetch fresh data from WHOOP API
    - On API error: Fall back to stale cache

    Query Parameters:
    - force_refresh: If True, fetch from WHOOP API even if recent cache exists
    - limit: Maximum records to return (default: 10)

    Returns:
        {
            "status": "success",
            "data": [...recovery records...],
            "metadata": {
                "source": "cache" or "whoop_api",
                "record_count": int,
                "last_sync_at": ISO datetime,
                "time_since_sync_seconds": int,
                "needs_sync": bool
            }
        }
    """
    try:
        user_id = str(current_user)

        logger.info(
            '📊 Recovery data request',
            user_id=user_id,
            force_refresh=force_refresh,
        )

        # Step 1: Check if we should sync
        sync_decision = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=force_refresh,
        )

        logger.info(
            'Sync decision made',
            user_id=user_id,
            should_sync=sync_decision['should_sync'],
            reason=sync_decision['reason'],
        )

        # Step 2a: Return cached data if within threshold and sync not needed
        if not sync_decision.get('should_sync', False):
            cached_data = await sync_service.get_cached_data(
                user_id=user_id,
                data_type='recovery',
                limit=limit,
            )

            if cached_data.get('count', 0) > 0:
                logger.info(
                    '✓ Returning cached recovery data',
                    user_id=user_id,
                    record_count=cached_data['count'],
                    last_sync_at=sync_decision.get('last_sync_at'),
                )

                return {
                    'status': 'success',
                    'data': cached_data['data'],
                    'metadata': {
                        'source': 'cache',
                        'record_count': cached_data['count'],
                        'last_sync_at': sync_decision.get('last_sync_at'),
                        'time_since_sync_seconds': sync_decision.get('time_since_last_sync_seconds'),
                        'time_since_sync_hours': sync_decision.get('time_since_last_sync_hours'),
                        'threshold_seconds': sync_decision.get('threshold_seconds'),
                        'cached_enough': True,
                        'note': '✓ Using cached data (fresh enough)',
                    },
                }

        # Step 2b: Fetch fresh data from WHOOP API
        logger.info(
            '🔄 Syncing fresh recovery data from WHOOP API',
            user_id=user_id,
        )

        try:
            # Fetch comprehensive data (includes recovery)
            fresh_data_response = await whoop_client.get_comprehensive_data(
                user_id=user_id,
                days_back=30,
                include_all_pages=False,
            )

            # Extract recovery data
            recovery_data = fresh_data_response.recovery_data or []

            logger.info(
                '✓ Fresh recovery data fetched from WHOOP',
                user_id=user_id,
                records_fetched=len(recovery_data),
            )

            # Store fresh data in database
            supabase = get_supabase().get_client()
            repo = WhoopDataRepository(supabase)

            # Extract raw_data from response objects
            recovery_records = [
                r.raw_data for r in recovery_data
                if hasattr(r, 'raw_data') and r.raw_data
            ]

            if recovery_records:
                stored_count = await repo.store_recovery_records(
                    UUID(current_user),
                    recovery_records,
                )
                logger.info(
                    '💾 Stored recovery records',
                    user_id=user_id,
                    stored=stored_count,
                )
            else:
                stored_count = 0
                logger.warn(
                    '⚠️ No recovery records extracted',
                    user_id=user_id,
                )

            # Log successful sync
            await sync_service.log_sync_attempt(
                user_id=user_id,
                data_type='recovery',
                status=SyncStatus.SUCCESS,
                records_synced=stored_count,
            )

            # Return fresh data with limit
            fresh_data_limited = recovery_records[:limit] if recovery_records else []

            logger.info(
                '✓ Recovery data synced successfully',
                user_id=user_id,
                records_returned=len(fresh_data_limited),
            )

            return {
                'status': 'success',
                'data': fresh_data_limited,
                'metadata': {
                    'source': 'whoop_api',
                    'record_count': len(fresh_data_limited),
                    'synced_at': datetime.now(timezone.utc).isoformat(),
                    'note': '✓ Fresh data from WHOOP API',
                },
            }

        except Exception as api_error:
            logger.error(
                '✗ WHOOP API sync failed',
                user_id=user_id,
                error=str(api_error),
            )

            # Log failed sync
            await sync_service.log_sync_attempt(
                user_id=user_id,
                data_type='recovery',
                status=SyncStatus.FAILED,
                error_message=str(api_error),
            )

            # Fallback: Try to return stale cache
            try:
                cached_data = await sync_service.get_cached_data(
                    user_id=user_id,
                    data_type='recovery',
                    limit=limit,
                )

                if cached_data.get('count', 0) > 0:
                    logger.warn(
                        '⚠️ Returning stale cache due to API error',
                        user_id=user_id,
                        cached_records=cached_data['count'],
                    )

                    return {
                        'status': 'success_with_warning',
                        'data': cached_data['data'],
                        'metadata': {
                            'source': 'stale_cache',
                            'record_count': cached_data['count'],
                            'warning': 'Using stale cached data due to sync failure',
                            'error': str(api_error),
                        },
                    }
            except:
                pass

            raise HTTPException(
                status_code=503,
                detail='Failed to retrieve recovery data from WHOOP API',
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            '✗ Unexpected error in recovery endpoint',
            user_id=current_user,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sleep")
async def get_sleep_data_smart(
    current_user: str = Depends(get_current_user),
    force_refresh: bool = Query(False),
    limit: int = Query(10, ge=1, le=100),
):
    """Get sleep data with smart caching - same logic as recovery"""
    try:
        user_id = str(current_user)

        logger.info('📊 Sleep data request', user_id=user_id, force_refresh=force_refresh)

        sync_decision = await sync_service.should_sync(
            user_id=user_id,
            data_type='sleep',
            force_refresh=force_refresh,
        )

        if not sync_decision.get('should_sync', False):
            cached_data = await sync_service.get_cached_data(
                user_id=user_id,
                data_type='sleep',
                limit=limit,
            )

            if cached_data.get('count', 0) > 0:
                return {
                    'status': 'success',
                    'data': cached_data['data'],
                    'metadata': {
                        'source': 'cache',
                        'record_count': cached_data['count'],
                        'last_sync_at': sync_decision.get('last_sync_at'),
                        'time_since_sync_hours': sync_decision.get('time_since_last_sync_hours'),
                    },
                }

        # Fetch fresh data
        logger.info('🔄 Syncing fresh sleep data', user_id=user_id)

        fresh_data_response = await whoop_client.get_comprehensive_data(
            user_id=user_id,
            days_back=30,
        )

        sleep_data = fresh_data_response.sleep_data or []
        sleep_records = [
            s.raw_data for s in sleep_data
            if hasattr(s, 'raw_data') and s.raw_data
        ]

        supabase = get_supabase().get_client()
        repo = WhoopDataRepository(supabase)

        if sleep_records:
            stored_count = await repo.store_sleep_records(
                UUID(current_user),
                sleep_records,
            )
        else:
            stored_count = 0

        await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='sleep',
            status=SyncStatus.SUCCESS,
            records_synced=stored_count,
        )

        sleep_data_limited = sleep_records[:limit] if sleep_records else []

        return {
            'status': 'success',
            'data': sleep_data_limited,
            'metadata': {
                'source': 'whoop_api',
                'record_count': len(sleep_data_limited),
                'synced_at': datetime.now(timezone.utc).isoformat(),
            },
        }

    except Exception as e:
        logger.error('✗ Sleep sync failed', user_id=current_user, error=str(e))

        await sync_service.log_sync_attempt(
            user_id=str(current_user),
            data_type='sleep',
            status=SyncStatus.FAILED,
            error_message=str(e),
        )

        # Fallback to cache
        try:
            cached_data = await sync_service.get_cached_data(
                user_id=str(current_user),
                data_type='sleep',
                limit=limit,
            )
            if cached_data.get('count', 0) > 0:
                return {
                    'status': 'success_with_warning',
                    'data': cached_data['data'],
                    'metadata': {'source': 'stale_cache', 'warning': 'Using stale cache'},
                }
        except:
            pass

        raise HTTPException(status_code=503, detail='Failed to fetch sleep data')


@router.get("/cycle")
async def get_cycle_data_smart(
    current_user: str = Depends(get_current_user),
    force_refresh: bool = Query(False),
    limit: int = Query(10, ge=1, le=100),
):
    """Get cycle data with smart caching - same logic as recovery"""
    try:
        user_id = str(current_user)

        logger.info('📊 Cycle data request', user_id=user_id, force_refresh=force_refresh)

        sync_decision = await sync_service.should_sync(
            user_id=user_id,
            data_type='cycle',
            force_refresh=force_refresh,
        )

        if not sync_decision.get('should_sync', False):
            cached_data = await sync_service.get_cached_data(
                user_id=user_id,
                data_type='cycle',
                limit=limit,
            )

            if cached_data.get('count', 0) > 0:
                return {
                    'status': 'success',
                    'data': cached_data['data'],
                    'metadata': {
                        'source': 'cache',
                        'record_count': cached_data['count'],
                        'last_sync_at': sync_decision.get('last_sync_at'),
                        'time_since_sync_hours': sync_decision.get('time_since_last_sync_hours'),
                    },
                }

        logger.info('🔄 Syncing fresh cycle data', user_id=user_id)

        fresh_data_response = await whoop_client.get_comprehensive_data(
            user_id=user_id,
            days_back=30,
        )

        cycle_data = fresh_data_response.cycle_data or []
        cycle_records = [
            c.raw_data for c in cycle_data
            if hasattr(c, 'raw_data') and c.raw_data
        ]

        supabase = get_supabase().get_client()
        repo = WhoopDataRepository(supabase)

        if cycle_records:
            stored_count = await repo.store_cycle_records(
                UUID(current_user),
                cycle_records,
            )
        else:
            stored_count = 0

        await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='cycle',
            status=SyncStatus.SUCCESS,
            records_synced=stored_count,
        )

        cycle_data_limited = cycle_records[:limit] if cycle_records else []

        return {
            'status': 'success',
            'data': cycle_data_limited,
            'metadata': {
                'source': 'whoop_api',
                'record_count': len(cycle_data_limited),
                'synced_at': datetime.now(timezone.utc).isoformat(),
            },
        }

    except Exception as e:
        logger.error('✗ Cycle sync failed', user_id=current_user, error=str(e))

        await sync_service.log_sync_attempt(
            user_id=str(current_user),
            data_type='cycle',
            status=SyncStatus.FAILED,
            error_message=str(e),
        )

        # Fallback to cache
        try:
            cached_data = await sync_service.get_cached_data(
                user_id=str(current_user),
                data_type='cycle',
                limit=limit,
            )
            if cached_data.get('count', 0) > 0:
                return {
                    'status': 'success_with_warning',
                    'data': cached_data['data'],
                    'metadata': {'source': 'stale_cache', 'warning': 'Using stale cache'},
                }
        except:
            pass

        raise HTTPException(status_code=503, detail='Failed to fetch cycle data')


@router.get("/workout")
async def get_workout_data_smart(
    current_user: str = Depends(get_current_user),
    force_refresh: bool = Query(False),
    limit: int = Query(10, ge=1, le=100),
):
    """Get workout data with smart caching - same logic as recovery"""
    try:
        user_id = str(current_user)

        logger.info('📊 Workout data request', user_id=user_id, force_refresh=force_refresh)

        sync_decision = await sync_service.should_sync(
            user_id=user_id,
            data_type='workout',
            force_refresh=force_refresh,
        )

        if not sync_decision.get('should_sync', False):
            cached_data = await sync_service.get_cached_data(
                user_id=user_id,
                data_type='workout',
                limit=limit,
            )

            if cached_data.get('count', 0) > 0:
                return {
                    'status': 'success',
                    'data': cached_data['data'],
                    'metadata': {
                        'source': 'cache',
                        'record_count': cached_data['count'],
                        'last_sync_at': sync_decision.get('last_sync_at'),
                        'time_since_sync_hours': sync_decision.get('time_since_last_sync_hours'),
                    },
                }

        logger.info('🔄 Syncing fresh workout data', user_id=user_id)

        fresh_data_response = await whoop_client.get_comprehensive_data(
            user_id=user_id,
            days_back=30,
        )

        workout_data = fresh_data_response.workout_data or []
        workout_records = [
            w.raw_data for w in workout_data
            if hasattr(w, 'raw_data') and w.raw_data
        ]

        supabase = get_supabase().get_client()
        repo = WhoopDataRepository(supabase)

        if workout_records:
            stored_count = await repo.store_workout_records(
                UUID(current_user),
                workout_records,
            )
        else:
            stored_count = 0

        await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='workout',
            status=SyncStatus.SUCCESS,
            records_synced=stored_count,
        )

        workout_data_limited = workout_records[:limit] if workout_records else []

        return {
            'status': 'success',
            'data': workout_data_limited,
            'metadata': {
                'source': 'whoop_api',
                'record_count': len(workout_data_limited),
                'synced_at': datetime.now(timezone.utc).isoformat(),
            },
        }

    except Exception as e:
        logger.error('✗ Workout sync failed', user_id=current_user, error=str(e))

        await sync_service.log_sync_attempt(
            user_id=str(current_user),
            data_type='workout',
            status=SyncStatus.FAILED,
            error_message=str(e),
        )

        # Fallback to cache
        try:
            cached_data = await sync_service.get_cached_data(
                user_id=str(current_user),
                data_type='workout',
                limit=limit,
            )
            if cached_data.get('count', 0) > 0:
                return {
                    'status': 'success_with_warning',
                    'data': cached_data['data'],
                    'metadata': {'source': 'stale_cache', 'warning': 'Using stale cache'},
                }
        except:
            pass

        raise HTTPException(status_code=503, detail='Failed to fetch workout data')


@router.get("/all")
async def get_all_data_smart(
    current_user: str = Depends(get_current_user),
    force_refresh: bool = Query(False, description="Force fresh data from WHOOP API"),
    limit: int = Query(10, ge=1, le=100, description="Max records per data type"),
):
    """
    Get ALL WHOOP data (recovery, sleep, cycle, workout) with smart caching.

    Calls all 4 individual smart sync endpoints and combines results.
    Uses same caching logic as individual endpoints.

    Query Parameters:
    - force_refresh: If True, fetch all data fresh from WHOOP API
    - limit: Maximum records per data type (default: 10)

    Returns:
        {
            "status": "success",
            "data": {
                "recovery": [...],
                "sleep": [...],
                "cycle": [...],
                "workout": [...]
            },
            "metadata": {
                "recovery": { "source": "cache" or "whoop_api", ... },
                "sleep": { ... },
                "cycle": { ... },
                "workout": { ... }
            }
        }
    """
    try:
        user_id = str(current_user)
        logger.info('📊 All data request', user_id=user_id, force_refresh=force_refresh)

        # Fetch all 4 data types with error handling
        results = {
            'recovery': None,
            'sleep': None,
            'cycle': None,
            'workout': None,
        }
        metadata = {
            'recovery': {},
            'sleep': {},
            'cycle': {},
            'workout': {},
        }

        # Recovery
        try:
            recovery_response = await get_recovery_data_smart(current_user, force_refresh, limit)
            results['recovery'] = recovery_response.get('data', [])
            metadata['recovery'] = recovery_response.get('metadata', {})
        except Exception as e:
            logger.error('✗ Recovery sync failed in all endpoint', error=str(e))
            results['recovery'] = []
            metadata['recovery'] = {'error': str(e)}

        # Sleep
        try:
            sleep_response = await get_sleep_data_smart(current_user, force_refresh, limit)
            results['sleep'] = sleep_response.get('data', [])
            metadata['sleep'] = sleep_response.get('metadata', {})
        except Exception as e:
            logger.error('✗ Sleep sync failed in all endpoint', error=str(e))
            results['sleep'] = []
            metadata['sleep'] = {'error': str(e)}

        # Cycle
        try:
            cycle_response = await get_cycle_data_smart(current_user, force_refresh, limit)
            results['cycle'] = cycle_response.get('data', [])
            metadata['cycle'] = cycle_response.get('metadata', {})
        except Exception as e:
            logger.error('✗ Cycle sync failed in all endpoint', error=str(e))
            results['cycle'] = []
            metadata['cycle'] = {'error': str(e)}

        # Workout
        try:
            workout_response = await get_workout_data_smart(current_user, force_refresh, limit)
            results['workout'] = workout_response.get('data', [])
            metadata['workout'] = workout_response.get('metadata', {})
        except Exception as e:
            logger.error('✗ Workout sync failed in all endpoint', error=str(e))
            results['workout'] = []
            metadata['workout'] = {'error': str(e)}

        logger.info('✓ All data synced successfully', user_id=user_id)

        return {
            'status': 'success',
            'data': results,
            'metadata': metadata,
        }

    except Exception as e:
        logger.error('✗ All data sync failed', user_id=current_user, error=str(e))
        raise HTTPException(status_code=503, detail=f'Failed to fetch all data: {str(e)}')


@router.get("/sync-status")
async def get_sync_status(
    current_user: str = Depends(get_current_user),
):
    """
    Get sync status for all data types.

    Shows when each data type was last synced and whether it needs fresh data.
    Useful for UI to display sync state and determine refresh priority.

    Returns:
        {
            "user_id": str,
            "sync_status": {
                "recovery": { "last_sync_at": "...", "needs_sync": bool, ... },
                "sleep": { ... },
                "cycle": { ... },
                "workout": { ... }
            },
            "check_timestamp": ISO datetime
        }
    """
    try:
        user_id = str(current_user)

        logger.info('📊 Getting sync status for all data types', user_id=user_id)

        result = await sync_service.get_sync_status_all(user_id)

        logger.info(
            '✓ Sync status retrieved',
            user_id=user_id,
            data_types=list(result['sync_status'].keys()),
        )

        return result

    except Exception as e:
        logger.error('✗ Failed to get sync status', user_id=current_user, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
