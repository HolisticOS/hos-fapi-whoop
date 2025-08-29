import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Cache TTL in seconds
    CACHE_TTL_OVERVIEW: int = int(os.getenv("CACHE_TTL_OVERVIEW", "300").split()[0])
    CACHE_TTL_METRICS: int = int(os.getenv("CACHE_TTL_METRICS", "600").split()[0])
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "WHOOP Health Metrics API"
    
    # Internal API Security
    SERVICE_API_KEY: str = os.getenv("SERVICE_API_KEY", "dev-api-key-change-in-production")
    
    # WHOOP Integration Settings
    WHOOP_CLIENT_ID: str = os.getenv("WHOOP_CLIENT_ID", "")
    WHOOP_CLIENT_SECRET: str = os.getenv("WHOOP_CLIENT_SECRET", "")
    WHOOP_REDIRECT_URL: str = os.getenv("WHOOP_REDIRECT_URL", "")
    WHOOP_WEBHOOK_SECRET: str = os.getenv("WHOOP_WEBHOOK_SECRET", "")
    WHOOP_ACCESS_TOKEN: str = os.getenv("WHOOP_ACCESS_TOKEN", "")
    WHOOP_API_BASE_URL: str = os.getenv("WHOOP_API_BASE_URL", "https://api.prod.whoop.com/developer/v2/")
    
    # WHOOP API Settings
    WHOOP_API_VERSION: str = "v2"
    WHOOP_SUPPORTS_UUIDS: bool = True
    WHOOP_BACKWARD_COMPATIBILITY: bool = False
    
    # API endpoints with UUID support
    WHOOP_SLEEP_ENDPOINT: str = "activity/sleep"
    WHOOP_WORKOUT_ENDPOINT: str = "activity/workout"
    WHOOP_RECOVERY_ENDPOINT: str = "recovery"
    
    # WHOOP API Rate Limiting Settings
    WHOOP_RATE_LIMIT_DELAY: float = float(os.getenv("WHOOP_RATE_LIMIT_DELAY", "0.6"))  # 600ms between requests
    WHOOP_MAX_RETRIES: int = int(os.getenv("WHOOP_MAX_RETRIES", "3"))
    WHOOP_RETRY_BASE_DELAY: float = float(os.getenv("WHOOP_RETRY_BASE_DELAY", "2.0"))  # Initial retry delay
    WHOOP_REQUEST_TIMEOUT: int = int(os.getenv("WHOOP_REQUEST_TIMEOUT", "30"))  # Request timeout in seconds
    
    # Rate Limiting (100/min, 10K/day as per WHOOP API docs)
    WHOOP_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("WHOOP_RATE_LIMIT_PER_MINUTE", "100"))
    WHOOP_RATE_LIMIT_PER_DAY: int = int(os.getenv("WHOOP_RATE_LIMIT_PER_DAY", "10000"))
    
    # Service-to-Service Authentication
    SERVICE_API_KEY: str = os.getenv("SERVICE_API_KEY", "")
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()