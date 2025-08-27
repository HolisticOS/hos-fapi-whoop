from fastapi import APIRouter, HTTPException
import structlog
from app.config.database import get_supabase_client

router = APIRouter()
logger = structlog.get_logger(__name__)

@router.get("/ready")
async def health_ready():
    """Service readiness check - ensures service and database are ready"""
    try:
        # Test database connectivity
        supabase = get_supabase_client()
        result = supabase.table("whoop_users").select("*").limit(1).execute()
        
        return {
            "status": "ready",
            "database": "connected",
            "service": "whoop-microservice"
        }
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")

@router.get("/live") 
async def health_live():
    """Service liveness check - basic service health"""
    return {
        "status": "alive",
        "service": "whoop-microservice",
        "version": "1.0.0-mvp"
    }

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy"}