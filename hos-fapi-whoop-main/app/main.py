from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config.settings import settings
from app.api import internal, auth, health

# Simple logging setup
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

# Create FastAPI app
app = FastAPI(
    title="WHOOP MVP Microservice",
    description="Simple WHOOP data integration service",
    version="1.0.0-mvp"
)

# Basic CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(internal.router, prefix="/internal")
app.include_router(auth.router, prefix="/auth")
app.include_router(health.router, prefix="/health")

@app.on_event("startup")
async def startup():
    logger.info("WHOOP MVP Microservice starting")

@app.on_event("shutdown")
async def shutdown():
    logger.info("WHOOP MVP Microservice stopping")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)