# hos-fapi-whoop-main - Detailed Microservice Implementation Plan

## 1. Project Structure

```
hos-fapi-whoop-main/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py            # Environment configuration
│   │   └── database.py            # Supabase client setup
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py              # Health check endpoints
│   │   └── internal/              # Internal API endpoints (no auth)
│   │       ├── __init__.py
│   │       ├── data.py           # Data retrieval endpoints
│   │       └── auth.py           # OAuth management endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whoop_service.py       # Core Whoop API client
│   │   ├── oauth_service.py       # OAuth 2.0 flow handler
│   │   ├── data_service.py        # Data processing and storage
│   │   └── cache_service.py       # Simple in-memory caching
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic models for API
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth_utils.py          # OAuth helper functions
│   │   └── date_utils.py          # Date handling utilities
│   └── exceptions/
│       ├── __init__.py
│       └── custom_exceptions.py   # Custom exception classes
├── requirements.txt
├── .env.example
├── docker-compose.yml             # For local development
├── Dockerfile
└── README.md
```

## 2. Core Implementation Files

### 2.1 Main Application (app/main.py)

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.config.settings import settings
from app.api import health
from app.api.internal import data, auth
from app.exceptions.custom_exceptions import WhoopServiceException

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whoop Health Data Service",
    description="Internal microservice for Whoop API integration",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None
)

# Configure CORS for internal service communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Global exception handler
@app.exception_handler(WhoopServiceException)
async def whoop_service_exception_handler(request: Request, exc: WhoopServiceException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "type": "whoop_service_error"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "type": "internal_error"}
    )

# Include routers
app.include_router(health.router)
app.include_router(data.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {
        "service": "hos-fapi-whoop-main",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
```

### 2.2 Configuration (app/config/settings.py)

```python
from pydantic import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Service Configuration
    PROJECT_NAME: str = "Whoop Health Data Service"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    ENVIRONMENT: str = "development"
    
    # Whoop API Configuration
    WHOOP_CLIENT_ID: str
    WHOOP_CLIENT_SECRET: str
    WHOOP_REDIRECT_URL: str
    WHOOP_API_BASE_URL: str = "https://api.prod.whoop.com/developer/v1"
    WHOOP_OAUTH_BASE_URL: str = "https://api.prod.whoop.com/oauth/oauth2"
    
    # Database Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000    # Simple LRU cache size
    
    # Security Configuration
    ALLOWED_ORIGINS: List[str] = ["*"]  # Configure for production
    
    # Rate Limiting (simple)
    WHOOP_API_CALLS_PER_MINUTE: int = 90  # Stay under 100/min limit
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
```

### 2.3 Database Client (app/config/database.py)

```python
from supabase import create_client, Client
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseClient:
    def __init__(self):
        self._client: Client = None
    
    @property
    def client(self) -> Client:
        if self._client is None:
            try:
                self._client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                logger.info("Supabase client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return self._client

# Global database client instance
db = DatabaseClient()
```

### 2.4 Pydantic Models (app/models/schemas.py)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# Request/Response Models
class UserConnectionStatus(BaseModel):
    user_id: str
    connected: bool
    whoop_user_id: Optional[str] = None
    connection_date: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None

class OAuthInitiationResponse(BaseModel):
    authorization_url: str
    state: str

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    user_id: str

# Data Models
class WhoopRecoveryData(BaseModel):
    recovery_score: Optional[Decimal] = Field(None, ge=0, le=100)
    hrv_rmssd: Optional[Decimal] = None
    resting_heart_rate: Optional[int] = None
    skin_temp_celsius: Optional[Decimal] = None
    date: date
    recorded_at: Optional[datetime] = None

class WhoopSleepData(BaseModel):
    sleep_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    efficiency_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    sleep_score: Optional[Decimal] = Field(None, ge=0, le=100)
    date: date

class WhoopWorkoutData(BaseModel):
    workout_id: Optional[str] = None
    sport_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    strain: Optional[Decimal] = Field(None, ge=0, le=21)
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories: Optional[int] = None
    date: date

# Combined Response Models
class UserHealthDataResponse(BaseModel):
    user_id: str
    date: str
    source: str = "whoop"
    recovery: Optional[WhoopRecoveryData] = None
    sleep: Optional[WhoopSleepData] = None
    workouts: Optional[List[WhoopWorkoutData]] = None
    last_updated: datetime

# Error Models
class ErrorResponse(BaseModel):
    error: str
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 2.5 Core Whoop API Service (app/services/whoop_service.py)

```python
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from app.config.settings import settings
from app.exceptions.custom_exceptions import WhoopAPIException, WhoopAuthException

logger = logging.getLogger(__name__)

class WhoopAPIClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = settings.WHOOP_API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Simple rate limiting
        self._last_request_time = 0
        self._min_request_interval = 60 / settings.WHOOP_API_CALLS_PER_MINUTE
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _rate_limit(self):
        """Simple rate limiting"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last_request
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated request to Whoop API"""
        await self._rate_limit()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(method, endpoint, **kwargs)
                
                # Handle authentication errors
                if response.status == 401:
                    raise WhoopAuthException("Invalid or expired access token")
                
                # Handle successful responses
                if response.status in [200, 201]:
                    return await response.json()
                
                # Handle other errors
                error_text = await response.text()
                raise WhoopAPIException(f"API request failed: {response.status} {error_text}")
                
        except aiohttp.ClientError as e:
            raise WhoopAPIException(f"Request failed: {e}")
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile information"""
        return await self._make_request("GET", "/user/profile")
    
    async def get_current_cycle(self) -> Optional[Dict[str, Any]]:
        """Get current cycle data"""
        response = await self._make_request("GET", "/cycle?limit=1")
        cycles = response.get("data", [])
        return cycles[0] if cycles else None
    
    async def get_recovery_by_cycle_id(self, cycle_id: str) -> Dict[str, Any]:
        """Get recovery data for specific cycle"""
        return await self._make_request("GET", f"/cycle/{cycle_id}/recovery")
    
    async def get_sleep_collection(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get sleep data for date range"""
        start_iso = start_date.isoformat()
        end_iso = (end_date + timedelta(days=1)).isoformat()  # Include end date
        
        all_sleep_data = []
        next_token = None
        
        while True:
            params = {
                "start": start_iso,
                "end": end_iso,
                "limit": 25  # Conservative limit for MVP
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            response = await self._make_request("GET", "/activity/sleep", params=params)
            
            sleep_records = response.get("data", [])
            all_sleep_data.extend(sleep_records)
            
            next_token = response.get("next_token")
            if not next_token or len(sleep_records) == 0:
                break
        
        return all_sleep_data
    
    async def get_workout_collection(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get workout data for date range"""
        start_iso = start_date.isoformat()
        end_iso = (end_date + timedelta(days=1)).isoformat()
        
        all_workouts = []
        next_token = None
        
        while True:
            params = {
                "start": start_iso,
                "end": end_iso,
                "limit": 25
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            response = await self._make_request("GET", "/activity/workout", params=params)
            
            workouts = response.get("data", [])
            all_workouts.extend(workouts)
            
            next_token = response.get("next_token")
            if not next_token or len(workouts) == 0:
                break
        
        return all_workouts
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
```

### 2.6 OAuth Service (app/services/oauth_service.py)

```python
import aiohttp
import secrets
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
from app.config.settings import settings
from app.config.database import db
from app.exceptions.custom_exceptions import WhoopOAuthException
import logging

logger = logging.getLogger(__name__)

class WhoopOAuthService:
    def __init__(self):
        self.client_id = settings.WHOOP_CLIENT_ID
        self.client_secret = settings.WHOOP_CLIENT_SECRET
        self.redirect_url = settings.WHOOP_REDIRECT_URL
        self.auth_url = f"{settings.WHOOP_OAUTH_BASE_URL}/auth"
        self.token_url = f"{settings.WHOOP_OAUTH_BASE_URL}/token"
    
    def generate_authorization_url(self, user_id: str) -> Tuple[str, str]:
        """Generate OAuth authorization URL and state"""
        state = f"{user_id}:{secrets.token_urlsafe(16)}"
        
        scopes = [
            "read:profile",
            "read:recovery", 
            "read:sleep",
            "read:workouts",
            "offline"  # For refresh token
        ]
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_url,
            "scope": " ".join(scopes),
            "state": state
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        authorization_url = f"{self.auth_url}?{param_string}"
        
        return authorization_url, state
    
    async def exchange_code_for_tokens(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens"""
        # Extract user_id from state
        try:
            user_id = state.split(":")[0]
        except:
            raise WhoopOAuthException("Invalid state parameter")
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_url,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        
                        # Calculate expiry
                        expires_in = token_data.get("expires_in", 3600)
                        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        
                        # Store tokens in database
                        await self._store_user_tokens(
                            user_id,
                            token_data["access_token"],
                            token_data.get("refresh_token"),
                            expires_at,
                            token_data.get("scope", "")
                        )
                        
                        return {
                            "user_id": user_id,
                            "access_token": token_data["access_token"],
                            "expires_at": expires_at,
                            "success": True
                        }
                    else:
                        error_text = await response.text()
                        raise WhoopOAuthException(f"Token exchange failed: {response.status} {error_text}")
        
        except aiohttp.ClientError as e:
            raise WhoopOAuthException(f"Request failed: {e}")
    
    async def refresh_access_token(self, user_id: str) -> Optional[str]:
        """Refresh expired access token"""
        # Get stored refresh token
        user_data = await self._get_user_tokens(user_id)
        if not user_data or not user_data.get("refresh_token"):
            return None
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": user_data["refresh_token"],
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        
                        expires_in = token_data.get("expires_in", 3600)
                        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        
                        # Update stored tokens
                        await self._update_user_tokens(
                            user_id,
                            token_data["access_token"],
                            token_data.get("refresh_token", user_data["refresh_token"]),
                            expires_at
                        )
                        
                        return token_data["access_token"]
                    else:
                        logger.error(f"Token refresh failed for user {user_id}: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Token refresh error for user {user_id}: {e}")
            return None
    
    async def _store_user_tokens(self, user_id: str, access_token: str, 
                               refresh_token: Optional[str], expires_at: datetime, 
                               scopes: str):
        """Store user tokens in database"""
        # First, get whoop user ID using the access token
        whoop_user_id = await self._get_whoop_user_id(access_token)
        
        data = {
            "user_id": user_id,
            "whoop_user_id": whoop_user_id,
            "access_token": access_token,  # TODO: Encrypt in production
            "refresh_token": refresh_token,  # TODO: Encrypt in production
            "token_expires_at": expires_at.isoformat(),
            "is_active": True
        }
        
        # Upsert user record
        result = db.client.table("whoop_users").upsert(data, on_conflict="user_id").execute()
        if result.data:
            logger.info(f"Stored tokens for user {user_id}")
        else:
            raise WhoopOAuthException("Failed to store user tokens")
    
    async def _get_whoop_user_id(self, access_token: str) -> Optional[str]:
        """Get Whoop user ID from profile API"""
        try:
            from app.services.whoop_service import WhoopAPIClient
            client = WhoopAPIClient(access_token)
            profile = await client.get_user_profile()
            await client.close()
            return str(profile.get("user_id"))
        except Exception as e:
            logger.warning(f"Could not fetch Whoop user ID: {e}")
            return None
    
    async def _get_user_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user tokens from database"""
        result = db.client.table("whoop_users").select("*").eq("user_id", user_id).eq("is_active", True).execute()
        return result.data[0] if result.data else None
    
    async def _update_user_tokens(self, user_id: str, access_token: str,
                                refresh_token: str, expires_at: datetime):
        """Update user tokens in database"""
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": expires_at.isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = db.client.table("whoop_users").update(data).eq("user_id", user_id).execute()
        if not result.data:
            raise WhoopOAuthException("Failed to update user tokens")
```

This detailed implementation provides a solid foundation for the MVP Whoop microservice. The key features include:

1. **Simple, focused architecture** following FastAPI best practices
2. **Clear separation of concerns** with dedicated services for OAuth, API calls, and data processing
3. **Graceful error handling** with custom exceptions
4. **Basic rate limiting** to respect Whoop API limits
5. **Minimal database schema** focusing only on essential data
6. **Production-ready configuration** with environment variables
7. **Health checks** for monitoring and debugging

The implementation prioritizes **simplicity and reliability** over advanced features, making it perfect for the MVP timeline while providing a solid foundation for future enhancements.