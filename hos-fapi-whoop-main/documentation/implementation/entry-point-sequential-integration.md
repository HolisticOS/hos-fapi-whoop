# Entry Point Sequential Integration Plan
*Generated: 2025-08-27 - MVP Sequential Calls*

## Overview

This document outlines how to enhance the existing `hos-fapi-hm-sahha-main` entry point API to orchestrate **sequential calls** to the new `hos-fapi-whoop-main` microservice. The approach prioritizes simplicity and reliability for MVP delivery.

## Sequential Integration Pattern

### Simple Sequential Flow
```
Flutter Request
    ↓
hos-fapi-hm-sahha-main (Entry Point)
    ↓
Step 1: Get Sahha Data (existing - always works)
    ↓
Step 2: Check if user has Whoop connection
    ↓
Step 3: If connected, get Whoop data (with timeout)
    ↓
Step 4: Simple merge and return
    ↓
Combined Response to Flutter
```

### MVP Integration Benefits
- ✅ **Simple to implement** - sequential logic is straightforward
- ✅ **Reliable** - if Whoop fails, Sahha still works
- ✅ **Easy to debug** - clear failure points
- ✅ **Fast delivery** - less complexity = faster MVP
- ✅ **Backward compatible** - existing clients unaffected

## Implementation in hos-fapi-hm-sahha-main

### Step 1: Simple Whoop Service Client

Create `app/services/whoop_service_client.py`:

```python
import httpx
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

class WhoopServiceClient:
    """Simple client for calling hos-fapi-whoop-main microservice"""
    
    def __init__(self):
        # These would come from environment variables
        self.base_url = "http://localhost:8001"  # or whoop-service.internal
        self.api_key = "your-service-api-key"
        self.timeout = 10  # Conservative timeout for MVP
        
    async def _make_service_call(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make simple HTTP call to Whoop service"""
        headers = {"X-API-Key": self.api_key}
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.info("Whoop data not available", endpoint=endpoint)
                    return None
                else:
                    logger.warning("Whoop service error", status=response.status_code)
                    return None
                    
        except httpx.TimeoutException:
            logger.warning("Whoop service timeout", endpoint=endpoint)
            return None
        except Exception as e:
            logger.error("Whoop service error", error=str(e), endpoint=endpoint)
            return None
    
    async def is_user_connected(self, user_id: str) -> bool:
        """Check if user has active Whoop connection"""
        try:
            result = await self._make_service_call('GET', f'/internal/auth/status/{user_id}')
            return result and result.get('connected', False)
        except:
            return False
    
    async def get_recovery_data(self, user_id: str, days: int = 7) -> Optional[Dict]:
        """Get recovery data from Whoop service"""
        params = {'days': days}
        return await self._make_service_call(
            'GET', 
            f'/internal/data/recovery/{user_id}',
            params=params
        )
    
    async def get_sleep_data(self, user_id: str, days: int = 7) -> Optional[Dict]:
        """Get sleep data from Whoop service"""
        params = {'days': days}
        return await self._make_service_call(
            'GET',
            f'/internal/data/sleep/{user_id}',
            params=params
        )
    
    async def get_workout_data(self, user_id: str, days: int = 7) -> Optional[Dict]:
        """Get workout data from Whoop service"""
        params = {'days': days}
        return await self._make_service_call(
            'GET',
            f'/internal/data/workouts/{user_id}',
            params=params
        )
    
    async def initiate_whoop_connection(self, user_id: str, redirect_url: str) -> Optional[Dict]:
        """Start Whoop OAuth flow for user"""
        data = {"redirect_url": redirect_url}
        return await self._make_service_call(
            'POST',
            f'/internal/auth/connect/{user_id}',
            json=data
        )
    
    async def health_check(self) -> bool:
        """Simple health check for Whoop service"""
        try:
            result = await self._make_service_call('GET', '/health/ready')
            return result is not None
        except:
            return False
```

### Step 2: Enhanced Health Service with Sequential Processing

Create `app/services/unified_health_service.py`:

```python
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from app.services.sahha_service import SahhaService  # Your existing service
from app.services.whoop_service_client import WhoopServiceClient

logger = structlog.get_logger(__name__)

class UnifiedHealthService:
    """Simple service to combine Sahha and Whoop data sequentially"""
    
    def __init__(self):
        self.sahha_service = SahhaService()
        self.whoop_client = WhoopServiceClient()
        
    async def get_health_overview(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get health overview with sequential data retrieval
        
        MVP Approach:
        1. Always get Sahha data first (existing, reliable)
        2. Try to get Whoop data if user is connected
        3. Simple merge and return
        """
        result = {
            "user_id": user_id,
            "days": days,
            "retrieved_at": datetime.utcnow().isoformat(),
            "sources": {},
            "combined": {},
            "errors": []
        }
        
        # Step 1: Get Sahha data (existing functionality)
        logger.info("Getting Sahha data", user_id=user_id)
        try:
            sahha_data = await self.sahha_service.get_health_metrics(user_id, days)
            result["sources"]["sahha"] = sahha_data
            result["sources"]["sahha"]["available"] = True
            logger.info("Sahha data retrieved successfully", user_id=user_id)
        except Exception as e:
            logger.error("Sahha service error", user_id=user_id, error=str(e))
            result["sources"]["sahha"] = {"available": False, "error": str(e)}
            result["errors"].append(f"Sahha: {str(e)}")
        
        # Step 2: Check Whoop connection (sequential)
        logger.info("Checking Whoop connection", user_id=user_id)
        whoop_connected = await self.whoop_client.is_user_connected(user_id)
        
        if whoop_connected:
            # Step 3: Get Whoop data (sequential, with timeout)
            logger.info("Getting Whoop data", user_id=user_id)
            try:
                whoop_recovery = await self.whoop_client.get_recovery_data(user_id, days)
                whoop_sleep = await self.whoop_client.get_sleep_data(user_id, days)
                whoop_workouts = await self.whoop_client.get_workout_data(user_id, days)
                
                result["sources"]["whoop"] = {
                    "available": True,
                    "recovery": whoop_recovery,
                    "sleep": whoop_sleep,
                    "workouts": whoop_workouts
                }
                logger.info("Whoop data retrieved successfully", user_id=user_id)
                
            except Exception as e:
                logger.error("Whoop service error", user_id=user_id, error=str(e))
                result["sources"]["whoop"] = {"available": False, "error": str(e)}
                result["errors"].append(f"Whoop: {str(e)}")
        else:
            result["sources"]["whoop"] = {"available": False, "reason": "not_connected"}
            logger.info("User not connected to Whoop", user_id=user_id)
        
        # Step 4: Simple data combination
        result["combined"] = self._create_simple_combined_data(result["sources"])
        
        return result
    
    def _create_simple_combined_data(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Simple MVP data combination - just basic merging"""
        combined = {
            "overall_score": None,
            "recovery_readiness": None,
            "sleep_quality": None,
            "activity_level": None,
            "data_completeness": 0
        }
        
        # Track data completeness
        completeness_factors = 0
        total_factors = 4
        
        # Use Sahha data as base
        sahha_data = sources.get("sahha", {})
        if sahha_data.get("available"):
            if sahha_data.get("readiness"):
                combined["recovery_readiness"] = sahha_data["readiness"]
                completeness_factors += 1
            if sahha_data.get("sleep"):
                combined["sleep_quality"] = sahha_data["sleep"]  
                completeness_factors += 1
            if sahha_data.get("activity"):
                combined["activity_level"] = sahha_data["activity"]
                completeness_factors += 1
        
        # Enhance with Whoop data if available
        whoop_data = sources.get("whoop", {})
        if whoop_data.get("available"):
            # Use Whoop recovery if available (more detailed)
            if whoop_data.get("recovery") and whoop_data["recovery"]:
                whoop_recovery_score = whoop_data["recovery"].get("latest", {}).get("recovery_score")
                if whoop_recovery_score:
                    combined["recovery_readiness"] = whoop_recovery_score
                    completeness_factors += 1
            
            # Use Whoop sleep score if available
            if whoop_data.get("sleep") and whoop_data["sleep"]:
                # Simple average of recent sleep scores
                sleep_data = whoop_data["sleep"].get("data", [])
                if sleep_data:
                    sleep_scores = [s.get("sleep_score") for s in sleep_data if s.get("sleep_score")]
                    if sleep_scores:
                        combined["sleep_quality"] = sum(sleep_scores) / len(sleep_scores)
        
        # Calculate simple overall score
        scores = []
        if combined["recovery_readiness"]:
            scores.append(combined["recovery_readiness"])
        if combined["sleep_quality"]:
            scores.append(combined["sleep_quality"])
        if combined["activity_level"]:
            scores.append(combined["activity_level"])
        
        if scores:
            combined["overall_score"] = sum(scores) / len(scores)
        
        combined["data_completeness"] = (completeness_factors / total_factors) * 100
        
        return combined
    
    async def get_available_sources(self, user_id: str) -> Dict[str, bool]:
        """Get available data sources for user"""
        return {
            "sahha": True,  # Assume always available
            "whoop": await self.whoop_client.is_user_connected(user_id)
        }
    
    async def initiate_whoop_connection(self, user_id: str, redirect_url: str) -> Optional[Dict]:
        """Start Whoop connection process"""
        return await self.whoop_client.initiate_whoop_connection(user_id, redirect_url)
```

### Step 3: Enhanced API Endpoints

Create or update `app/api/health_unified.py`:

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import structlog

from app.services.unified_health_service import UnifiedHealthService
from app.models.schemas import UnifiedHealthResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/health/{user_id}")
async def get_unified_health_data(
    user_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days to retrieve")
):
    """
    Get unified health data from all available sources (sequential)
    
    This endpoint:
    1. Always gets Sahha data first (reliable)
    2. Checks if user has Whoop connection
    3. If connected, gets Whoop data (with timeout)
    4. Returns combined data
    
    Works even if Whoop service is down or user isn't connected.
    """
    try:
        service = UnifiedHealthService()
        data = await service.get_health_overview(user_id, days)
        
        return {
            "success": True,
            "data": data,
            "message": "Health data retrieved successfully"
        }
        
    except Exception as e:
        logger.error("Error getting unified health data", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error retrieving health data")

@router.get("/health/{user_id}/sources")
async def get_data_sources(user_id: str):
    """Get available data sources for user"""
    try:
        service = UnifiedHealthService()
        sources = await service.get_available_sources(user_id)
        
        return {
            "user_id": user_id,
            "available_sources": sources,
            "recommendations": _get_recommendations(sources)
        }
        
    except Exception as e:
        logger.error("Error getting data sources", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error checking data sources")

@router.post("/whoop/connect/{user_id}")
async def connect_whoop_device(
    user_id: str,
    redirect_url: str = Query(..., description="OAuth callback URL")
):
    """Initiate Whoop device connection for user"""
    try:
        service = UnifiedHealthService()
        auth_data = await service.initiate_whoop_connection(user_id, redirect_url)
        
        if not auth_data:
            raise HTTPException(status_code=400, detail="Unable to initiate Whoop connection")
        
        return {
            "success": True,
            "user_id": user_id,
            "authorization_url": auth_data.get("authorization_url"),
            "expires_in": auth_data.get("expires_in", 300)
        }
        
    except Exception as e:
        logger.error("Error connecting Whoop device", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Error initiating Whoop connection")

def _get_recommendations(sources: Dict[str, bool]) -> List[str]:
    """Simple recommendations based on available sources"""
    recommendations = []
    
    if not sources.get("whoop", False):
        recommendations.append("Connect your WHOOP device for enhanced recovery insights")
    
    if sources.get("sahha") and sources.get("whoop"):
        recommendations.append("Great! You have comprehensive health data from multiple sources")
    elif sources.get("sahha"):
        recommendations.append("Your basic health data is available. Consider adding WHOOP for detailed physiological monitoring")
    
    return recommendations
```

### Step 4: Update Main Application

Add the new router to `app/main.py`:

```python
from app.api import health_unified

# Include the new unified health router
app.include_router(
    health_unified.router, 
    prefix="/api/v1", 
    tags=["Unified Health"]
)
```

### Step 5: Environment Configuration

Add to `.env` in `hos-fapi-hm-sahha-main`:

```bash
# Whoop Microservice Integration
WHOOP_SERVICE_URL=http://localhost:8001
WHOOP_SERVICE_API_KEY=your_service_to_service_api_key
WHOOP_SERVICE_TIMEOUT=10

# Feature Flags for MVP
ENABLE_WHOOP_INTEGRATION=true
WHOOP_CONNECTION_TIMEOUT=10
```

## Sequential Flow Examples

### Successful Flow (Both Sources Available)
```
1. Flutter: GET /api/v1/health/user123
2. Entry Point: Get Sahha data (800ms)
3. Entry Point: Check Whoop connection (100ms) → True
4. Entry Point: Get Whoop recovery (600ms)
5. Entry Point: Get Whoop sleep (400ms) 
6. Entry Point: Get Whoop workouts (300ms)
7. Entry Point: Merge data (50ms)
8. Flutter: Receives combined data (Total: ~2.25s)
```

### Graceful Degradation (Whoop Service Down)
```
1. Flutter: GET /api/v1/health/user123
2. Entry Point: Get Sahha data (800ms)
3. Entry Point: Check Whoop connection (timeout after 10s)
4. Entry Point: Log warning, continue with Sahha only
5. Entry Point: Return Sahha data with note about Whoop unavailable
6. Flutter: Receives Sahha data normally (Total: ~11s, but app works)
```

### User Without Whoop Connection
```
1. Flutter: GET /api/v1/health/user123
2. Entry Point: Get Sahha data (800ms)
3. Entry Point: Check Whoop connection (100ms) → False
4. Entry Point: Skip Whoop calls, return Sahha data
5. Flutter: Receives Sahha data (Total: ~900ms)
```

## Testing the Sequential Integration

### Simple Integration Test
```python
import pytest
from app.services.unified_health_service import UnifiedHealthService

@pytest.mark.asyncio
async def test_sequential_health_data_retrieval():
    service = UnifiedHealthService()
    
    # Test with mock user
    result = await service.get_health_overview("test_user", days=7)
    
    # Should always have Sahha data (or error)
    assert "sahha" in result["sources"]
    
    # Should indicate Whoop status
    assert "whoop" in result["sources"]
    
    # Should have combined data
    assert "combined" in result
    
    # Should complete within reasonable time
    # (This would be measured in actual test)

@pytest.mark.asyncio 
async def test_whoop_service_failure_graceful():
    # Mock Whoop service failure
    service = UnifiedHealthService()
    # ... test that Sahha data still works when Whoop fails
```

## MVP Benefits Summary

### ✅ **Simplicity**
- Sequential logic is easy to understand and debug
- Clear error boundaries between services
- Straightforward testing approach

### ✅ **Reliability** 
- Existing Sahha users completely unaffected
- Graceful degradation when Whoop service unavailable
- Conservative timeouts prevent hanging requests

### ✅ **Speed to Market**
- Much faster to implement than parallel processing
- Less complexity = fewer bugs
- Can deliver MVP in 4 weeks instead of 8

### ✅ **Future Ready**
- Foundation is solid for parallel enhancement later
- Data structures support both sequential and parallel
- Can optimize performance in v2.0

## Next Steps After MVP

### Version 2.0 Enhancements
1. **Parallel Processing**: Make Sahha and Whoop calls simultaneously
2. **Advanced Caching**: Redis-based caching for faster responses  
3. **Real-time Updates**: Webhook integration for live data
4. **Smart Insights**: Cross-source data correlation and analytics

This sequential approach gets you to market fast with a reliable foundation that can be enhanced incrementally!