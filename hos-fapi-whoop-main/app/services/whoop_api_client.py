"""
Comprehensive WHOOP API Client Implementation
Handles rate limiting, error handling, and all WHOOP API endpoints
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
import httpx
import structlog
from cachetools import TTLCache

from app.config.settings import settings
from app.services.oauth_service import WhoopOAuthService
from app.models.schemas import (
    WhoopUserProfile, WhoopRecoveryData, WhoopSleepData, 
    WhoopWorkoutData
)

logger = structlog.get_logger(__name__)


class RateLimitManager:
    """Advanced rate limiting for WHOOP API (100/min, 10K/day)"""
    
    def __init__(self):
        # WHOOP API limits: 100/minute, 10,000/day
        self.minute_limit = settings.WHOOP_RATE_LIMIT_PER_MINUTE
        self.daily_limit = settings.WHOOP_RATE_LIMIT_PER_DAY
        
        # Rate limiting windows
        self.minute_requests = []  # Timestamps of requests in current minute
        self.daily_requests = []   # Timestamps of requests in current day
        
        # Request delay between calls
        self.request_delay = settings.WHOOP_RATE_LIMIT_DELAY  # 0.6 seconds
        
        logger.info("Rate limit manager initialized", 
                   minute_limit=self.minute_limit,
                   daily_limit=self.daily_limit,
                   request_delay=self.request_delay)
    
    async def acquire_permit(self) -> bool:
        """
        Acquire permission to make API request, respecting rate limits
        
        Returns:
            True if request can proceed, False if limits exceeded
        """
        now = datetime.utcnow()
        
        # Clean old requests (older than 1 minute and 1 day)
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        self.minute_requests = [req for req in self.minute_requests if req > minute_ago]
        self.daily_requests = [req for req in self.daily_requests if req > day_ago]
        
        # Check limits
        if len(self.minute_requests) >= self.minute_limit:
            logger.warning("⚠️ Minute rate limit exceeded", 
                         current_requests=len(self.minute_requests),
                         limit=self.minute_limit)
            return False
        
        if len(self.daily_requests) >= self.daily_limit:
            logger.error("❌ Daily rate limit exceeded", 
                        current_requests=len(self.daily_requests),
                        limit=self.daily_limit)
            return False
        
        # Add current request to tracking
        self.minute_requests.append(now)
        self.daily_requests.append(now)
        
        # Apply inter-request delay
        if len(self.minute_requests) > 1:
            await asyncio.sleep(self.request_delay)
        
        return True
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        # Clean and count current requests
        minute_count = sum(1 for req in self.minute_requests if req > minute_ago)
        daily_count = sum(1 for req in self.daily_requests if req > day_ago)
        
        return {
            "minute_limit": self.minute_limit,
            "minute_used": minute_count,
            "minute_remaining": max(0, self.minute_limit - minute_count),
            "daily_limit": self.daily_limit,
            "daily_used": daily_count,
            "daily_remaining": max(0, self.daily_limit - daily_count),
            "request_delay": self.request_delay
        }


class WhoopAPIClient:
    """Comprehensive WHOOP API client with full endpoint support"""
    
    def __init__(self):
        self.base_url = settings.WHOOP_API_BASE_URL
        self.oauth_service = WhoopOAuthService()
        self.rate_limiter = RateLimitManager()
        
        # Response cache (TTL-based for performance)
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
        
        # Retry configuration
        self.max_retries = settings.WHOOP_MAX_RETRIES
        self.retry_base_delay = settings.WHOOP_RETRY_BASE_DELAY
        self.request_timeout = settings.WHOOP_REQUEST_TIMEOUT
        
        logger.info("WHOOP API client initialized", 
                   base_url=self.base_url,
                   max_retries=self.max_retries,
                   timeout=self.request_timeout)
    
    async def _make_authenticated_request(
        self, 
        method: str, 
        endpoint: str, 
        user_id: str,
        params: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        bypass_cache: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to WHOOP API with comprehensive error handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            user_id: User identifier for authentication
            params: Query parameters
            cache_key: Cache key for response caching
            bypass_cache: Skip cache lookup
            
        Returns:
            API response data or None if failed
        """
        # Check cache first (if enabled and not bypassing)
        if cache_key and not bypass_cache:
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.info("Cache hit", cache_key=cache_key, user_id=user_id)
                return cached_response
        
        # Get valid access token
        access_token = await self.oauth_service.get_valid_access_token(user_id)
        if not access_token:
            logger.error("No valid access token available", user_id=user_id)
            return None
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                # Acquire rate limiting permit
                if not await self.rate_limiter.acquire_permit():
                    logger.error("Rate limit exceeded, request blocked", 
                               user_id=user_id, endpoint=endpoint)
                    return None
                
                async with httpx.AsyncClient() as client:
                    logger.info(f"Making {method} request", 
                               endpoint=endpoint, 
                               attempt=attempt + 1,
                               user_id=user_id)
                    
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        timeout=self.request_timeout
                    )
                    
                    # Handle different response codes
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Cache successful response
                        if cache_key:
                            self.cache[cache_key] = data
                            logger.info("Response cached", cache_key=cache_key)
                        
                        logger.info("API request successful", 
                                   endpoint=endpoint,
                                   user_id=user_id,
                                   response_size=len(str(data)))
                        return data
                    
                    elif response.status_code == 401:
                        # Unauthorized - token may be invalid
                        logger.warning("Unauthorized response, attempting token refresh", 
                                     user_id=user_id)
                        
                        # Try token refresh once
                        if await self.oauth_service.refresh_user_token(user_id):
                            # Get new token and retry (counts as attempt)
                            access_token = await self.oauth_service.get_valid_access_token(user_id)
                            if access_token:
                                headers['Authorization'] = f'Bearer {access_token}'
                                continue  # Retry with new token
                        
                        logger.error("Authentication failed after refresh attempt", 
                                   user_id=user_id)
                        return None
                    
                    elif response.status_code == 429:
                        # Rate limited by WHOOP
                        retry_after = response.headers.get('Retry-After', '60')
                        retry_delay = int(retry_after)
                        
                        logger.warning("Rate limited by WHOOP API", 
                                     retry_after=retry_delay,
                                     user_id=user_id)
                        
                        if attempt < self.max_retries:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error("Max retries exceeded for rate limiting", 
                                       user_id=user_id)
                            return None
                    
                    elif 400 <= response.status_code < 500:
                        # Client error - don't retry
                        logger.error("Client error from WHOOP API", 
                                   status_code=response.status_code,
                                   response=response.text,
                                   user_id=user_id)
                        return None
                    
                    elif response.status_code >= 500:
                        # Server error - retry with backoff
                        if attempt < self.max_retries:
                            delay = self.retry_base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning("Server error, retrying", 
                                         status_code=response.status_code,
                                         delay=delay,
                                         attempt=attempt + 1)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error("Server error, max retries exceeded", 
                                       status_code=response.status_code,
                                       user_id=user_id)
                            return None
                    
            except httpx.TimeoutException:
                logger.warning("Request timeout", 
                             endpoint=endpoint,
                             attempt=attempt + 1,
                             user_id=user_id)
                
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("Request timeout, max retries exceeded", user_id=user_id)
                    return None
                    
            except Exception as e:
                logger.error("Unexpected error in API request", 
                           endpoint=endpoint,
                           user_id=user_id,
                           error=str(e),
                           attempt=attempt + 1)
                
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        return None  # All attempts failed
    
    async def get_user_profile(self, user_id: str) -> Optional[WhoopUserProfile]:
        """Get user's WHOOP profile information"""
        try:
            cache_key = f"profile_{user_id}"
            data = await self._make_authenticated_request(
                method="GET",
                endpoint="user/profile",
                user_id=user_id,
                cache_key=cache_key
            )
            
            if data:
                return WhoopUserProfile(**data)
            return None
            
        except Exception as e:
            logger.error("❌ Failed to get user profile", user_id=user_id, error=str(e))
            return None
    
    async def get_cycles(self, user_id: str, limit: int = 25, 
                        start: Optional[datetime] = None, 
                        end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get user's cycles (recovery periods)
        
        Args:
            user_id: User identifier
            limit: Number of cycles to retrieve (max 50)
            start: Start datetime for filtering
            end: End datetime for filtering
            
        Returns:
            List of cycle data dictionaries
        """
        try:
            params = {"limit": min(limit, 50)}  # WHOOP API max limit
            
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()
            
            cache_key = f"cycles_{user_id}_{limit}_{start}_{end}"
            data = await self._make_authenticated_request(
                method="GET",
                endpoint="cycle",
                user_id=user_id,
                params=params,
                cache_key=cache_key
            )
            
            if data and 'data' in data:
                logger.info("✅ Retrieved cycles", 
                           user_id=user_id, 
                           count=len(data['data']))
                return data['data']
            
            return []
            
        except Exception as e:
            logger.error("❌ Failed to get cycles", user_id=user_id, error=str(e))
            return []
    
    async def get_recovery_data(self, user_id: str, cycle_id: str) -> Optional[WhoopRecoveryData]:
        """Get recovery data for specific cycle"""
        try:
            cache_key = f"recovery_{user_id}_{cycle_id}"
            data = await self._make_authenticated_request(
                method="GET",
                endpoint=f"cycle/{cycle_id}/recovery",
                user_id=user_id,
                cache_key=cache_key
            )
            
            if data:
                return WhoopRecoveryData(cycle_id=cycle_id, **data)
            return None
            
        except Exception as e:
            logger.error("❌ Failed to get recovery data", 
                        user_id=user_id, cycle_id=cycle_id, error=str(e))
            return None
    
    async def get_sleep_activities(self, user_id: str, limit: int = 25,
                                 start: Optional[datetime] = None,
                                 end: Optional[datetime] = None) -> List[WhoopSleepData]:
        """
        Get user's sleep activities
        
        Args:
            user_id: User identifier
            limit: Number of sleep records to retrieve
            start: Start datetime for filtering
            end: End datetime for filtering
            
        Returns:
            List of WhoopSleepData objects
        """
        try:
            params = {"limit": min(limit, 50)}
            
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()
            
            cache_key = f"sleep_{user_id}_{limit}_{start}_{end}"
            data = await self._make_authenticated_request(
                method="GET",
                endpoint="activity/sleep",
                user_id=user_id,
                params=params,
                cache_key=cache_key
            )
            
            if data and 'data' in data:
                sleep_records = []
                for sleep_item in data['data']:
                    try:
                        sleep_record = WhoopSleepData(**sleep_item)
                        sleep_records.append(sleep_record)
                    except Exception as parse_error:
                        logger.warning("⚠️ Failed to parse sleep record", 
                                     user_id=user_id, 
                                     error=str(parse_error))
                
                logger.info("✅ Retrieved sleep activities", 
                           user_id=user_id, 
                           count=len(sleep_records))
                return sleep_records
            
            return []
            
        except Exception as e:
            logger.error("❌ Failed to get sleep activities", user_id=user_id, error=str(e))
            return []
    
    async def get_workout_activities(self, user_id: str, limit: int = 25,
                                   start: Optional[datetime] = None,
                                   end: Optional[datetime] = None) -> List[WhoopWorkoutData]:
        """
        Get user's workout activities
        
        Args:
            user_id: User identifier
            limit: Number of workout records to retrieve
            start: Start datetime for filtering
            end: End datetime for filtering
            
        Returns:
            List of WhoopWorkoutData objects
        """
        try:
            params = {"limit": min(limit, 50)}
            
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()
            
            cache_key = f"workouts_{user_id}_{limit}_{start}_{end}"
            data = await self._make_authenticated_request(
                method="GET",
                endpoint="activity/workout",
                user_id=user_id,
                params=params,
                cache_key=cache_key
            )
            
            if data and 'data' in data:
                workout_records = []
                for workout_item in data['data']:
                    try:
                        workout_record = WhoopWorkoutData(**workout_item)
                        workout_records.append(workout_record)
                    except Exception as parse_error:
                        logger.warning("⚠️ Failed to parse workout record", 
                                     user_id=user_id, 
                                     error=str(parse_error))
                
                logger.info("✅ Retrieved workout activities", 
                           user_id=user_id, 
                           count=len(workout_records))
                return workout_records
            
            return []
            
        except Exception as e:
            logger.error("❌ Failed to get workout activities", user_id=user_id, error=str(e))
            return []
    
    async def get_comprehensive_user_data(self, user_id: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive health data for user (all data types)
        
        Args:
            user_id: User identifier
            days_back: Number of days of historical data to retrieve
            
        Returns:
            Dictionary containing all user health data
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            logger.info("📊 Fetching comprehensive user data", 
                       user_id=user_id, 
                       date_range=f"{start_date.date()} to {end_date.date()}")
            
            # Fetch all data types concurrently (respecting rate limits)
            profile = await self.get_user_profile(user_id)
            cycles = await self.get_cycles(user_id, limit=days_back * 2, start=start_date, end=end_date)
            sleep_data = await self.get_sleep_activities(user_id, limit=days_back * 2, start=start_date, end=end_date)
            workout_data = await self.get_workout_activities(user_id, limit=days_back * 4, start=start_date, end=end_date)
            
            # Get recovery data for each cycle
            recovery_data = []
            for cycle in cycles:
                if 'id' in cycle:
                    recovery = await self.get_recovery_data(user_id, cycle['id'])
                    if recovery:
                        recovery_data.append(recovery)
            
            result = {
                "user_id": user_id,
                "fetch_timestamp": datetime.utcnow().isoformat(),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days_back
                },
                "profile": profile.model_dump() if profile else None,
                "cycles": cycles,
                "recovery": [r.model_dump() for r in recovery_data],
                "sleep": [s.model_dump() for s in sleep_data],
                "workouts": [w.model_dump() for w in workout_data],
                "summary": {
                    "cycles_count": len(cycles),
                    "recovery_count": len(recovery_data),
                    "sleep_count": len(sleep_data),
                    "workout_count": len(workout_data)
                }
            }
            
            logger.info("✅ Comprehensive data fetch completed", 
                       user_id=user_id,
                       cycles=len(cycles),
                       recovery=len(recovery_data),
                       sleep=len(sleep_data),
                       workouts=len(workout_data))
            
            return result
            
        except Exception as e:
            logger.error("❌ Failed to get comprehensive user data", 
                        user_id=user_id, error=str(e))
            return {
                "user_id": user_id,
                "error": str(e),
                "fetch_timestamp": datetime.utcnow().isoformat()
            }
    
    def get_client_status(self) -> Dict[str, Any]:
        """Get comprehensive client status and statistics"""
        rate_limit_status = self.rate_limiter.get_rate_limit_status()
        
        return {
            "status": "operational",
            "base_url": self.base_url,
            "cache_size": len(self.cache),
            "cache_max_size": self.cache.maxsize,
            "rate_limiting": rate_limit_status,
            "configuration": {
                "max_retries": self.max_retries,
                "retry_base_delay": self.retry_base_delay,
                "request_timeout": self.request_timeout
            }
        }