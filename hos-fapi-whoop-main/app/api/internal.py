"""
Internal WHOOP Health Metrics API Endpoints
Provides comprehensive health data access and synchronization
Integrates with Supabase JWT authentication
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends, Header
from typing import Optional, List
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
import structlog

from app.services.whoop_service import WhoopAPIService
from app.models.database import WhoopDataService
from app.core.auth import get_current_user

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
whoop_client = WhoopAPIService()
data_service = WhoopDataService()


@router.get("/health-metrics")
async def get_health_metrics(
    current_user: str = Depends(get_current_user),
    start_date: Optional[date] = Query(None, description="Start date for data range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for data range (YYYY-MM-DD)"),
    metric_types: Optional[str] = Query("recovery,sleep,workout", description="Comma-separated list of metric types"),
    source: str = Query("database", description="Data source: 'database', 'whoop', or 'both'"),
    days_back: int = Query(7, ge=1, le=30, description="Days of historical data (1-30)")
):
    """
    Get comprehensive health metrics for authenticated user from database and/or WHOOP API

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Args:
        start_date: Optional start date (defaults to days_back from today)
        end_date: Optional end date (defaults to today)
        metric_types: Comma-separated metric types (recovery,sleep,workout)
        source: Data source preference (database/whoop/both)
        days_back: Days of historical data if dates not specified

    Returns:
        Comprehensive health metrics data
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        logger.info("📊 Getting health metrics",
                   user_id=current_user,
                   source=source,
                   metric_types=metric_types,
                   days_back=days_back)

        # Calculate date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=days_back)

        # Parse requested metric types
        requested_types = [t.strip() for t in metric_types.split(",")] if metric_types else ["recovery", "sleep", "workout"]

        result = {
            "user_id": current_user,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days + 1
            },
            "requested_metrics": requested_types,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Get data based on source preference
        if source in ["database", "both"]:
            logger.info("📖 Fetching data from database")
            db_data = await data_service.get_comprehensive_health_data(user_uuid, start_date, end_date)
            result["database_data"] = db_data

        if source in ["whoop", "both"]:
            logger.info("🏃‍♂️ Fetching data from WHOOP API")
            api_data = await whoop_client.get_comprehensive_data(user_uuid, days_back=(end_date - start_date).days + 1)
            result["whoop_data"] = api_data

        # If both sources requested, provide unified view
        if source == "both" and "database_data" in result and "whoop_data" in result:
            result["unified_data"] = _merge_data_sources(result["database_data"], result["whoop_data"])

        logger.info("✅ Health metrics retrieved successfully",
                   user_id=current_user,
                   date_range=f"{start_date} to {end_date}")

        return result

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get health metrics",
                    user_id=current_user, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve health metrics: {str(e)}"
        )


@router.get("/data/recovery")
async def get_recovery_data(
    current_user: str = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30, description="Days of historical data")
):
    """
    Get authenticated user's recovery data from WHOOP API

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Args:
        days: Number of days of recovery data

    Returns:
        Recovery data from WHOOP API
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        logger.info("💚 Getting recovery data", user_id=current_user, days=days)

        # Get recovery data from WHOOP API
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        # Convert UUID to string for API service
        recovery_collection = await whoop_client.get_recovery_data(str(user_uuid), start_iso, end_iso, limit=10)

        logger.info("✅ Recovery data retrieved",
                   user_id=current_user,
                   recovery_count=len(recovery_collection.records))

        return {
            "user_id": current_user,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "recovery_data": [r.model_dump() if hasattr(r, 'model_dump') else r for r in recovery_collection.records],
            "summary": {
                "recovery_records": len(recovery_collection.records),
                "has_next_page": bool(recovery_collection.next_token)
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get recovery data", user_id=current_user, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve recovery data: {str(e)}"
        )


@router.get("/data/sleep")
async def get_sleep_data(
    current_user: str = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30, description="Days of historical data")
):
    """
    Get authenticated user's sleep data from WHOOP API

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Args:
        days: Number of days of sleep data

    Returns:
        Sleep data from WHOOP API
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        logger.info("😴 Getting sleep data", user_id=current_user, days=days)

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        # Convert UUID to string for API service
        sleep_collection = await whoop_client.get_sleep_data(str(user_uuid), start_iso, end_iso, limit=10)

        logger.info("✅ Sleep data retrieved",
                   user_id=current_user,
                   records_count=len(sleep_collection.records))

        return {
            "user_id": current_user,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "sleep_data": [s.model_dump() if hasattr(s, 'model_dump') else s for s in sleep_collection.records],
            "summary": {
                "sleep_records": len(sleep_collection.records),
                "has_next_page": bool(sleep_collection.next_token)
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get sleep data", user_id=current_user, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sleep data: {str(e)}"
        )


@router.get("/data/workouts")
async def get_workout_data(
    current_user: str = Depends(get_current_user),
    days: int = Query(7, ge=1, le=30, description="Days of historical data")
):
    """
    Get authenticated user's workout data from WHOOP API

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Args:
        days: Number of days of workout data

    Returns:
        Workout data from WHOOP API
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        logger.info("🏋️‍♂️ Getting workout data", user_id=current_user, days=days)

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        # Convert UUID to string for API service
        workout_collection = await whoop_client.get_workout_data(str(user_uuid), start_iso, end_iso, limit=10)

        logger.info("✅ Workout data retrieved",
                   user_id=current_user,
                   records_count=len(workout_collection.records))

        return {
            "user_id": current_user,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "workout_data": [w.model_dump() if hasattr(w, 'model_dump') else w for w in workout_collection.records],
            "summary": {
                "workout_records": len(workout_collection.records),
                "has_next_page": bool(workout_collection.next_token)
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get workout data", user_id=current_user, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve workout data: {str(e)}"
        )




@router.post("/sync")
async def sync_user_data(
    current_user: str = Depends(get_current_user),
    data_types: Optional[str] = Query("recovery,sleep,workout,cycle", description="Comma-separated data types to sync"),
    days_back: int = Query(7, ge=1, le=30, description="Days of data to sync (1-30)"),
    force_refresh: bool = Query(False, description="Force refresh even if recently synced")
):
    """
    Sync authenticated user's WHOOP data from API to database

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Args:
        data_types: Comma-separated data types (recovery,sleep,workout,cycle)
        days_back: Number of days to sync
        force_refresh: Force sync even if recently synced

    Returns:
        Sync status and statistics
    """
    try:
        # Convert string UUID to UUID type
        user_uuid = UUID(current_user)

        logger.info("🔄 Starting data sync",
                   user_id=current_user,
                   data_types=data_types,
                   days_back=days_back,
                   force_refresh=force_refresh)

        # Parse data types
        sync_types = [t.strip() for t in data_types.split(",")] if data_types else ["recovery", "sleep", "workout", "cycle"]

        # Calculate date range for API
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        logger.info("🔄 Starting API data sync",
                   user_id=current_user,
                   start_date=start_iso,
                   end_date=end_iso)

        # Fetch comprehensive data using API with UUID
        # Convert UUID to string for the API service
        # Use limit based on days_back to get approximately one record per day
        data_response = await whoop_client.get_comprehensive_data(
            user_id=str(user_uuid),
            days_back=days_back,
            include_all_pages=False  # Don't fetch all pages, respect the limit
        )

        # Store data in database using repository
        from app.repositories.whoop_data_repository import WhoopDataRepository
        from app.db.supabase_client import get_supabase

        supabase = get_supabase()
        repo = WhoopDataRepository(supabase.get_client())

        # Store recovery data
        recovery_stored = 0
        if "recovery" in sync_types and data_response.recovery_data:
            logger.info(f"🔍 Recovery data_response has {len(data_response.recovery_data)} records", user_id=current_user)

            # Debug: Check what's in the recovery data
            for i, r in enumerate(data_response.recovery_data[:2]):  # Check first 2 records
                logger.info(f"🔍 Recovery record {i}: has_raw_data={hasattr(r, 'raw_data')}, raw_data_type={type(r.raw_data) if hasattr(r, 'raw_data') else 'N/A'}, raw_data_empty={len(r.raw_data) == 0 if hasattr(r, 'raw_data') else 'N/A'}", user_id=current_user)

            recovery_records = [r.raw_data for r in data_response.recovery_data if hasattr(r, 'raw_data') and r.raw_data]
            logger.info(f"💾 Extracted {len(recovery_records)} recovery records with raw_data (from {len(data_response.recovery_data)} total)", user_id=current_user)

            if recovery_records:
                logger.info(f"💾 Storing {len(recovery_records)} recovery records to whoop_recovery table", user_id=current_user)
                recovery_stored = await repo.store_recovery_records(user_uuid, recovery_records)
                logger.info(f"✅ Stored {recovery_stored} recovery records", user_id=current_user)
            else:
                logger.warning(f"⚠️ No recovery records to store - raw_data extraction returned empty list", user_id=current_user)
        else:
            logger.warning(f"⚠️ Skipping recovery storage",
                          in_sync_types="recovery" in sync_types,
                          has_data=bool(data_response.recovery_data),
                          recovery_count=len(data_response.recovery_data) if data_response.recovery_data else 0,
                          user_id=current_user)

        # Store sleep data
        sleep_stored = 0
        if "sleep" in sync_types and data_response.sleep_data:
            logger.info(f"🔍 Sleep data_response has {len(data_response.sleep_data)} records", user_id=current_user)

            # Debug: Check first record
            if data_response.sleep_data:
                s = data_response.sleep_data[0]
                logger.info(f"🔍 Sleep record 0: has_raw_data={hasattr(s, 'raw_data')}, raw_data_type={type(s.raw_data) if hasattr(s, 'raw_data') else 'N/A'}, raw_data_empty={len(s.raw_data) == 0 if hasattr(s, 'raw_data') else 'N/A'}", user_id=current_user)

            sleep_records = [s.raw_data for s in data_response.sleep_data if hasattr(s, 'raw_data') and s.raw_data]
            logger.info(f"💾 Extracted {len(sleep_records)} sleep records with raw_data (from {len(data_response.sleep_data)} total)", user_id=current_user)

            if sleep_records:
                logger.info(f"💾 Storing {len(sleep_records)} sleep records to whoop_sleep table", user_id=current_user)
                sleep_stored = await repo.store_sleep_records(user_uuid, sleep_records)
                logger.info(f"✅ Stored {sleep_stored} sleep records", user_id=current_user)
            else:
                logger.warning(f"⚠️ No sleep records to store - raw_data extraction returned empty list", user_id=current_user)
        else:
            logger.warning(f"⚠️ Skipping sleep storage",
                          in_sync_types="sleep" in sync_types,
                          has_data=bool(data_response.sleep_data),
                          sleep_count=len(data_response.sleep_data) if data_response.sleep_data else 0,
                          user_id=current_user)

        # Store workout data
        workout_stored = 0
        if "workout" in sync_types and data_response.workout_data:
            logger.info(f"🔍 Workout data_response has {len(data_response.workout_data)} records", user_id=current_user)

            # Debug: Check first record
            if data_response.workout_data:
                w = data_response.workout_data[0]
                logger.info(f"🔍 Workout record 0: has_raw_data={hasattr(w, 'raw_data')}, raw_data_type={type(w.raw_data) if hasattr(w, 'raw_data') else 'N/A'}, raw_data_empty={len(w.raw_data) == 0 if hasattr(w, 'raw_data') else 'N/A'}", user_id=current_user)

            workout_records = [w.raw_data for w in data_response.workout_data if hasattr(w, 'raw_data') and w.raw_data]
            logger.info(f"💾 Extracted {len(workout_records)} workout records with raw_data (from {len(data_response.workout_data)} total)", user_id=current_user)

            if workout_records:
                logger.info(f"💾 Storing {len(workout_records)} workout records to whoop_workout table", user_id=current_user)
                workout_stored = await repo.store_workout_records(user_uuid, workout_records)
                logger.info(f"✅ Stored {workout_stored} workout records", user_id=current_user)
            else:
                logger.warning(f"⚠️ No workout records to store - raw_data extraction returned empty list", user_id=current_user)
        else:
            logger.warning(f"⚠️ Skipping workout storage",
                          in_sync_types="workout" in sync_types,
                          has_data=bool(data_response.workout_data),
                          workout_count=len(data_response.workout_data) if data_response.workout_data else 0,
                          user_id=current_user)

        # Store cycle data (now included in comprehensive data response)
        cycle_stored = 0
        if "cycle" in sync_types and data_response.cycle_data:
            logger.info(f"🔍 Cycle data_response has {len(data_response.cycle_data)} records", user_id=current_user)

            # Debug: Check first record
            if data_response.cycle_data:
                c = data_response.cycle_data[0]
                logger.info(f"🔍 Cycle record 0: has_raw_data={hasattr(c, 'raw_data')}, raw_data_type={type(c.raw_data) if hasattr(c, 'raw_data') else 'N/A'}, raw_data_empty={len(c.raw_data) == 0 if hasattr(c, 'raw_data') and c.raw_data else 'N/A'}", user_id=current_user)

            cycle_records = [c.raw_data for c in data_response.cycle_data if hasattr(c, 'raw_data') and c.raw_data]
            logger.info(f"💾 Extracted {len(cycle_records)} cycle records with raw_data (from {len(data_response.cycle_data)} total)", user_id=current_user)

            if cycle_records:
                logger.info(f"💾 Storing {len(cycle_records)} cycle records to whoop_cycle table", user_id=current_user)
                cycle_stored = await repo.store_cycle_records(user_uuid, cycle_records)
                logger.info(f"✅ Stored {cycle_stored} cycle records", user_id=current_user)
            else:
                logger.warning(f"⚠️ No cycle records to store - raw_data extraction returned empty list", user_id=current_user)
        else:
            logger.warning(f"⚠️ Skipping cycle storage",
                          in_sync_types="cycle" in sync_types,
                          has_data=bool(data_response.cycle_data),
                          cycle_count=len(data_response.cycle_data) if data_response.cycle_data else 0,
                          user_id=current_user)

        total_stored = recovery_stored + sleep_stored + workout_stored + cycle_stored

        # Update sync log for each data type
        if "recovery" in sync_types:
            await repo.update_sync_log(user_uuid, 'recovery', recovery_stored, 'success')
        if "sleep" in sync_types:
            await repo.update_sync_log(user_uuid, 'sleep', sleep_stored, 'success')
        if "workout" in sync_types:
            await repo.update_sync_log(user_uuid, 'workout', workout_stored, 'success')
        if "cycle" in sync_types:
            await repo.update_sync_log(user_uuid, 'cycle', cycle_stored, 'success')

        sync_results = {
            "user_id": current_user,
            "sync_timestamp": datetime.utcnow().isoformat(),
            "requested_types": sync_types,
            "days_synced": days_back,
            "force_refresh": force_refresh,
            "api_version": "v2",
            "data_summary": {
                "recovery_records": len(data_response.recovery_data) if data_response.recovery_data else 0,
                "sleep_records": len(data_response.sleep_data) if data_response.sleep_data else 0,
                "workout_records": len(data_response.workout_data) if data_response.workout_data else 0,
                "cycle_records": len(data_response.cycle_data) if data_response.cycle_data else 0,
                "total_records": data_response.total_records
            },
            "storage_summary": {
                "recovery_stored": recovery_stored,
                "sleep_stored": sleep_stored,
                "workouts_stored": workout_stored,
                "cycles_stored": cycle_stored,
                "total_stored": total_stored
            }
        }

        # Determine overall status
        if total_stored > 0:
            sync_results["status"] = "success"
            sync_results["message"] = f"Data sync completed successfully. Stored {total_stored} records."
        else:
            sync_results["status"] = "no_new_data"
            sync_results["message"] = "No new data to sync. All records already exist."

        logger.info("✅ Data sync completed",
                   user_id=current_user,
                   synced_types=sync_types,
                   total_stored=total_stored)

        return sync_results

    except ValueError as e:
        logger.error("Invalid UUID format", user_id=current_user, error=str(e))
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Data sync failed", user_id=current_user, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data: {str(e)}"
        )


@router.get("/client-status")
async def get_client_status(current_user: str = Depends(get_current_user)):
    """
    Get WHOOP API client status and configuration for authenticated user

    Requires:
        Authorization: Bearer <supabase_jwt_token>

    Returns:
        Client status, rate limiting, and configuration information
    """
    try:
        logger.info("📊 Getting client status", user_id=current_user)

        client_status = whoop_client.get_service_status()

        return {
            "service_status": "operational",
            "whoop_client": client_status,
            "user_id": current_user,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("❌ Failed to get client status", user_id=current_user, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get client status: {str(e)}"
        )


def _merge_data_sources(db_data: dict, api_data: dict) -> dict:
    """
    Merge database and API data sources for unified view
    
    Args:
        db_data: Data from database
        api_data: Data from WHOOP API
        
    Returns:
        Merged data with source attribution
    """
    try:
        merged = {
            "sources": ["database", "whoop_api"],
            "merge_timestamp": datetime.utcnow().isoformat(),
            "data_freshness": {
                "database": db_data.get("last_sync", {}),
                "api": api_data.get("fetch_timestamp")
            }
        }
        
        # Merge recovery data (API data takes precedence)
        merged["recovery"] = api_data.get("recovery", []) or db_data.get("recovery", [])
        
        # Merge sleep data
        merged["sleep"] = api_data.get("sleep", []) or db_data.get("sleep", [])
        
        # Merge workout data  
        merged["workouts"] = api_data.get("workouts", []) or db_data.get("workouts", [])
        
        # Include profile from API if available
        merged["profile"] = api_data.get("profile") or db_data.get("profile")
        
        # Summary statistics
        merged["summary"] = {
            "recovery_count": len(merged["recovery"]),
            "sleep_count": len(merged["sleep"]),
            "workout_count": len(merged["workouts"]),
            "data_source_priority": "whoop_api_first"
        }
        
        return merged
        
    except Exception as e:
        logger.error("❌ Failed to merge data sources", error=str(e))
        return {
            "error": f"Data merge failed: {str(e)}",
            "database_data": db_data,
            "api_data": api_data
        }