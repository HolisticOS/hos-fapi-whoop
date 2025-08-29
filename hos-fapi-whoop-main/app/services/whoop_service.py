"""
WHOOP API Service Implementation
Handles UUID identifiers for Sleep and Workout resources
Extends the existing API client with v2-specific functionality
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date, timedelta
import httpx
import structlog
from cachetools import TTLCache

from app.config.settings import settings
from app.models.schemas import (
    WhoopSleepData, WhoopWorkoutData, WhoopRecoveryData, WhoopCycleData, 
    WhoopProfileData, WhoopBodyMeasurementData,
    WhoopSleepCollection, WhoopWorkoutCollection, WhoopRecoveryCollection, WhoopCycleCollection,
    WhoopDataResponse
)
from app.utils.uuid_utils import (
    is_valid_uuid, normalize_whoop_id, validate_whoop_resource_id,
    is_uuid_required_for_resource
)
from app.services.raw_data_storage import WhoopRawDataStorage

logger = structlog.get_logger(__name__)


class SimpleRateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_request = None
    
    async def acquire_permit(self) -> bool:
        """Check if we can make a request (simple time-based rate limiting)"""
        current_time = time.time()
        
        if self.last_request is None:
            self.last_request = current_time
            return True
        
        time_since_last = current_time - self.last_request
        if time_since_last >= self.min_interval:
            self.last_request = current_time
            return True
        
        # Wait if needed
        wait_time = self.min_interval - time_since_last
        await asyncio.sleep(wait_time)
        self.last_request = time.time()
        return True
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        current_time = time.time()
        time_since_last = current_time - self.last_request if self.last_request else None
        
        return {
            'requests_remaining': 1 if (time_since_last is None or time_since_last >= self.min_interval) else 0,
            'reset_time': None,
            'time_since_last_request': time_since_last
        }


class WhoopAPIService:
    """
    WHOOP API Service with UUID support
    Handles the transition from v1 integer IDs to v2 UUID identifiers
    """
    
    def __init__(self):
        self.base_url = settings.WHOOP_API_BASE_URL  # Should be v2 URL
        # OAuth and rate limiting would be handled here
        # Simplified for v2-only operation
        
        # Response cache (TTL-based for performance)  
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
        
        # Rate limiting - simple implementation
        self.rate_limiter = SimpleRateLimiter(min_interval=1.0)
        
        # Retry configuration
        self.max_retries = settings.WHOOP_MAX_RETRIES
        self.retry_base_delay = settings.WHOOP_RETRY_BASE_DELAY
        self.request_timeout = settings.WHOOP_REQUEST_TIMEOUT
        
        # v2 configuration
        self.api_version = "v2"
        self.supports_uuids = settings.WHOOP_SUPPORTS_UUIDS
        self.backward_compatibility = settings.WHOOP_BACKWARD_COMPATIBILITY
        
        # Initialize raw data storage
        self.raw_storage = WhoopRawDataStorage()
        
        logger.info("WHOOP API service initialized",
                   base_url=self.base_url,
                   api_version=self.api_version,
                   supports_uuids=self.supports_uuids,
                   backward_compatibility=self.backward_compatibility)
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        user_id: str,
        params: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        bypass_cache: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to WHOOP API with UUID handling
        
        Args:
            method: HTTP method
            endpoint: API endpoint path
            user_id: User identifier for authentication
            params: Query parameters
            cache_key: Cache key for response caching
            bypass_cache: Skip cache lookup
            
        Returns:
            API response data or None if failed
        """
        # Check cache first
        if cache_key and not bypass_cache:
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.info("cache hit", cache_key=cache_key, user_id=user_id)
                return cached_response
        
        # Get valid access token from database
        from app.services.auth_service import WhoopAuthService
        auth_service = WhoopAuthService()
        access_token = await auth_service.get_valid_token(user_id)
        
        if not access_token:
            logger.error("No valid access token for user", user_id=user_id)
            return None
        
        # Ensure endpoint has proper v2 base URL
        if not self.base_url.endswith('/'):
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = f"{self.base_url}{endpoint.lstrip('/')}"
            
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'User-Agent': f'WHOOP-v2-Client/{self.api_version}'
        }
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                # Acquire rate limiting permit
                if not await self.rate_limiter.acquire_permit():
                    logger.error("Rate limit exceeded for API", 
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
                            logger.info("response cached", cache_key=cache_key)
                        
                        logger.info("API request successful",
                                   endpoint=endpoint,
                                   user_id=user_id,
                                   response_size=len(str(data)))
                        return data
                    
                    elif response.status_code == 401:
                        # Unauthorized - attempt token refresh
                        logger.warning("API unauthorized, attempting token refresh", 
                                     user_id=user_id)
                        
                        # Token refresh is now handled automatically by auth_service
                        # Try to get a fresh token
                        fresh_token = await auth_service.get_valid_token(user_id)
                        if fresh_token and fresh_token != access_token:
                            headers['Authorization'] = f'Bearer {fresh_token}'
                            continue
                        
                        logger.error("API authentication failed after refresh", 
                                   user_id=user_id)
                        return None
                    
                    elif response.status_code == 404:
                        # Resource not found - could be v1/v2 ID mismatch
                        logger.warning("API resource not found", 
                                     endpoint=endpoint,
                                     user_id=user_id,
                                     status_code=response.status_code)
                        return None
                        
                    elif response.status_code == 429:
                        # Rate limited
                        retry_after = response.headers.get('Retry-After', '60')
                        retry_delay = int(retry_after)
                        
                        logger.warning("API rate limited", 
                                     retry_after=retry_delay,
                                     user_id=user_id)
                        
                        if attempt < self.max_retries:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            return None
                    
                    elif 400 <= response.status_code < 500:
                        # Client error
                        logger.error("API client error", 
                                   status_code=response.status_code,
                                   response=response.text,
                                   user_id=user_id)
                        return None
                    
                    elif response.status_code >= 500:
                        # Server error - retry with backoff
                        if attempt < self.max_retries:
                            delay = self.retry_base_delay * (2 ** attempt)
                            logger.warning("API server error, retrying", 
                                         status_code=response.status_code,
                                         delay=delay,
                                         attempt=attempt + 1)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            return None
                    
            except httpx.TimeoutException:
                logger.warning("API request timeout", 
                             endpoint=endpoint,
                             attempt=attempt + 1,
                             user_id=user_id)
                
                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
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
        
        return None
    
    async def get_sleep_data(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        next_token: Optional[str] = None,
        limit: int = 25
    ) -> WhoopSleepCollection:
        """
        Fetch sleep data from API with UUID identifiers
        
        Args:
            user_id: User identifier
            start_date: Start date in ISO format (currently ignored due to v2 API issue)
            end_date: End date in ISO format (currently ignored due to v2 API issue)
            next_token: Pagination token
            limit: Number of records to retrieve
            
        Returns:
            WhoopSleepCollection with sleep records
        """
        try:
            # TEMP FIX: Date parameters cause 404s in WHOOP v2 API
            # Using only limit parameter until date format issue is resolved
            params = {
                "limit": min(limit, 50)
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            cache_key = f"sleep_{user_id}_{start_date}_{end_date}_{limit}" if not next_token else None
            
            response_data = await self._make_request(
                method="GET",
                endpoint="activity/sleep",
                user_id=user_id,
                params=params,
                cache_key=cache_key
            )
            
            if not response_data:
                return WhoopSleepCollection()
            
            sleep_records = []
            for record in response_data.get("records", []):
                try:
                    # Validate UUID identifier
                    record_id = record.get("id")
                    if not is_valid_uuid(record_id):
                        logger.warning("Invalid sleep UUID in v2 response", 
                                     record_id=record_id, user_id=user_id)
                        continue
                    
                    # Create v2 sleep data model using actual API field names
                    sleep_data = WhoopSleepData(
                        id=record_id,
                        activity_v1_id=record.get("v1_id"),  # API returns "v1_id" not "activityV1Id"
                        user_id=record["user_id"],  # API returns "user_id" as int
                        start=record["start"],
                        end=record["end"],
                        timezone_offset=record.get("timezoneOffset"),
                        total_sleep_time_milli=record.get("totalSleepTimeMilli"),
                        time_in_bed_milli=record.get("timeInBedMilli"),
                        cycle_id=record.get("cycleId"),
                        raw_data=record
                    )
                    
                    sleep_records.append(sleep_data)
                    
                except Exception as parse_error:
                    logger.warning("Failed to parse v2 sleep record", 
                                 user_id=user_id,
                                 record_id=record.get("id"),
                                 error=str(parse_error))
            
            collection = WhoopSleepCollection(
                records=sleep_records,
                next_token=response_data.get("next_token"),
                total_count=len(sleep_records)
            )
            
            logger.info("✅ Retrieved v2 sleep data", 
                       user_id=user_id,
                       count=len(sleep_records),
                       has_next_token=bool(collection.next_token))
            
            # Store raw data in database
            raw_records = response_data.get("records", [])
            if raw_records:
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="sleep",
                    records=raw_records,
                    next_token=response_data.get("next_token"),
                    api_endpoint="activity/sleep"
                )
            
            return collection
            
        except Exception as e:
            logger.error("❌ Failed to get sleep data", 
                        user_id=user_id, error=str(e))
            return WhoopSleepCollection()
    
    async def get_workout_data(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        next_token: Optional[str] = None,
        limit: int = 25
    ) -> WhoopWorkoutCollection:
        """
        Fetch workout data from API with UUID identifiers
        
        Args:
            user_id: User identifier
            start_date: Start date in ISO format
            end_date: End date in ISO format
            next_token: Pagination token
            limit: Number of records to retrieve
            
        Returns:
            WhoopWorkoutCollection with workout records
        """
        try:
            # TEMP FIX: Date parameters cause 404s in WHOOP v2 API
            # Using only limit parameter until date format issue is resolved
            params = {
                "limit": min(limit, 50)
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            cache_key = f"workout_{user_id}_{start_date}_{end_date}_{limit}" if not next_token else None
            
            response_data = await self._make_request(
                method="GET",
                endpoint="activity/workout",
                user_id=user_id,
                params=params,
                cache_key=cache_key
            )
            
            if not response_data:
                return WhoopWorkoutCollection()
            
            workout_records = []
            for record in response_data.get("records", []):
                try:
                    # Validate UUID identifier
                    record_id = record.get("id")
                    if not is_valid_uuid(record_id):
                        logger.warning("Invalid workout UUID in v2 response", 
                                     record_id=record_id, user_id=user_id)
                        continue
                    
                    # Create v2 workout data model
                    workout_data = WhoopWorkoutData(
                        id=record_id,
                        activity_v1_id=record.get("v1_id"),  # API returns "v1_id" 
                        user_id=record["user_id"],  # API returns "user_id" as int
                        sport_id=record["sport_id"],  # API returns "sport_id" not "sportId"
                        sport_name=record.get("sport_name"),  # API returns "sport_name"
                        start=record["start"],
                        end=record["end"],
                        timezone_offset=record.get("timezoneOffset"),
                        strain_score=record.get("strain"),
                        average_heart_rate=record.get("averageHeartRate"),
                        max_heart_rate=record.get("maxHeartRate"),
                        calories_burned=record.get("calories"),
                        distance_meters=record.get("distanceMeters"),
                        raw_data=record
                    )
                    
                    workout_records.append(workout_data)
                    
                except Exception as parse_error:
                    logger.warning("Failed to parse v2 workout record", 
                                 user_id=user_id,
                                 record_id=record.get("id"),
                                 error=str(parse_error))
            
            collection = WhoopWorkoutCollection(
                records=workout_records,
                next_token=response_data.get("next_token"),
                total_count=len(workout_records)
            )
            
            logger.info("✅ Retrieved v2 workout data", 
                       user_id=user_id,
                       count=len(workout_records),
                       has_next_token=bool(collection.next_token))
            
            # Store raw data in database
            raw_records = response_data.get("records", [])
            if raw_records:
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="workout",
                    records=raw_records,
                    next_token=response_data.get("next_token"),
                    api_endpoint="activity/workout"
                )
            
            return collection
            
        except Exception as e:
            logger.error("❌ Failed to get workout data", 
                        user_id=user_id, error=str(e))
            return WhoopWorkoutCollection()
    
    async def get_recovery_data(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        next_token: Optional[str] = None,
        limit: int = 25
    ) -> WhoopRecoveryCollection:
        """
        Fetch recovery data from API (structure unchanged from v1)
        
        Args:
            user_id: User identifier
            start_date: Start date in ISO format
            end_date: End date in ISO format
            next_token: Pagination token
            limit: Number of records to retrieve
            
        Returns:
            WhoopRecoveryCollection with recovery records
        """
        try:
            # TEMP FIX: Date parameters cause 404s in WHOOP v2 API
            # Using only limit parameter until date format issue is resolved
            params = {
                "limit": min(limit, 50)
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            cache_key = f"recovery_{user_id}_{start_date}_{end_date}_{limit}" if not next_token else None
            
            response_data = await self._make_request(
                method="GET",
                endpoint="recovery",
                user_id=user_id,
                params=params,
                cache_key=cache_key
            )
            
            if not response_data:
                return WhoopRecoveryCollection()
            
            recovery_records = []
            for record in response_data.get("records", []):
                try:
                    recovery_data = WhoopRecoveryData(
                        cycle_id=record["cycle_id"],  # API returns "cycle_id" as int
                        user_id=record["user_id"],  # API returns "user_id" as int
                        recovery_score=record.get("score", {}).get("recovery_score"),
                        hrv_rmssd=record.get("score", {}).get("hrv_rmssd_milli"),
                        resting_heart_rate=record.get("score", {}).get("resting_heart_rate"),
                        respiratory_rate=None,  # Not in response, make optional
                        recorded_at=record.get("created_at"),
                        raw_data=record
                    )
                    
                    recovery_records.append(recovery_data)
                    
                except Exception as parse_error:
                    logger.warning("Failed to parse v2 recovery record", 
                                 user_id=user_id,
                                 cycle_id=record.get("cycle", {}).get("id"),
                                 error=str(parse_error))
            
            collection = WhoopRecoveryCollection(
                records=recovery_records,
                next_token=response_data.get("next_token"),
                total_count=len(recovery_records)
            )
            
            logger.info("✅ Retrieved v2 recovery data", 
                       user_id=user_id,
                       count=len(recovery_records),
                       has_next_token=bool(collection.next_token))
            
            # Store raw data in database
            raw_records = response_data.get("records", [])
            if raw_records:
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="recovery",
                    records=raw_records,
                    next_token=response_data.get("next_token"),
                    api_endpoint="recovery"
                )
            
            return collection
            
        except Exception as e:
            logger.error("❌ Failed to get recovery data", 
                        user_id=user_id, error=str(e))
            return WhoopRecoveryCollection()
    
    async def get_sleep_by_uuid(self, user_id: str, sleep_uuid: str) -> Optional[WhoopSleepData]:
        """
        Get specific sleep record by UUID identifier
        
        Args:
            user_id: User identifier
            sleep_uuid: Sleep UUID from API
            
        Returns:
            WhoopSleepData or None if not found
        """
        try:
            # Validate UUID format
            if not is_valid_uuid(sleep_uuid):
                logger.error("Invalid sleep UUID format", 
                           sleep_uuid=sleep_uuid, user_id=user_id)
                return None
            
            cache_key = f"sleep_uuid_{user_id}_{sleep_uuid}"
            
            response_data = await self._make_request(
                method="GET",
                endpoint=f"activity/sleep/{sleep_uuid}",
                user_id=user_id,
                cache_key=cache_key
            )
            
            if not response_data:
                return None
            
            sleep_data = WhoopSleepData(
                id=response_data["id"],
                activity_v1_id=response_data.get("activityV1Id"),
                user_id=response_data["userId"],
                start=response_data["start"],
                end=response_data["end"],
                timezone_offset=response_data.get("timezoneOffset"),
                raw_data=response_data
            )
            
            logger.info("✅ Retrieved sleep record by UUID", 
                       user_id=user_id, sleep_uuid=sleep_uuid)
            
            return sleep_data
            
        except Exception as e:
            logger.error("❌ Failed to get sleep by UUID", 
                        user_id=user_id, sleep_uuid=sleep_uuid, error=str(e))
            return None
    
    async def get_workout_by_uuid(self, user_id: str, workout_uuid: str) -> Optional[WhoopWorkoutData]:
        """
        Get specific workout record by UUID identifier
        
        Args:
            user_id: User identifier
            workout_uuid: Workout UUID from API
            
        Returns:
            WhoopWorkoutData or None if not found
        """
        try:
            # Validate UUID format
            if not is_valid_uuid(workout_uuid):
                logger.error("Invalid workout UUID format", 
                           workout_uuid=workout_uuid, user_id=user_id)
                return None
            
            cache_key = f"workout_uuid_{user_id}_{workout_uuid}"
            
            response_data = await self._make_request(
                method="GET",
                endpoint=f"activity/workout/{workout_uuid}",
                user_id=user_id,
                cache_key=cache_key
            )
            
            if not response_data:
                return None
            
            workout_data = WhoopWorkoutData(
                id=response_data["id"],
                activity_v1_id=response_data.get("activityV1Id"),
                user_id=response_data["userId"],
                sport_id=response_data["sportId"],
                start=response_data["start"],
                end=response_data["end"],
                raw_data=response_data
            )
            
            logger.info("✅ Retrieved workout record by UUID", 
                       user_id=user_id, workout_uuid=workout_uuid)
            
            return workout_data
            
        except Exception as e:
            logger.error("❌ Failed to get workout by UUID", 
                        user_id=user_id, workout_uuid=workout_uuid, error=str(e))
            return None
    
    async def get_comprehensive_data(
        self,
        user_id: str,
        days_back: int = 7,
        include_all_pages: bool = False
    ) -> WhoopDataResponse:
        """
        Get comprehensive health data using API with UUID support
        
        Args:
            user_id: User identifier
            days_back: Number of days of historical data
            include_all_pages: Whether to fetch all paginated results
            
        Returns:
            WhoopDataResponse with all health data
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            logger.info("📊 Fetching comprehensive data", 
                       user_id=user_id,
                       date_range=f"{start_date.date()} to {end_date.date()}")
            
            # Fetch all data types concurrently
            sleep_collection = await self.get_sleep_data(user_id, start_iso, end_iso, limit=50)
            workout_collection = await self.get_workout_data(user_id, start_iso, end_iso, limit=50)
            recovery_collection = await self.get_recovery_data(user_id, start_iso, end_iso, limit=50)
            
            # Handle pagination if requested
            if include_all_pages:
                # Fetch additional pages for sleep data
                while sleep_collection.next_token:
                    next_sleep = await self.get_sleep_data(
                        user_id, start_iso, end_iso, 
                        next_token=sleep_collection.next_token
                    )
                    sleep_collection.records.extend(next_sleep.records)
                    sleep_collection.next_token = next_sleep.next_token
                
                # Fetch additional pages for workout data
                while workout_collection.next_token:
                    next_workout = await self.get_workout_data(
                        user_id, start_iso, end_iso,
                        next_token=workout_collection.next_token
                    )
                    workout_collection.records.extend(next_workout.records)
                    workout_collection.next_token = next_workout.next_token
                
                # Fetch additional pages for recovery data
                while recovery_collection.next_token:
                    next_recovery = await self.get_recovery_data(
                        user_id, start_iso, end_iso,
                        next_token=recovery_collection.next_token
                    )
                    recovery_collection.records.extend(next_recovery.records)
                    recovery_collection.next_token = next_recovery.next_token
            
            response = WhoopDataResponse(
                sleep_data=sleep_collection.records,
                workout_data=workout_collection.records,
                recovery_data=recovery_collection.records,
                total_records=(
                    len(sleep_collection.records) + 
                    len(workout_collection.records) + 
                    len(recovery_collection.records)
                ),
                api_version="v2"
            )
            
            logger.info("✅ Comprehensive v2 data fetch completed", 
                       user_id=user_id,
                       sleep_count=len(response.sleep_data),
                       workout_count=len(response.workout_data),
                       recovery_count=len(response.recovery_data),
                       total_records=response.total_records)
            
            return response
            
        except Exception as e:
            logger.error("❌ Failed to get comprehensive data", 
                        user_id=user_id, error=str(e))
            return WhoopDataResponse()
    
    async def get_cycle_data(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        next_token: Optional[str] = None,
        limit: int = 25
    ) -> Optional[WhoopCycleCollection]:
        """
        Get WHOOP cycle data for user
        
        Args:
            user_id: User identifier
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            next_token: Pagination token
            limit: Number of records to fetch (max 50)
            
        Returns:
            WhoopCycleCollection or None if error
        """
        try:
            # TEMP FIX: Date parameters cause 404s in WHOOP v2 API
            # Using only limit parameter until date format issue is resolved
            params = {
                "limit": min(limit, 50)
            }
            
            if next_token:
                params["nextToken"] = next_token
            
            response_data = await self._make_request(
                method="GET",
                endpoint="cycle",
                user_id=user_id,
                params=params
            )
            
            if not response_data:
                return WhoopCycleCollection()
            
            cycles = []
            for item in response_data.get("records", []):
                # Create cycle data with actual API field names
                cycle = WhoopCycleData(
                    id=str(item["id"]),  # API returns id as int, convert to string
                    user_id=item["user_id"],  # API returns "user_id" as int  
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                    start=item["start"],
                    end=item.get("end"),
                    timezone_offset=item.get("timezone_offset"),
                    score_state=item.get("score_state"),
                    score=item.get("score"),
                    raw_data=item
                )
                cycles.append(cycle)
            
            collection = WhoopCycleCollection(
                data=cycles,
                next_token=response_data.get("next_token")
            )
            
            logger.info("✅ Retrieved cycle data", 
                       user_id=user_id, count=len(cycles))
            
            # Store raw data in database
            raw_records = response_data.get("records", [])
            if raw_records:
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="cycle",
                    records=raw_records,
                    next_token=response_data.get("next_token"),
                    api_endpoint="cycle"
                )
            
            return collection
            
        except Exception as e:
            logger.error("❌ Failed to get cycle data", 
                        user_id=user_id, error=str(e))
            return WhoopCycleCollection()
    
    async def get_profile_data(self, user_id: str) -> Optional[WhoopProfileData]:
        """
        Get WHOOP profile data for user
        
        Args:
            user_id: User identifier
            
        Returns:
            WhoopProfileData or None if error
        """
        try:
            
            response_data = await self._make_request(
                method="GET",
                endpoint="user/profile/basic",
                user_id=user_id
            )
            
            if not response_data:
                return None
            
            profile = WhoopProfileData(
                user_id=response_data["user_id"],
                email=response_data["email"],
                first_name=response_data["first_name"],
                last_name=response_data["last_name"],
                raw_data=response_data
            )
            
            logger.info("✅ Retrieved profile data", user_id=user_id)
            
            return profile
            
        except Exception as e:
            logger.error("❌ Failed to get profile data", 
                        user_id=user_id, error=str(e))
            return None
    
    async def get_body_measurement_data(self, user_id: str) -> Optional[WhoopBodyMeasurementData]:
        """
        Get WHOOP body measurement data for user (from profile endpoint)
        Note: Body measurements are included in the profile data
        
        Args:
            user_id: User identifier
            
        Returns:
            WhoopBodyMeasurementData or None if error
        """
        try:
            # Body measurements are part of the profile endpoint in v2
            profile_data = await self.get_profile_data(user_id)
            
            if not profile_data or not profile_data.raw_data:
                return None
            
            # Extract body measurements from profile data
            raw_data = profile_data.raw_data
            
            body_measurement = WhoopBodyMeasurementData(
                user_id=raw_data.get("user_id", 0),
                height_meter=raw_data.get("height_meter"),
                weight_kilogram=raw_data.get("weight_kilogram"), 
                max_heart_rate=raw_data.get("max_heart_rate"),
                raw_data=raw_data
            )
            
            logger.info("✅ Retrieved body measurement data from profile", user_id=user_id)
            
            return body_measurement
            
        except Exception as e:
            logger.error("❌ Failed to get body measurement data", 
                        user_id=user_id, error=str(e))
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status and configuration"""
        rate_limit_status = self.rate_limiter.get_rate_limit_status()
        
        return {
            "status": "operational",
            "api_version": self.api_version,
            "base_url": self.base_url,
            "supports_uuids": self.supports_uuids,
            "backward_compatibility": self.backward_compatibility,
            "cache_size": len(self.cache),
            "rate_limiting": rate_limit_status,
            "configuration": {
                "max_retries": self.max_retries,
                "retry_base_delay": self.retry_base_delay,
                "request_timeout": self.request_timeout
            }
        }


# Create singleton instance
whoop_service = WhoopAPIService()

# Export service instance and class
__all__ = ["WhoopAPIService", "whoop_service"]