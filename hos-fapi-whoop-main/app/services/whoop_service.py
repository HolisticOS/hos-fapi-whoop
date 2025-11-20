"""
WHOOP API Service Implementation
Handles UUID identifiers for Sleep and Workout resources
Extends the existing API client with v2-specific functionality
Integrates with Supabase authentication (UUID-based user_id)
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date, timedelta, timezone
from uuid import UUID
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
        supabase_user_id: UUID,
        params: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        bypass_cache: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to WHOOP API with UUID handling

        Args:
            method: HTTP method
            endpoint: API endpoint path
            supabase_user_id: Supabase UUID from auth.users.id (from JWT token)
            params: Query parameters
            cache_key: Cache key for response caching
            bypass_cache: Skip cache lookup

        Returns:
            API response data or None if failed
        """
        # Convert UUID to string for logging and cache keys
        user_id_str = str(supabase_user_id)

        # Check cache first
        if cache_key and not bypass_cache:
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.info("cache hit", cache_key=cache_key, supabase_user_id=supabase_user_id)
                return cached_response

        # Get valid access token from database using Supabase UUID
        from app.services.auth_service import WhoopAuthService
        auth_service = WhoopAuthService()
        access_token = await auth_service.get_valid_token(supabase_user_id)

        if not access_token:
            logger.error("No valid access token for user", supabase_user_id=supabase_user_id)
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
                               supabase_user_id=supabase_user_id, endpoint=endpoint)
                    return None

                async with httpx.AsyncClient() as client:
                    logger.info(f"Making {method} request",
                               endpoint=endpoint,
                               attempt=attempt + 1,
                               supabase_user_id=supabase_user_id)
                    
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
                                   supabase_user_id=supabase_user_id,
                                   response_size=len(str(data)))
                        return data

                    elif response.status_code == 401:
                        # Unauthorized - attempt token refresh
                        logger.warning("API unauthorized, attempting token refresh",
                                     supabase_user_id=supabase_user_id)

                        # Token refresh is now handled automatically by auth_service
                        # Try to get a fresh token
                        fresh_token = await auth_service.get_valid_token(supabase_user_id)
                        if fresh_token and fresh_token != access_token:
                            headers['Authorization'] = f'Bearer {fresh_token}'
                            continue

                        logger.error("API authentication failed after refresh",
                                   supabase_user_id=supabase_user_id)
                        return None

                    elif response.status_code == 404:
                        # Resource not found - could be v1/v2 ID mismatch
                        logger.warning("API resource not found",
                                     endpoint=endpoint,
                                     supabase_user_id=supabase_user_id,
                                     status_code=response.status_code)
                        return None

                    elif response.status_code == 429:
                        # Rate limited
                        retry_after = response.headers.get('Retry-After', '60')
                        retry_delay = int(retry_after)

                        logger.warning("API rate limited",
                                     retry_after=retry_delay,
                                     supabase_user_id=supabase_user_id)
                        
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
                                   supabase_user_id=supabase_user_id)
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
                             supabase_user_id=supabase_user_id)

                if attempt < self.max_retries:
                    delay = self.retry_base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None

            except Exception as e:
                logger.error("Unexpected error in API request",
                           endpoint=endpoint,
                           supabase_user_id=supabase_user_id,
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
            user_id: User identifier (Supabase UUID as string)
            start_date: Start date in ISO format (currently ignored due to v2 API issue)
            end_date: End date in ISO format (currently ignored due to v2 API issue)
            next_token: Pagination token
            limit: Number of records to retrieve

        Returns:
            WhoopSleepCollection with sleep records
        """
        try:
            # Convert string UUID to UUID type
            supabase_user_uuid = UUID(user_id)

            # NOTE: WHOOP v2 sleep endpoint doesn't reliably support date filtering
            # Using limit only to get most recent records
            # WHOOP API max limit is 25
            params = {
                "limit": min(limit, 25)
            }

            if next_token:
                params["nextToken"] = next_token

            cache_key = f"sleep_{user_id}_recent_{limit}" if not next_token else None

            response_data = await self._make_request(
                method="GET",
                endpoint="activity/sleep",
                supabase_user_id=supabase_user_uuid,
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
                    
                    # Extract score data (nested in v2 API response)
                    score_data = record.get("score", {}) or {}

                    # Create v2 sleep data model using actual API field names
                    sleep_data = WhoopSleepData(
                        id=record_id,
                        activity_v1_id=record.get("v1_id"),  # API returns "v1_id" not "activityV1Id"
                        user_id=record["user_id"],  # API returns "user_id" as int
                        start=record["start"],
                        end=record["end"],
                        timezone_offset=record.get("timezone_offset"),
                        # Extract from nested score object if available
                        total_sleep_time_milli=score_data.get("total_sleep_time_milli") or score_data.get("stage_summary", {}).get("total_in_bed_time_milli"),
                        time_in_bed_milli=score_data.get("stage_summary", {}).get("total_in_bed_time_milli"),
                        cycle_id=record.get("cycle_id"),
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
            
            # Note: Raw data storage moved to get_comprehensive_data to avoid duplicates during pagination

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
            user_id: User identifier (Supabase UUID as string)
            start_date: Start date in ISO format
            end_date: End date in ISO format
            next_token: Pagination token
            limit: Number of records to retrieve

        Returns:
            WhoopWorkoutCollection with workout records
        """
        try:
            # Convert string UUID to UUID type
            supabase_user_uuid = UUID(user_id)

            # NOTE: WHOOP v2 workout endpoint doesn't reliably support date filtering
            # Using limit only to get most recent records
            # WHOOP API max limit is 25
            params = {
                "limit": min(limit, 25)
            }

            if next_token:
                params["nextToken"] = next_token

            cache_key = f"workout_{user_id}_recent_{limit}" if not next_token else None

            response_data = await self._make_request(
                method="GET",
                endpoint="activity/workout",
                supabase_user_id=supabase_user_uuid,
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
                    
                    # Extract score data (nested in v2 API response)
                    score_data = record.get("score", {}) or {}

                    # Create v2 workout data model with proper field extraction
                    workout_data = WhoopWorkoutData(
                        id=record_id,
                        activity_v1_id=record.get("v1_id"),  # API returns "v1_id"
                        user_id=record["user_id"],  # API returns "user_id" as int
                        sport_id=record["sport_id"],  # API returns "sport_id" not "sportId"
                        sport_name=record.get("sport_name"),  # API returns "sport_name"
                        start=record["start"],
                        end=record["end"],
                        timezone_offset=record.get("timezone_offset"),
                        # Extract from nested score object
                        strain_score=score_data.get("strain"),
                        average_heart_rate=score_data.get("average_heart_rate"),
                        max_heart_rate=score_data.get("max_heart_rate"),
                        calories_burned=score_data.get("kilojoule"),  # API uses kilojoule
                        distance_meters=score_data.get("distance_meter"),
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
            
            # Note: Raw data storage moved to get_comprehensive_data to avoid duplicates during pagination

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
            user_id: User identifier (Supabase UUID as string)
            start_date: Start date in ISO format
            end_date: End date in ISO format
            next_token: Pagination token
            limit: Number of records to retrieve

        Returns:
            WhoopRecoveryCollection with recovery records
        """
        try:
            # Convert string UUID to UUID type
            supabase_user_uuid = UUID(user_id)

            # Build query parameters
            # Note: WHOOP v2 API uses ISO 8601 format (YYYY-MM-DDTHH:MM:SS.sssZ)
            # WHOOP API max limit is 25
            params = {
                "limit": min(limit, 25),
                "start": start_date,  # ISO format string
                "end": end_date      # ISO format string
            }

            if next_token:
                params["nextToken"] = next_token

            cache_key = f"recovery_{user_id}_{start_date}_{end_date}_{limit}" if not next_token else None

            # Try recovery endpoint - may need to use cycle endpoint instead in v2
            response_data = await self._make_request(
                method="GET",
                endpoint="recovery",  # Try /v2/recovery first
                supabase_user_id=supabase_user_uuid,
                params=params,
                cache_key=cache_key
            )

            # If 404, recovery might not have standalone endpoint in v2
            # May need to fetch through cycles instead

            if not response_data:
                logger.warning("⚠️ No recovery response data from API",
                             user_id=user_id,
                             endpoint="recovery",
                             note="May need to fetch recovery through /v2/cycle endpoint instead")
                return WhoopRecoveryCollection()

            logger.info("📦 Processing recovery API response",
                       user_id=user_id,
                       records_count=len(response_data.get("records", [])),
                       has_next_token=bool(response_data.get("next_token")))

            recovery_records = []
            for record in response_data.get("records", []):
                try:
                    logger.info("🔍 Parsing recovery record",
                                user_id=user_id,
                                cycle_id=record.get("cycle_id"),
                                has_score=bool(record.get("score")),
                                has_created_at=bool(record.get("created_at")))

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
                    logger.info("✅ Successfully parsed recovery record",
                               user_id=user_id,
                               cycle_id=record.get("cycle_id"))

                except Exception as parse_error:
                    logger.warning("❌ Failed to parse v2 recovery record",
                                 user_id=user_id,
                                 cycle_id=record.get("cycle_id"),
                                 has_cycle_id=bool(record.get("cycle_id")),
                                 has_user_id=bool(record.get("user_id")),
                                 has_created_at=bool(record.get("created_at")),
                                 error=str(parse_error),
                                 error_type=type(parse_error).__name__)
            
            collection = WhoopRecoveryCollection(
                records=recovery_records,
                next_token=response_data.get("next_token"),
                total_count=len(recovery_records)
            )
            
            logger.info("✅ Retrieved v2 recovery data", 
                       user_id=user_id,
                       count=len(recovery_records),
                       has_next_token=bool(collection.next_token))
            
            # Note: Raw data storage moved to get_comprehensive_data to avoid duplicates during pagination

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
            # Calculate date range (use timezone-aware datetime for WHOOP API)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)

            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            logger.info("📊 Fetching comprehensive data", 
                       user_id=user_id,
                       date_range=f"{start_date.date()} to {end_date.date()}")
            
            # Fetch all data types concurrently (limit based on days_back)
            # Sleep, recovery, workout: fetch directly from API
            # Cycle: skip for now (returns 404)
            limit = min(days_back, 25)  # WHOOP API max is 25

            # Fetch sleep, recovery, and workout in parallel
            sleep_collection = await self.get_sleep_data(user_id, start_iso, end_iso, limit=limit)
            recovery_collection = await self.get_recovery_data(user_id, start_iso, end_iso, limit=limit)

            # For workouts, fetch max 25 records (no pagination)
            workout_collection = await self.get_workout_data(user_id, start_iso, end_iso, limit=25)

            # Try to fetch cycle data (may return 404 if endpoint not available)
            logger.info("📊 Attempting to fetch cycle data",
                       user_id=user_id,
                       start_iso=start_iso,
                       end_iso=end_iso,
                       limit=limit * 2)

            cycle_collection = await self.get_cycle_data(user_id, start_iso, end_iso, limit=limit * 2)

            if not cycle_collection or not cycle_collection.data:
                logger.warning("⚠️ Cycle data not available (endpoint may not be accessible)",
                             user_id=user_id,
                             has_collection=bool(cycle_collection))
                cycle_collection = WhoopCycleCollection(data=[], next_token=None)
            else:
                logger.info("✅ Retrieved cycle data",
                           user_id=user_id,
                           cycle_count=len(cycle_collection.data))
            
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
                cycle_data=cycle_collection.data if cycle_collection else [],
                total_records=(
                    len(sleep_collection.records) +
                    len(workout_collection.records) +
                    len(recovery_collection.records) +
                    (len(cycle_collection.data) if cycle_collection and cycle_collection.data else 0)
                ),
                api_version="v2"
            )

            logger.info("✅ Comprehensive v2 data fetch completed",
                       user_id=user_id,
                       sleep_count=len(response.sleep_data),
                       workout_count=len(response.workout_data),
                       recovery_count=len(response.recovery_data),
                       cycle_count=len(response.cycle_data),
                       total_records=response.total_records)

            # Store raw data in whoop_raw_data table (one entry per data type)
            # Extract raw_data from each record to store as array
            if sleep_collection.records:
                sleep_raw = [s.raw_data for s in sleep_collection.records if s.raw_data]
                logger.info("💾 Storing sleep raw data to whoop_raw_data table",
                           user_id=user_id,
                           count=len(sleep_raw))
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="sleep",
                    records=sleep_raw,
                    api_endpoint="activity/sleep"
                )

            if workout_collection.records:
                workout_raw = [w.raw_data for w in workout_collection.records if w.raw_data]
                logger.info("💾 Storing workout raw data to whoop_raw_data table",
                           user_id=user_id,
                           count=len(workout_raw))
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="workout",
                    records=workout_raw,
                    api_endpoint="activity/workout"
                )

            if recovery_collection.records:
                recovery_raw = [r.raw_data for r in recovery_collection.records if r.raw_data]
                logger.info("💾 Storing recovery raw data to whoop_raw_data table",
                           user_id=user_id,
                           count=len(recovery_raw))
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="recovery",
                    records=recovery_raw,
                    api_endpoint="recovery"
                )
            else:
                logger.warning("⚠️ No recovery data to store in raw_data table",
                             user_id=user_id,
                             recovery_collection_empty=len(recovery_collection.records) == 0)

            # Store cycle raw data
            if cycle_collection and cycle_collection.data:
                cycle_raw = [c.raw_data for c in cycle_collection.data if hasattr(c, 'raw_data') and c.raw_data]
                logger.info("💾 Storing cycle raw data to whoop_raw_data table",
                           user_id=user_id,
                           count=len(cycle_raw))
                await self.raw_storage.store_whoop_data(
                    user_id=user_id,
                    data_type="cycle",
                    records=cycle_raw,
                    api_endpoint="cycle"
                )

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
            user_id: User identifier (Supabase UUID as string)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            next_token: Pagination token
            limit: Number of records to fetch (max 50)

        Returns:
            WhoopCycleCollection or None if error
        """
        try:
            # Convert string UUID to UUID type
            supabase_user_uuid = UUID(user_id)

            # Build query parameters
            # Note: WHOOP v2 API uses ISO 8601 format (YYYY-MM-DDTHH:MM:SS.sssZ)
            # WHOOP API max limit is 25
            params = {
                "limit": min(limit, 25),
                "start": start_date,  # ISO format string
                "end": end_date      # ISO format string
            }

            if next_token:
                params["nextToken"] = next_token

            response_data = await self._make_request(
                method="GET",
                endpoint="cycle",
                supabase_user_id=supabase_user_uuid,
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
            
            # Note: Raw data storage moved to get_comprehensive_data to avoid duplicates during pagination

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