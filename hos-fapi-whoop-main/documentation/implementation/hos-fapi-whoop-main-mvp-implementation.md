# hos-fapi-whoop-main MVP Implementation Plan
*Generated: 2025-08-27 - Sequential Calls MVP*

## Project Overview

This document provides a simplified, MVP-focused implementation guide for creating `hos-fapi-whoop-main` as a standalone microservice. The focus is on **speed to market** with **minimal complexity** - no over-engineering, just core functionality that works reliably.

## MVP Project Structure

### Simplified Directory Structure
```
hos-fapi-whoop-main/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Simple FastAPI app
│   ├── api/
│   │   ├── __init__.py
│   │   ├── internal.py           # All internal endpoints
│   │   ├── auth.py               # OAuth endpoints  
│   │   └── health.py             # Health checks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whoop_client.py       # Whoop API client
│   │   ├── auth_service.py       # OAuth management
│   │   └── data_service.py       # Data retrieval
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py           # Simple DB models
│   │   └── schemas.py            # Pydantic schemas
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # Configuration
│   └── utils/
│       ├── __init__.py
│       ├── rate_limit.py         # Basic rate limiting
│       └── crypto.py             # Token encryption
├── migrations/
│   └── init_whoop_db.sql         # Simple DB setup
├── tests/
│   └── test_basic.py             # Basic tests
├── requirements.txt               # Minimal dependencies
├── .env.example
├── Dockerfile                     # Simple container
└── README.md
```

## MVP Dependencies (requirements.txt)

Keep it minimal - only essential packages:

```txt
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
asyncpg==0.29.0
databases==0.8.0

# HTTP Client
httpx==0.25.2

# Security & Auth
python-jose[cryptography]==3.3.0
python-multipart==0.0.6

# Environment
python-dotenv==1.0.0
pydantic-settings==2.1.0

# Logging
structlog==23.2.0

# Development/Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

## Step 1: Basic FastAPI Application

### app/main.py (Simplified)
```python
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
```

### app/config/settings.py (Minimal)
```python
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
```

## Step 2: Simple Database Models

### app/models/database.py (MVP Schema)
```python
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.config.settings import settings

# Database connection
database = Database(settings.DATABASE_URL)
metadata = MetaData()
engine = create_engine(settings.DATABASE_URL)

# Simple tables - only essentials for MVP
whoop_users = Table(
    "whoop_users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("user_id", String, unique=True, nullable=False),
    Column("whoop_user_id", Integer, unique=True),
    Column("access_token_encrypted", Text),
    Column("refresh_token_encrypted", Text),
    Column("expires_at", DateTime),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

whoop_recovery_data = Table(
    "whoop_recovery_data",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("user_id", String, nullable=False),
    Column("recovery_score", Float),
    Column("hrv_rmssd", Float),
    Column("resting_heart_rate", Integer),
    Column("recorded_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
)

whoop_sleep_data = Table(
    "whoop_sleep_data",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("user_id", String, nullable=False),
    Column("sleep_id", String, unique=True),
    Column("duration_seconds", Integer),
    Column("efficiency_percentage", Float),
    Column("sleep_score", Float),
    Column("recorded_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
)

whoop_workout_data = Table(
    "whoop_workout_data",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("user_id", String, nullable=False),
    Column("workout_id", String, unique=True),
    Column("strain_score", Float),
    Column("average_heart_rate", Integer),
    Column("max_heart_rate", Integer),
    Column("recorded_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
)

async def connect_db():
    await database.connect()

async def disconnect_db():
    await database.disconnect()

def create_tables():
    metadata.create_all(engine)
```

### migrations/init_whoop_db.sql
```sql
-- Simple MVP database setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User connections
CREATE TABLE whoop_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) UNIQUE NOT NULL,
    whoop_user_id INTEGER UNIQUE,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Recovery data
CREATE TABLE whoop_recovery_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    recovery_score FLOAT,
    hrv_rmssd FLOAT,
    resting_heart_rate INTEGER,
    recorded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sleep data  
CREATE TABLE whoop_sleep_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    sleep_id VARCHAR(255) UNIQUE,
    duration_seconds INTEGER,
    efficiency_percentage FLOAT,
    sleep_score FLOAT,
    recorded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Workout data
CREATE TABLE whoop_workout_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    workout_id VARCHAR(255) UNIQUE,
    strain_score FLOAT,
    average_heart_rate INTEGER,
    max_heart_rate INTEGER,
    recorded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Simple indexes for performance
CREATE INDEX idx_whoop_recovery_user_id ON whoop_recovery_data(user_id);
CREATE INDEX idx_whoop_sleep_user_id ON whoop_sleep_data(user_id);
CREATE INDEX idx_whoop_workout_user_id ON whoop_workout_data(user_id);
```

## Step 3: Simple Whoop API Client

### app/services/whoop_client.py (MVP Version)
```python
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog

from app.config.settings import settings
from app.utils.rate_limit import RateLimiter
from app.utils.crypto import decrypt_token

logger = structlog.get_logger(__name__)

class WhoopClient:
    """Simplified Whoop API client for MVP"""
    
    def __init__(self, access_token_encrypted: str):
        self.access_token_encrypted = access_token_encrypted
        self.base_url = "https://api.prod.whoop.com/developer/v1"
        self.rate_limiter = RateLimiter(max_requests=80, time_window=60)
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Simple HTTP request with basic error handling"""
        await self.rate_limiter.acquire()
        
        access_token = decrypt_token(self.access_token_encrypted)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method, 
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    **kwargs
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Simple rate limit handling
                    await asyncio.sleep(60)
                    return await self._make_request(method, endpoint, **kwargs)
                else:
                    logger.error("Whoop API error", status=response.status_code)
                    return None
                    
        except Exception as e:
            logger.error("HTTP request failed", error=str(e))
            return None
    
    async def get_recovery_data(self, days: int = 7) -> Optional[Dict]:
        """Get recovery data for last N days"""
        try:
            # Get current cycle first
            cycle_data = await self._make_request('GET', '/cycle', params={'limit': 1})
            if not cycle_data or not cycle_data.get('data'):
                return None
                
            cycle_id = cycle_data['data'][0]['id']
            recovery = await self._make_request('GET', f'/cycle/{cycle_id}/recovery')
            
            return {
                'latest': recovery,
                'cycle': cycle_data['data'][0]
            }
            
        except Exception as e:
            logger.error("Error getting recovery data", error=str(e))
            return None
    
    async def get_sleep_data(self, days: int = 7) -> Optional[Dict]:
        """Get sleep data for last N days"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            params = {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'limit': 50
            }
            
            sleep_data = await self._make_request('GET', '/activity/sleep', params=params)
            return sleep_data
            
        except Exception as e:
            logger.error("Error getting sleep data", error=str(e))
            return None
    
    async def get_workout_data(self, days: int = 7) -> Optional[Dict]:
        """Get workout data for last N days"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            params = {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'limit': 50
            }
            
            workout_data = await self._make_request('GET', '/activity/workout', params=params)
            return workout_data
            
        except Exception as e:
            logger.error("Error getting workout data", error=str(e))
            return None
```

## Step 4: Simple Internal API Endpoints

### app/api/internal.py (MVP Endpoints)
```python
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import structlog

from app.services.data_service import DataService
from app.services.auth_service import AuthService
from app.models.schemas import RecoveryResponse, SleepResponse, WorkoutResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

# Simple API key authentication
async def verify_api_key(x_api_key: str = Header(...)):
    from app.config.settings import settings
    if x_api_key != settings.SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@router.get("/data/recovery/{user_id}")
async def get_recovery_data(
    user_id: str,
    days: int = 7,
    auth: str = Depends(verify_api_key)
):
    """Get recovery data for user"""
    try:
        data_service = DataService()
        result = await data_service.get_recovery_data(user_id, days)
        
        if result is None:
            raise HTTPException(status_code=404, detail="No recovery data found")
            
        return result
        
    except Exception as e:
        logger.error("Error getting recovery data", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data/sleep/{user_id}")
async def get_sleep_data(
    user_id: str,
    days: int = 7,
    auth: str = Depends(verify_api_key)
):
    """Get sleep data for user"""
    try:
        data_service = DataService()
        result = await data_service.get_sleep_data(user_id, days)
        
        if result is None:
            raise HTTPException(status_code=404, detail="No sleep data found")
            
        return result
        
    except Exception as e:
        logger.error("Error getting sleep data", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/data/workouts/{user_id}")
async def get_workout_data(
    user_id: str,
    days: int = 7,
    auth: str = Depends(verify_api_key)
):
    """Get workout data for user"""
    try:
        data_service = DataService()
        result = await data_service.get_workout_data(user_id, days)
        
        if result is None:
            raise HTTPException(status_code=404, detail="No workout data found")
            
        return result
        
    except Exception as e:
        logger.error("Error getting workout data", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/auth/status/{user_id}")
async def check_connection_status(
    user_id: str,
    auth: str = Depends(verify_api_key)
):
    """Check if user has active Whoop connection"""
    try:
        auth_service = AuthService()
        is_connected = await auth_service.is_user_connected(user_id)
        
        return {
            "user_id": user_id,
            "connected": is_connected,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error checking connection status", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/auth/connect/{user_id}")
async def initiate_connection(
    user_id: str,
    redirect_url: str,
    auth: str = Depends(verify_api_key)
):
    """Initiate OAuth connection for user"""
    try:
        auth_service = AuthService()
        auth_url, state = await auth_service.generate_auth_url(user_id, redirect_url)
        
        return {
            "user_id": user_id,
            "authorization_url": auth_url,
            "state": state,
            "expires_in": 300
        }
        
    except Exception as e:
        logger.error("Error initiating connection", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Step 5: Simple Environment Configuration

### .env.example
```bash
# Basic Configuration
PORT=8001
ENVIRONMENT=development

# Whoop API
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret
WHOOP_REDIRECT_URL=https://yourapp.com/auth/whoop/callback

# Database (Separate from Sahha)
DATABASE_URL=postgresql://user:pass@localhost:5432/whoop_mvp_db

# Service Security
SERVICE_API_KEY=your_internal_api_key_here

# Rate Limiting
RATE_LIMIT_PER_MINUTE=80
RATE_LIMIT_PER_DAY=8000
```

## MVP Implementation Timeline

### Week 1: Foundation (Days 1-7)
- [ ] Set up project structure
- [ ] Implement basic FastAPI app
- [ ] Set up database and migrations
- [ ] Create simple models and schemas

### Week 2: Core Integration (Days 8-14)
- [ ] Implement Whoop API client
- [ ] Add OAuth service (basic flow)
- [ ] Create internal API endpoints
- [ ] Add basic rate limiting

### Week 3: Data Services (Days 15-21)
- [ ] Implement data retrieval services
- [ ] Add simple data storage
- [ ] Create health check endpoints
- [ ] Add basic error handling

### Week 4: Testing & Deployment (Days 22-28)
- [ ] End-to-end testing
- [ ] Fix bugs and issues
- [ ] Deploy to staging
- [ ] Performance testing

## Simple Testing Strategy

### app/tests/test_basic.py
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health/ready")
    assert response.status_code == 200

def test_internal_auth_required():
    response = client.get("/internal/auth/status/test_user")
    assert response.status_code == 401  # No API key

def test_with_api_key():
    headers = {"X-API-Key": "test_key"}  # Use test key
    response = client.get("/internal/auth/status/test_user", headers=headers)
    # Should not be 401
    assert response.status_code in [200, 404, 500]  # Any except unauthorized
```

## Deployment (Simple Docker)

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY .env .env

EXPOSE 8001

CMD ["python", "-m", "app.main"]
```

### docker-compose.yml (Development)
```yaml
version: '3.8'
services:
  whoop-api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/whoop_mvp_db
    depends_on:
      - db
    
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=whoop_mvp_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Success Criteria for MVP

### Technical Success
- [ ] Service starts and responds to health checks
- [ ] Can authenticate with Whoop API
- [ ] Internal endpoints return data or proper errors
- [ ] Basic rate limiting prevents API abuse
- [ ] Database operations work correctly

### Integration Success  
- [ ] Entry point API can call this service
- [ ] OAuth flow works end-to-end
- [ ] Data retrieval completes within timeouts
- [ ] Errors don't crash the service
- [ ] Logging provides useful debugging info

### Business Success
- [ ] Users can connect their Whoop devices
- [ ] Health data appears in combined responses
- [ ] No impact on existing Sahha functionality
- [ ] Response times acceptable (<3s total)
- [ ] Ready for user testing

This MVP implementation focuses on **getting it working** rather than **getting it perfect**. The goal is a solid foundation that can be enhanced in future iterations while delivering value to users quickly.