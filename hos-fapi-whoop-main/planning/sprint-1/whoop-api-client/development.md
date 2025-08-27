# Sprint 1 - WHOOP API Client: Development Plan

## Feature Description
Implement a comprehensive WHOOP API client for retrieving health data including recovery metrics, sleep data, workout information, and user profiles. The client provides rate-limited, authenticated access to WHOOP's REST API with proper error handling, retry logic, and data transformation.

## Technical Requirements
- **HTTP Client**: aiohttp-based async client with connection pooling
- **Authentication**: Bearer token authentication with automatic refresh
- **Rate Limiting**: Respect WHOOP API limits (100 requests/minute, 10K/day)
- **Error Handling**: Comprehensive error handling with retries and circuit breaking
- **Data Models**: Pydantic models for type safety and validation
- **Pagination**: Support for WHOOP API pagination with next_token handling
- **Timeouts**: Configurable request timeouts with graceful failure handling

## Dependencies
- **Internal**: OAuth service for token management and refresh
- **External**: WHOOP API endpoints and valid access tokens
- **Libraries**: aiohttp, pydantic, asyncio, datetime, logging
- **Configuration**: WHOOP_API_BASE_URL, rate limiting settings
- **Database**: User token storage for authentication

## Steps to Implement

### Step 1: Core API Client Structure (6 hours)
1. **Client class foundation** (2 hours)
   - Create app/services/whoop_service.py with WhoopAPIClient class
   - Implement constructor with access token and configuration
   - Set up aiohttp ClientSession with proper timeout configuration
   - Initialize rate limiting variables and request tracking

2. **HTTP session management** (2 hours)
   - Implement _get_session() method with connection pooling
   - Configure session timeouts, headers, and connection limits
   - Add session lifecycle management (creation, reuse, cleanup)
   - Implement proper session closure and resource cleanup

3. **Rate limiting implementation** (2 hours)
   - Implement _rate_limit() method using asyncio timing
   - Calculate minimum request intervals based on API limits
   - Track last request time and enforce delays between requests
   - Add configurable rate limiting parameters from settings

### Step 2: Core API Request Infrastructure (8 hours)
1. **Base request method** (4 hours)
   - Implement _make_request() method for all API calls
   - Add Bearer token authentication headers automatically
   - Handle HTTP response codes and error conditions
   - Implement request retry logic with exponential backoff

2. **Error handling and responses** (2 hours)
   - Handle 401 unauthorized responses with token refresh
   - Handle 429 rate limiting with Retry-After header respect
   - Handle network timeouts and connection failures
   - Create custom exceptions for different error types

3. **Response processing** (2 hours)
   - Parse JSON responses with proper error handling
   - Validate response structure and required fields
   - Handle empty responses and missing data gracefully
   - Log request/response details for debugging

### Step 3: User Profile and Authentication APIs (4 hours)
1. **User profile retrieval** (2 hours)
   - Implement get_user_profile() method for user information
   - Handle profile API response parsing and validation
   - Extract user_id, email, and basic profile information
   - Add error handling for profile access failures

2. **Token validation** (2 hours)
   - Create token validation methods using profile endpoint
   - Implement connection status checking for users
   - Add methods for testing token validity
   - Handle expired token detection and refresh triggering

### Step 4: Recovery Data API Implementation (6 hours)
1. **Current cycle retrieval** (2 hours)
   - Implement get_current_cycle() method for latest cycle data
   - Handle cycle API response and extract cycle_id
   - Parse cycle start/end times and status information
   - Handle cases where no current cycle exists

2. **Recovery data by cycle** (2 hours)
   - Implement get_recovery_by_cycle_id() for specific cycle recovery
   - Parse recovery score, HRV, resting heart rate data
   - Handle skin temperature and other recovery metrics
   - Transform API response to internal data models

3. **Recovery data aggregation** (2 hours)
   - Create helper methods for combining cycle and recovery data
   - Implement date-based recovery data retrieval
   - Handle multiple cycles per day scenarios
   - Add data validation and quality checks

### Step 5: Sleep Data API Implementation (6 hours)
1. **Sleep collection retrieval** (3 hours)
   - Implement get_sleep_collection() method with date range support
   - Handle pagination with next_token for large datasets
   - Parse sleep start/end times, duration, and efficiency
   - Extract sleep scores and sleep stage information

2. **Sleep data processing** (2 hours)
   - Transform WHOOP sleep data to internal models
   - Handle sleep records spanning multiple dates
   - Aggregate sleep metrics by date for consistency
   - Validate sleep data completeness and quality

3. **Sleep data pagination** (1 hour)
   - Implement robust pagination handling for sleep endpoints
   - Handle large date ranges with multiple API calls
   - Manage memory usage for large sleep datasets
   - Add pagination limits and safety checks

### Step 6: Workout Data API Implementation (6 hours)
1. **Workout collection retrieval** (3 hours)
   - Implement get_workout_collection() method with date filtering
   - Handle workout pagination with next_token management
   - Parse workout start/end times, duration, and intensity
   - Extract heart rate data, strain scores, and calories

2. **Workout data transformation** (2 hours)
   - Transform WHOOP workout data to internal models
   - Handle different sport types and activity classifications
   - Aggregate workout metrics by date and activity type
   - Validate workout data integrity and completeness

3. **Workout data optimization** (1 hour)
   - Optimize API calls for workout data retrieval
   - Implement efficient date range querying
   - Add workout data caching for repeated requests
   - Handle workout data updates and modifications

## Expected Output
1. **Comprehensive API client**:
   - WhoopAPIClient class with all health data retrieval methods
   - Rate-limited HTTP client with proper session management
   - Error handling and retry logic for robust operation
   - Token-based authentication with refresh support

2. **Health data retrieval**:
   - User profile information with WHOOP user ID
   - Recovery data with scores, HRV, and physiological metrics
   - Sleep data with timing, efficiency, and sleep scores
   - Workout data with activity details, strain, and heart rate

3. **Production-ready features**:
   - Configurable timeouts and rate limiting
   - Comprehensive error handling and logging
   - Resource cleanup and session management
   - Data validation and quality checks

## Acceptance Criteria
1. **API client initialization** works with valid access token
2. **User profile retrieval** returns complete profile information
3. **Recovery data retrieval** provides current and historical recovery metrics
4. **Sleep data retrieval** handles date ranges and pagination correctly
5. **Workout data retrieval** processes activity data with proper parsing
6. **Rate limiting** respects WHOOP API limits and handles 429 responses
7. **Error handling** provides clear messages and appropriate exceptions
8. **Session management** properly creates, reuses, and cleans up connections

## Definition of Done
- [ ] WhoopAPIClient class implemented with all required methods
- [ ] HTTP session management with connection pooling and timeouts
- [ ] Rate limiting implemented to respect WHOOP API constraints
- [ ] Bearer token authentication working with all API calls
- [ ] User profile retrieval functional with error handling
- [ ] Current cycle and recovery data retrieval implemented
- [ ] Sleep data collection with pagination support completed
- [ ] Workout data collection with date filtering operational
- [ ] Comprehensive error handling for all API failure scenarios
- [ ] Request retry logic with exponential backoff implemented
- [ ] Session cleanup and resource management working
- [ ] Integration with OAuth service for token refresh
- [ ] Unit tests cover all API client functionality
- [ ] Integration tests verify actual API communication
- [ ] Documentation includes API usage examples and error handling

## Quality Gates
- **API Integration**: All WHOOP API endpoints tested with real tokens
- **Rate Limiting**: Confirmed to respect API limits under load
- **Error Handling**: All error scenarios tested and handled gracefully
- **Performance**: API calls complete within timeout constraints
- **Memory Management**: No memory leaks during session lifecycle
- **Security**: No token leakage in logs or error messages