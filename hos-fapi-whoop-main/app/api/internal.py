"""
Internal WHOOP Health Metrics API Endpoints
Provides comprehensive health data access and synchronization
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends, Header
from typing import Optional, List
from datetime import date, datetime, timedelta
import structlog

from app.services.whoop_api_client import WhoopAPIClient
from app.services.oauth_service import WhoopOAuthService
from app.models.database import WhoopDataService
from app.models.schemas import HealthMetricsRequest, HealthMetricsResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
whoop_client = WhoopAPIClient()
oauth_service = WhoopOAuthService()
data_service = WhoopDataService()


# Simple API key authentication for internal services
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify internal API key for service-to-service communication"""
    from app.config.settings import settings
    expected_key = getattr(settings, 'SERVICE_API_KEY', 'dev-api-key-change-in-production')
    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


async def verify_user_connection(user_id: str) -> bool:
    """Dependency to verify user has active WHOOP connection"""
    status = await oauth_service.get_connection_status(user_id)
    if not status.get("connected", False):
        raise HTTPException(
            status_code=404,
            detail=f"No active WHOOP connection found for user {user_id}"
        )
    return True


@router.get("/health-metrics/{user_id}")
async def get_health_metrics(
    user_id: str = Path(..., description="User ID to get health metrics for"),
    start_date: Optional[date] = Query(None, description="Start date for data range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for data range (YYYY-MM-DD)"),
    metric_types: Optional[str] = Query("recovery,sleep,workout", description="Comma-separated list of metric types"),
    source: str = Query("database", description="Data source: 'database', 'whoop', or 'both'"),
    days_back: int = Query(7, ge=1, le=30, description="Days of historical data (1-30)"),
    auth: str = Depends(verify_api_key),
    _: bool = Depends(verify_user_connection)
):
    """
    Get comprehensive health metrics for user from database and/or WHOOP API
    
    Args:
        user_id: User identifier
        start_date: Optional start date (defaults to days_back from today)
        end_date: Optional end date (defaults to today)
        metric_types: Comma-separated metric types (recovery,sleep,workout)
        source: Data source preference (database/whoop/both)
        days_back: Days of historical data if dates not specified
        
    Returns:
        Comprehensive health metrics data
    """
    try:
        logger.info("📊 Getting health metrics", 
                   user_id=user_id, 
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
            "user_id": user_id,
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
            db_data = await data_service.get_comprehensive_health_data(user_id, start_date, end_date)
            result["database_data"] = db_data
        
        if source in ["whoop", "both"]:
            logger.info("🏃‍♂️ Fetching data from WHOOP API")
            api_data = await whoop_client.get_comprehensive_user_data(user_id, days_back=(end_date - start_date).days + 1)
            result["whoop_data"] = api_data
        
        # If both sources requested, provide unified view
        if source == "both" and "database_data" in result and "whoop_data" in result:
            result["unified_data"] = _merge_data_sources(result["database_data"], result["whoop_data"])
        
        logger.info("✅ Health metrics retrieved successfully", 
                   user_id=user_id,
                   date_range=f"{start_date} to {end_date}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get health metrics", 
                    user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve health metrics: {str(e)}"
        )


@router.get("/data/recovery/{user_id}")
async def get_recovery_data(
    user_id: str = Path(..., description="User ID to get recovery data for"),
    days: int = Query(7, ge=1, le=30, description="Days of historical data"),
    auth: str = Depends(verify_api_key),
    _: bool = Depends(verify_user_connection)
):
    """
    Get user's recovery data from WHOOP API
    
    Args:
        user_id: User identifier
        days: Number of days of recovery data
        
    Returns:
        Recovery data from WHOOP API
    """
    try:
        logger.info("💚 Getting recovery data", user_id=user_id, days=days)
        
        # Get cycles first, then recovery data for each
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        cycles = await whoop_client.get_cycles(user_id, limit=days * 2, start=start_date, end=end_date)
        
        recovery_data = []
        for cycle in cycles:
            if 'id' in cycle:
                recovery = await whoop_client.get_recovery_data(user_id, cycle['id'])
                if recovery:
                    recovery_data.append({
                        "cycle": cycle,
                        "recovery": recovery.model_dump()
                    })
        
        logger.info("✅ Recovery data retrieved", 
                   user_id=user_id, 
                   cycles_count=len(cycles),
                   recovery_count=len(recovery_data))
        
        return {
            "user_id": user_id,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "cycles": cycles,
            "recovery_data": recovery_data,
            "summary": {
                "cycles_found": len(cycles),
                "recovery_records": len(recovery_data)
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get recovery data", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve recovery data: {str(e)}"
        )


@router.get("/data/sleep/{user_id}")
async def get_sleep_data(
    user_id: str = Path(..., description="User ID to get sleep data for"),
    days: int = Query(7, ge=1, le=30, description="Days of historical data"),
    auth: str = Depends(verify_api_key),
    _: bool = Depends(verify_user_connection)
):
    """
    Get user's sleep data from WHOOP API
    
    Args:
        user_id: User identifier  
        days: Number of days of sleep data
        
    Returns:
        Sleep data from WHOOP API
    """
    try:
        logger.info("😴 Getting sleep data", user_id=user_id, days=days)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        sleep_data = await whoop_client.get_sleep_activities(user_id, limit=days * 2, start=start_date, end=end_date)
        
        logger.info("✅ Sleep data retrieved", 
                   user_id=user_id, 
                   records_count=len(sleep_data))
        
        return {
            "user_id": user_id,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "sleep_data": [s.model_dump() for s in sleep_data],
            "summary": {
                "sleep_records": len(sleep_data),
                "total_sleep_hours": sum(s.duration_seconds or 0 for s in sleep_data) / 3600 if sleep_data else 0
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get sleep data", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sleep data: {str(e)}"
        )


@router.get("/data/workouts/{user_id}")
async def get_workout_data(
    user_id: str = Path(..., description="User ID to get workout data for"),
    days: int = Query(7, ge=1, le=30, description="Days of historical data"),
    auth: str = Depends(verify_api_key),
    _: bool = Depends(verify_user_connection)
):
    """
    Get user's workout data from WHOOP API
    
    Args:
        user_id: User identifier
        days: Number of days of workout data
        
    Returns:
        Workout data from WHOOP API
    """
    try:
        logger.info("🏋️‍♂️ Getting workout data", user_id=user_id, days=days)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        workout_data = await whoop_client.get_workout_activities(user_id, limit=days * 4, start=start_date, end=end_date)
        
        logger.info("✅ Workout data retrieved", 
                   user_id=user_id, 
                   records_count=len(workout_data))
        
        return {
            "user_id": user_id,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "workout_data": [w.model_dump() for w in workout_data],
            "summary": {
                "workout_records": len(workout_data),
                "total_strain": sum(w.strain or 0 for w in workout_data) if workout_data else 0,
                "total_duration_hours": sum(w.duration_seconds or 0 for w in workout_data) / 3600 if workout_data else 0
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get workout data", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve workout data: {str(e)}"
        )


@router.get("/auth/status/{user_id}")
async def check_connection_status(
    user_id: str = Path(..., description="User ID to check connection status for"),
    auth: str = Depends(verify_api_key)
):
    """
    Check if user has active WHOOP connection
    
    Args:
        user_id: User identifier
        
    Returns:
        Detailed connection status
    """
    try:
        logger.info("📊 Checking connection status", user_id=user_id)
        
        status = await oauth_service.get_connection_status(user_id)
        
        return {
            "user_id": user_id,
            "connection_status": status,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("❌ Connection status check failed", 
                    user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check connection status: {str(e)}"
        )


@router.post("/auth/connect/{user_id}")
async def initiate_connection(
    user_id: str = Path(..., description="User ID to initiate connection for"),
    auth: str = Depends(verify_api_key)
):
    """
    Initiate OAuth connection for user
    
    Args:
        user_id: User identifier
        
    Returns:
        OAuth authorization URL and state for connection
    """
    try:
        logger.info("🔐 Initiating OAuth connection", user_id=user_id)
        
        # Use default comprehensive scopes
        auth_response = await oauth_service.initiate_oauth_flow(user_id)
        
        return {
            "user_id": user_id,
            "oauth_flow": auth_response.model_dump(),
            "initiated_at": datetime.utcnow().isoformat(),
            "instructions": "Redirect user to authorization_url to complete OAuth flow"
        }
        
    except Exception as e:
        logger.error("❌ OAuth connection initiation failed", 
                    user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate OAuth connection: {str(e)}"
        )


@router.post("/sync/{user_id}")
async def sync_user_data(
    user_id: str = Path(..., description="User ID to sync data for"),
    data_types: Optional[str] = Query("recovery,sleep,workout", description="Comma-separated data types to sync"),
    days_back: int = Query(7, ge=1, le=30, description="Days of data to sync (1-30)"),
    force_refresh: bool = Query(False, description="Force refresh even if recently synced"),
    auth: str = Depends(verify_api_key),
    _: bool = Depends(verify_user_connection)
):
    """
    Sync user's WHOOP data from API to database
    
    Args:
        user_id: User identifier
        data_types: Comma-separated data types (recovery,sleep,workout)
        days_back: Number of days to sync
        force_refresh: Force sync even if recently synced
        
    Returns:
        Sync status and statistics
    """
    try:
        logger.info("🔄 Starting data sync", 
                   user_id=user_id, 
                   data_types=data_types,
                   days_back=days_back,
                   force_refresh=force_refresh)
        
        # Parse data types
        sync_types = [t.strip() for t in data_types.split(",")] if data_types else ["recovery", "sleep", "workout"]
        
        # Get fresh data from WHOOP API
        whoop_data = await whoop_client.get_comprehensive_user_data(user_id, days_back=days_back)
        
        if "error" in whoop_data:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch data from WHOOP API: {whoop_data['error']}"
            )
        
        sync_results = {
            "user_id": user_id,
            "sync_timestamp": datetime.utcnow().isoformat(),
            "requested_types": sync_types,
            "days_synced": days_back,
            "force_refresh": force_refresh,
            "results": {}
        }
        
        # TODO: Implement actual data sync to database
        # This would involve parsing whoop_data and storing to database
        # using the repository classes from database.py
        
        # For now, return the fetched data structure
        sync_results["whoop_api_data"] = whoop_data
        sync_results["status"] = "success"
        sync_results["message"] = "Data sync completed successfully (API fetch only - database storage pending)"
        
        logger.info("✅ Data sync completed", 
                   user_id=user_id,
                   synced_types=sync_types)
        
        return sync_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Data sync failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data: {str(e)}"
        )


@router.get("/client-status")
async def get_client_status(auth: str = Depends(verify_api_key)):
    """
    Get WHOOP API client status and configuration
    
    Returns:
        Client status, rate limiting, and configuration information
    """
    try:
        logger.info("📊 Getting client status")
        
        client_status = whoop_client.get_client_status()
        
        return {
            "service_status": "operational",
            "whoop_client": client_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("❌ Failed to get client status", error=str(e))
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