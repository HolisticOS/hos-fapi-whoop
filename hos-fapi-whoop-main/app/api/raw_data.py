"""
Raw WHOOP Data API endpoints
Simple endpoints to view stored data
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import structlog

from app.services.raw_data_storage import WhoopRawDataStorage

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/raw-data", tags=["Raw Data"])

@router.get("/summary/{user_id}")
async def get_user_data_summary(user_id: str) -> Dict[str, Any]:
    """
    Get summary of stored WHOOP data for a user
    
    Args:
        user_id: Internal user ID (e.g., 'user002')
        
    Returns:
        Summary of stored data by type
    """
    try:
        storage = WhoopRawDataStorage()
        summary = await storage.get_user_summary(user_id)
        
        return {
            "user_id": user_id,
            "data_summary": summary,
            "total_types": len(summary)
        }
        
    except Exception as e:
        logger.error("Failed to get user summary", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest/{user_id}/{data_type}")
async def get_latest_data(
    user_id: str,
    data_type: str,
    limit: int = Query(1, ge=1, le=10, description="Number of latest entries to return")
) -> Dict[str, Any]:
    """
    Get the latest stored data for a user and type
    
    Args:
        user_id: Internal user ID
        data_type: Type of data (sleep, recovery, workout, cycle, profile)
        limit: Number of latest entries to return
        
    Returns:
        Latest stored data
    """
    try:
        storage = WhoopRawDataStorage()
        data = await storage.get_latest_data(user_id, data_type, limit)
        
        if not data:
            raise HTTPException(
                status_code=404, 
                detail=f"No {data_type} data found for user {user_id}"
            )
        
        return {
            "user_id": user_id,
            "data_type": data_type,
            "data": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get latest data", 
            user_id=user_id, 
            data_type=data_type, 
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/records/{user_id}/{data_type}")
async def get_raw_records(
    user_id: str,
    data_type: str,
    limit: int = Query(1, ge=1, le=5, description="Number of latest entries")
) -> Dict[str, Any]:
    """
    Get just the raw WHOOP records (the actual API data)
    
    Args:
        user_id: Internal user ID  
        data_type: Type of data
        limit: Number of latest entries
        
    Returns:
        Raw WHOOP API records
    """
    try:
        storage = WhoopRawDataStorage()
        data = await storage.get_latest_data(user_id, data_type, limit)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No {data_type} data found for user {user_id}"
            )
        
        # Extract just the records from the stored data
        if isinstance(data, list):
            all_records = []
            for entry in data:
                all_records.extend(entry.get('records', []))
            records = all_records
        else:
            records = data.get('records', [])
        
        return {
            "user_id": user_id,
            "data_type": data_type,
            "record_count": len(records),
            "records": records
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get raw records",
            user_id=user_id,
            data_type=data_type, 
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup/{user_id}")
async def cleanup_old_data(
    user_id: str,
    data_type: Optional[str] = Query(None, description="Specific data type to clean up"),
    keep_latest: int = Query(5, ge=1, le=20, description="Number of latest entries to keep")
) -> Dict[str, Any]:
    """
    Clean up old data for a user
    
    Args:
        user_id: Internal user ID
        data_type: Specific data type to clean up (optional)
        keep_latest: Number of latest entries to keep per type
        
    Returns:
        Cleanup result
    """
    try:
        storage = WhoopRawDataStorage()
        
        if data_type:
            # Clean up specific data type
            success = await storage.cleanup_old_data(user_id, data_type, keep_latest)
            return {
                "user_id": user_id,
                "data_type": data_type,
                "success": success,
                "kept_latest": keep_latest
            }
        else:
            # Clean up all data types
            data_types = ["sleep", "recovery", "workout", "cycle", "profile"]
            results = {}
            
            for dt in data_types:
                results[dt] = await storage.cleanup_old_data(user_id, dt, keep_latest)
            
            return {
                "user_id": user_id,
                "cleanup_results": results,
                "kept_latest_per_type": keep_latest
            }
            
    except Exception as e:
        logger.error("Failed to cleanup data", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))