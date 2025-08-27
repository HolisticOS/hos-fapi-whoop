from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Basic app config
    PORT: int = 8001
    ENVIRONMENT: str = "development"
    
    # Whoop API
    WHOOP_CLIENT_ID: str
    WHOOP_CLIENT_SECRET: str
    WHOOP_REDIRECT_URL: str
    
    # Database
    DATABASE_URL: str
    
    # Service security
    SERVICE_API_KEY: str
    
    # Simple rate limiting
    RATE_LIMIT_PER_MINUTE: int = 80
    RATE_LIMIT_PER_DAY: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()