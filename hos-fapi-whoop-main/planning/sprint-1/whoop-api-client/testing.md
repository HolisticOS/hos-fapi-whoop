# Sprint 1 - WHOOP API Client: Testing Plan

## Testing Strategy
Comprehensive testing approach for WHOOP API client focusing on HTTP communication, data parsing, error handling, and integration with WHOOP's production API endpoints.

## Test Scenarios

### 1. API Client Initialization and Session Management Tests
**Objective**: Verify proper client setup and HTTP session lifecycle management

**Test Cases**:
- **TC1.1**: Client initialization with valid access token
  - Create WhoopAPIClient with valid access token
  - Verify base_url, headers, and rate limiting setup
  - Confirm session is not created until first request
  - Test access token storage and authentication header setup

- **TC1.2**: HTTP session lifecycle management
  - Test _get_session() method creates session on first call
  - Verify session reuse for subsequent requests
  - Test session closure during client cleanup
  - Confirm session timeout and connection pool configuration

- **TC1.3**: Session error recovery
  - Test session recreation after connection failure
  - Test handling of closed session during requests
  - Verify session cleanup prevents resource leaks
  - Test concurrent session access safety

### 2. Rate Limiting Implementation Tests
**Objective**: Ensure API rate limits are respected and enforced correctly

**Test Cases**:
- **TC2.1**: Rate limiting enforcement
  - Test _rate_limit() method delays between rapid requests
  - Verify minimum interval calculation based on settings
  - Test rate limiting with different API call frequencies
  - Confirm rate limiting doesn't block valid request patterns

- **TC2.2**: Rate limiting timing accuracy
  - Test precise timing of rate limiting delays
  - Verify rate limiting works across multiple client instances
  - Test rate limiting behavior with slow network responses
  - Confirm rate limiting resets properly after delays

- **TC2.3**: 429 Rate limiting response handling
  - Mock 429 response with Retry-After header
  - Test automatic retry after rate limit delay
  - Verify exponential backoff for repeated rate limiting
  - Test rate limiting error propagation and logging

### 3. Authentication and Token Management Tests
**Objective**: Validate Bearer token authentication and token refresh integration

**Test Cases**:
- **TC3.1**: Bearer token authentication
  - Test Authorization header added to all requests
  - Verify token format in HTTP headers
  - Test authentication with valid and invalid tokens
  - Confirm authentication header consistency across requests

- **TC3.2**: Token refresh integration
  - Mock 401 unauthorized response from API
  - Test automatic token refresh trigger
  - Verify request retry after successful token refresh
  - Test token refresh failure handling and error propagation

- **TC3.3**: Token validation and error handling
  - Test token expiration detection
  - Test malformed token handling
  - Verify token validation before API requests
  - Test token refresh loop prevention

### 4. User Profile API Tests
**Objective**: Validate user profile retrieval and data parsing

**Test Cases**:
- **TC4.1**: Successful profile retrieval
  - Mock valid profile API response with complete user data
  - Test get_user_profile() method with valid token
  - Verify user_id, email, and profile data extraction
  - Confirm response parsing and data validation

- **TC4.2**: Profile API error handling
  - Mock 404 response for non-existent user
  - Mock malformed JSON response from profile API
  - Test network timeout during profile request
  - Verify appropriate error messages and exception types

- **TC4.3**: Profile data validation
  - Test profile response with missing required fields
  - Test profile response with invalid data types
  - Verify profile data sanitization and validation
  - Test profile data conversion to internal models

### 5. Recovery Data API Tests
**Objective**: Ensure proper recovery data retrieval and processing

**Test Cases**:
- **TC5.1**: Current cycle retrieval
  - Mock valid current cycle API response
  - Test get_current_cycle() method functionality
  - Verify cycle_id extraction and cycle data parsing
  - Test handling of no current cycle scenario

- **TC5.2**: Recovery data by cycle ID
  - Mock recovery data response for specific cycle
  - Test get_recovery_by_cycle_id() method
  - Verify recovery score, HRV, and heart rate extraction
  - Test skin temperature and other metric parsing

- **TC5.3**: Recovery data error scenarios
  - Mock 404 response for non-existent cycle
  - Test recovery API timeout and network failures
  - Test incomplete recovery data handling
  - Verify recovery data validation and quality checks

### 6. Sleep Data API Tests
**Objective**: Validate sleep data collection and pagination handling

**Test Cases**:
- **TC6.1**: Sleep collection with date range
  - Mock paginated sleep API response with multiple pages
  - Test get_sleep_collection() with start and end dates
  - Verify date range parameter formatting and encoding
  - Test sleep data aggregation across multiple API calls

- **TC6.2**: Sleep data pagination handling
  - Mock sleep API responses with next_token pagination
  - Test automatic pagination through multiple pages
  - Verify complete dataset collection across all pages
  - Test pagination timeout and error handling

- **TC6.3**: Sleep data parsing and validation
  - Mock sleep responses with various sleep record formats
  - Test sleep timing, duration, and efficiency extraction
  - Verify sleep score and quality metric parsing
  - Test sleep data spanning multiple dates

### 7. Workout Data API Tests
**Objective**: Ensure workout data retrieval and activity processing

**Test Cases**:
- **TC7.1**: Workout collection with filtering
  - Mock workout API response with various activity types
  - Test get_workout_collection() with date filtering
  - Verify workout timing, duration, and intensity parsing
  - Test sport classification and activity categorization

- **TC7.2**: Workout data aggregation
  - Mock workout responses with multiple activities per day
  - Test workout data aggregation by date
  - Verify strain scores, heart rate, and calorie extraction
  - Test workout data quality validation

- **TC7.3**: Workout API error handling
  - Mock workout API errors and empty responses
  - Test workout data with missing or invalid fields
  - Verify workout API timeout and retry handling
  - Test workout data transformation error scenarios

## Test Data Requirements

### Mock API Response Data
```json
// User profile response
{
  "user_id": 12345,
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User",
  "created_at": "2023-01-01T00:00:00Z"
}

// Current cycle response
{
  "data": [{
    "id": 67890,
    "user_id": 12345,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T06:00:00Z",
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-01-02T00:00:00Z"
  }]
}

// Recovery data response
{
  "cycle_id": 67890,
  "sleep_id": 98765,
  "user_id": 12345,
  "created_at": "2024-01-01T08:00:00Z",
  "updated_at": "2024-01-01T08:00:00Z",
  "score": {
    "user_calibrating": false,
    "recovery_score": 85.5,
    "hrv_rmssd_milli": 45.2,
    "resting_heart_rate": 55,
    "skin_temp_celsius": 33.2
  }
}

// Sleep collection response
{
  "data": [{
    "id": 98765,
    "user_id": 12345,
    "created_at": "2024-01-01T07:30:00Z",
    "updated_at": "2024-01-01T07:30:00Z",
    "start": "2024-01-01T22:30:00Z",
    "end": "2024-01-02T06:30:00Z",
    "score": {
      "sleep_performance_percentage": 88,
      "sleep_consistency_percentage": 92,
      "sleep_efficiency_percentage": 95
    }
  }],
  "next_token": "eyJzdWIiOiIxMjM0..."
}

// Workout collection response
{
  "data": [{
    "id": 54321,
    "user_id": 12345,
    "created_at": "2024-01-01T18:00:00Z",
    "updated_at": "2024-01-01T18:00:00Z",
    "start": "2024-01-01T17:00:00Z",
    "end": "2024-01-01T18:00:00Z",
    "sport_id": 1,
    "score": {
      "strain": 12.5,
      "average_heart_rate": 145,
      "max_heart_rate": 172,
      "kilojoule": 850
    }
  }]
}
```

### Error Response Mocking
```json
// Authentication error
{
  "error": "Unauthorized",
  "message": "Invalid or expired access token"
}

// Rate limiting error
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded"
}

// General API error
{
  "error": "Bad Request",
  "message": "Invalid date range parameters"
}
```

### Test Environment Configuration
```bash
# Test API settings
WHOOP_API_BASE_URL=https://api.test.whoop.com/developer/v1
WHOOP_API_CALLS_PER_MINUTE=90
ACCESS_TOKEN=test_access_token_12345
TEST_USER_ID=test_user_12345
```

## Testing Steps

### Phase 1: Unit Testing (Isolated Components)
1. **Client initialization tests** (2 hours)
   - Test WhoopAPIClient constructor with various parameters
   - Test session management methods in isolation
   - Test rate limiting logic with mock timing
   - Verify authentication header setup and formatting

2. **API method unit tests** (3 hours)
   - Test individual API methods with mock responses
   - Test request parameter formatting and validation
   - Test response parsing and data extraction
   - Mock all HTTP calls for isolated testing

3. **Error handling unit tests** (2 hours)
   - Test exception handling for various error conditions
   - Test retry logic with mock HTTP failures
   - Test token refresh integration with mock responses
   - Verify error message formatting and logging

### Phase 2: Integration Testing (HTTP Communication)
1. **Mock API integration tests** (3 hours)
   - Test complete API workflows with aioresponses mocks
   - Test pagination handling with multiple mock responses
   - Test rate limiting with realistic timing scenarios
   - Verify session lifecycle across multiple requests

2. **Error scenario integration tests** (2 hours)
   - Test network timeout and connection failure handling
   - Test API error response processing
   - Test rate limiting response handling with delays
   - Verify error recovery and retry mechanisms

### Phase 3: Live API Testing (Real WHOOP API)
1. **Authentication testing** (1 hour)
   - Test real authentication with valid tokens
   - Test token validation with WHOOP profile endpoint
   - Verify authentication error handling with invalid tokens
   - Test token refresh with real OAuth service integration

2. **Data retrieval testing** (2 hours)
   - Test profile, recovery, sleep, and workout data retrieval
   - Verify real API response parsing and validation
   - Test date range queries with actual user data
   - Validate data quality and completeness

## Automated Test Requirements

### Unit Test Structure
```python
@pytest.mark.asyncio
async def test_whoop_client_initialization():
    """Test client initialization with valid token"""
    
@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    """Test rate limiting prevents rapid requests"""
    
@pytest.mark.asyncio
async def test_get_user_profile_success():
    """Test successful user profile retrieval"""
    
@pytest.mark.asyncio
async def test_sleep_collection_pagination():
    """Test sleep data pagination handling"""
```

### Mock Configuration
```python
@pytest.fixture
def mock_whoop_responses():
    """Mock WHOOP API responses for testing"""
    with aioresponses() as m:
        # Profile endpoint
        m.get('https://api.test.whoop.com/developer/v1/user/profile',
              payload=mock_profile_response)
        
        # Recovery endpoint
        m.get(re.compile(r'.*/cycle/.*/recovery'),
              payload=mock_recovery_response)
        
        # Sleep endpoint with pagination
        m.get(re.compile(r'.*/activity/sleep.*'),
              payload=mock_sleep_response)
        
        yield m
```

### Performance Test Requirements
```python
@pytest.mark.asyncio
async def test_client_performance():
    """Test API client performance under load"""
    # Test multiple concurrent requests
    # Verify rate limiting doesn't cause excessive delays
    # Test memory usage during large data retrievals
```

## Performance Criteria

### Response Time Requirements
- **User profile retrieval**: < 2 seconds
- **Recovery data retrieval**: < 3 seconds
- **Sleep data collection**: < 5 seconds per day of data
- **Workout data collection**: < 5 seconds per day of data

### Rate Limiting Compliance
- **Request frequency**: Maximum 90 requests per minute
- **Daily limits**: Stay under 9,000 requests per day for testing
- **Burst handling**: Proper delays for rapid request bursts
- **Rate limiting recovery**: < 60 seconds recovery time

### Resource Usage Limits
- **Memory usage**: < 50MB for typical data retrieval operations
- **Connection pooling**: < 10 concurrent connections per client
- **Session lifetime**: Proper cleanup prevents resource leaks
- **Request timeout**: 10 seconds maximum per API call

## Error Scenario Testing

### Network Error Scenarios
- **Connection timeout**: API unavailable or slow responses
- **DNS resolution failure**: WHOOP API domain unavailable
- **SSL/TLS errors**: Certificate or encryption issues
- **Network interruption**: Connection drops during requests

### API Error Scenarios
- **401 Unauthorized**: Invalid or expired tokens
- **403 Forbidden**: Insufficient permissions or disabled account
- **429 Rate Limited**: API quota exceeded
- **500 Server Error**: WHOOP API internal failures
- **502/503 Gateway Errors**: WHOOP infrastructure issues

### Data Error Scenarios
- **Malformed JSON**: Invalid or incomplete API responses
- **Missing fields**: Required data fields absent from responses
- **Invalid data types**: Data type mismatches in responses
- **Large datasets**: Memory and performance issues with large responses

## Success Criteria

### Functional Success
- [ ] All WHOOP API endpoints accessible with proper authentication
- [ ] Complete health data retrieval (profile, recovery, sleep, workouts)
- [ ] Pagination handling works for large datasets
- [ ] Rate limiting respects WHOOP API constraints
- [ ] Error handling provides clear and actionable messages

### Performance Success
- [ ] API calls complete within performance criteria
- [ ] Rate limiting doesn't cause excessive delays
- [ ] Memory usage remains stable during data operations
- [ ] Concurrent requests handled properly without conflicts

### Integration Success
- [ ] OAuth service integration works for token management
- [ ] Token refresh triggers automatically on 401 responses
- [ ] Database integration supports token storage and retrieval
- [ ] Error propagation maintains system stability

### Quality Success
- [ ] Test coverage > 85% for API client functionality
- [ ] All error scenarios tested and handled gracefully
- [ ] Real API integration tested with valid credentials
- [ ] Performance testing validates resource usage limits