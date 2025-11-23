from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config.settings import settings
from app.config.database import init_database, close_database
from app.api import internal, auth, health, raw_data, smart_sync
from app.core.auth import get_current_user

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    version="1.0.0-mvp"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API versioning
app.include_router(health.router, prefix="/health")
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/whoop/auth", tags=["whoop-auth"])
app.include_router(internal.router, prefix=settings.API_V1_STR, tags=["whoop-data"])
app.include_router(raw_data.router, prefix="", tags=["raw-data"])
app.include_router(
    smart_sync.router,
    prefix=f"{settings.API_V1_STR}/smart",
    tags=["smart-sync"],
    dependencies=[Depends(get_current_user)]
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("WHOOP Microservice starting", environment=settings.ENVIRONMENT)
    
    # Initialize database connection with graceful handling
    db_success = await init_database()
    if not db_success:
        logger.warning("Database initialization incomplete - running in degraded mode")
        logger.info("To fix: Run the SQL migration script in /migrations/001_create_whoop_tables.sql")
    else:
        logger.info("Database initialized successfully")
    
    logger.info("WHOOP Microservice started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("WHOOP Microservice shutting down")
    await close_database()
    logger.info("WHOOP Microservice stopped")

@app.get("/")
async def root():
    return {
        "message": "WHOOP Health Metrics API",
        "version": "1.0.0-mvp",
        "docs": "/docs" if settings.is_development else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development
    )