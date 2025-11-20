"""
Entry point for WHOOP API Service
Run from project root: python start.py
"""
import uvicorn
from app.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development
    )
