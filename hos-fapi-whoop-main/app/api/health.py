from fastapi import APIRouter

router = APIRouter()

@router.get("/ready")
async def health_ready():
    """Service readiness check"""
    return {"status": "ready", "service": "whoop-microservice"}

@router.get("/live") 
async def health_live():
    """Service liveness check"""
    return {"status": "alive", "service": "whoop-microservice"}