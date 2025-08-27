# Sprint 1 - Internal APIs: Testing Plan

## Testing Strategy
Comprehensive testing approach for internal API endpoints focusing on authentication, OAuth flow integration, health data retrieval, error handling, and service-to-service communication patterns.

## Test Scenarios

### 1. Service Authentication and Security Tests
**Objective**: Verify internal API authentication and access control mechanisms

**Test Cases**:
- **TC1.1**: Valid API key authentication
  - Test requests with valid SERVICE_API_KEY header
  - Verify successful authentication and request processing
  - Test API key validation logic and header parsing
  - Confirm authenticated requests access all internal endpoints

- **TC1.2**: Invalid API key handling
  - Test requests with invalid API key
  - Test requests with missing API key header
  - Test requests with expired or malformed API keys
  - Verify 401 Unauthorized responses with proper error messages

- **TC1.3**: Authentication bypass prevention
  - Test attempts to access endpoints without authentication
  - Test manipulation of authentication headers
  - Verify authentication middleware protects all internal routes
  - Test authentication with different header formats and cases

### 2. OAuth Management Endpoint Tests
**Objective**: Validate OAuth initiation, callback handling, and user connection management

**Test Cases**:
- **TC2.1**: OAuth initiation endpoint (POST /internal/oauth/initiate)
  - Test with valid user_id parameter
  - Verify authorization URL generation with proper parameters
  - Test state parameter generation and format
  - Confirm OAuth service integration and response formatting

- **TC2.2**: OAuth callback endpoint (POST /internal/oauth/callback)
  - Test with valid authorization code, state, and user_id
  - Mock successful token exchange and database storage
  - Verify callback response includes connection status
  - Test error handling for invalid authorization codes

- **TC2.3**: User connection status endpoint (GET /internal/oauth/status/{user_id})
  - Test with connected user returning complete status
  - Test with non-existent user returning appropriate response
  - Test with expired tokens showing refresh requirements
  - Verify status response includes all required connection metadata

### 3. User Connection Management Tests
**Objective**: Ensure proper user disconnection and connection validation functionality

**Test Cases**:
- **TC3.1**: User disconnection endpoint (DELETE /internal/oauth/disconnect/{user_id})
  - Test disconnection of connected user
  - Test disconnection of already disconnected user
  - Test disconnection of non-existent user
  - Verify token deactivation in database and cleanup confirmation

- **TC3.2**: Connection validation endpoint (POST /internal/oauth/validate/{user_id})
  - Test validation with valid tokens making profile API call
  - Test validation triggering token refresh for expired tokens
  - Test validation failure with invalid tokens
  - Verify detailed validation response with token status information

- **TC3.3**: OAuth error scenario handling
  - Test OAuth service failures during initiation
  - Test token exchange failures during callback
  - Test database failures during token storage
  - Verify proper error propagation and client-friendly messages

### 4. Health Data Retrieval Endpoint Tests
**Objective**: Validate health data endpoints return properly formatted WHOOP data

**Test Cases**:
- **TC4.1**: User profile endpoint (GET /internal/data/profile/{user_id})
  - Test profile retrieval with valid connected user
  - Mock WHOOP profile API response and verify data transformation
  - Test profile retrieval triggering token refresh
  - Test profile retrieval with disconnected user

- **TC4.2**: Recovery data endpoint (GET /internal/data/recovery/{user_id})
  - Test recovery data retrieval with date parameters
  - Mock WHOOP recovery API responses with various data scenarios
  - Test recovery data with missing or incomplete metrics
  - Verify recovery data formatting and response structure

- **TC4.3**: Sleep data endpoint (GET /internal/data/sleep/{user_id})
  - Test sleep data with date range parameters
  - Mock paginated sleep API responses
  - Test sleep data aggregation across multiple API calls
  - Verify sleep data formatting with timing and score information

### 5. Workout Data and Combined Endpoint Tests
**Objective**: Ensure workout data retrieval and combined health data functionality

**Test Cases**:
- **TC5.1**: Workout data endpoint (GET /internal/data/workouts/{user_id})
  - Test workout data with date filtering
  - Mock workout API responses with various activity types
  - Test workout data processing and activity classification
  - Verify workout data includes strain, heart rate, and performance metrics

- **TC5.2**: Combined health data endpoint (GET /internal/data/health/{user_id})
  - Test comprehensive health data retrieval combining all sources
  - Mock all WHOOP API endpoints for complete data response
  - Test partial data scenarios with some API failures
  - Verify combined response structure and data organization

- **TC5.3**: Data caching and optimization
  - Test caching behavior for repeated requests
  - Test cache invalidation based on data age
  - Test request deduplication for concurrent identical requests
  - Verify caching doesn't return stale data inappropriately

### 6. Error Handling and Edge Case Tests
**Objective**: Validate comprehensive error handling and edge case management

**Test Cases**:
- **TC6.1**: Invalid user ID handling
  - Test all endpoints with non-existent user IDs
  - Test endpoints with malformed user ID formats
  - Test endpoints with empty or null user ID parameters
  - Verify consistent 404 responses for invalid users

- **TC6.2**: Parameter validation and sanitization
  - Test date parameters with invalid formats
  - Test date ranges with invalid start/end combinations
  - Test query parameters with injection attempts
  - Verify parameter validation errors with detailed field information

- **TC6.3**: External service failure handling
  - Mock WHOOP API failures for all health data endpoints
  - Mock database connection failures during operations
  - Mock OAuth service failures during authentication flows
  - Verify graceful degradation and appropriate error responses

## Test Data Requirements

### Authentication Test Data
```bash
# Valid service API key
SERVICE_API_KEY=internal_api_key_12345_valid

# Invalid API keys for testing
INVALID_API_KEY=invalid_key_test
EXPIRED_API_KEY=expired_key_12345
MALFORMED_API_KEY=malformed%20key%20test
```

### OAuth Test Data
```json
// OAuth initiation request
{
  "user_id": "test_user_12345"
}

// OAuth initiation response
{
  "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth?client_id=...",
  "state": "test_user_12345:random_state_token"
}

// OAuth callback request
{
  "code": "oauth_authorization_code_12345",
  "state": "test_user_12345:random_state_token",
  "user_id": "test_user_12345"
}

// Connection status response
{
  "user_id": "test_user_12345",
  "connected": true,
  "whoop_user_id": "whoop_user_67890",
  "connection_date": "2024-01-01T10:00:00Z",
  "token_expires_at": "2024-01-02T10:00:00Z"
}
```

### Health Data Mock Responses
```json
// Profile data response
{
  "user_id": "test_user_12345",
  "profile": {
    "user_id": 67890,
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User"
  },
  "source": "whoop",
  "last_updated": "2024-01-01T12:00:00Z"
}

// Combined health data response
{
  "user_id": "test_user_12345",
  "date": "2024-01-01",
  "source": "whoop",
  "profile": { /* profile data */ },
  "recovery": { /* recovery metrics */ },
  "sleep": { /* sleep data */ },
  "workouts": [ /* workout array */ ],
  "last_updated": "2024-01-01T12:00:00Z"
}
```

### Error Response Formats
```json
// Authentication error
{
  "error": "Unauthorized",
  "type": "authentication_error",
  "message": "Invalid or missing API key",
  "timestamp": "2024-01-01T12:00:00Z"
}

// Validation error
{
  "error": "Validation Error",
  "type": "validation_error",
  "message": "Invalid date format",
  "details": [
    {
      "field": "date",
      "message": "Date must be in YYYY-MM-DD format"
    }
  ],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Testing Steps

### Phase 1: Unit Testing (Individual Endpoint Logic)
1. **Authentication middleware testing** (2 hours)
   - Test API key validation logic in isolation
   - Test authentication dependency creation and validation
   - Test authentication error handling and response formatting
   - Mock all external dependencies for isolated testing

2. **OAuth endpoint unit tests** (3 hours)
   - Test OAuth initiation logic with mock OAuth service
   - Test callback processing with mock token exchange
   - Test connection status logic with mock database queries
   - Isolate endpoint logic from external service calls

3. **Health data endpoint unit tests** (3 hours)
   - Test health data endpoints with mock WHOOP API client
   - Test data transformation and response formatting logic
   - Test error handling for API client failures
   - Test parameter validation and sanitization

### Phase 2: Integration Testing (API Workflow Testing)
1. **OAuth flow integration tests** (3 hours)
   - Test complete OAuth flow from initiation to callback completion
   - Test OAuth integration with database storage
   - Test connection status updates during OAuth flow
   - Use mock external services but real internal integration

2. **Health data integration tests** (2 hours)
   - Test health data retrieval with mock WHOOP API responses
   - Test token refresh integration during data requests
   - Test combined endpoint data aggregation
   - Test caching integration across multiple requests

3. **Error handling integration tests** (2 hours)
   - Test error propagation across service boundaries
   - Test database transaction rollback during failures
   - Test partial failure scenarios in combined endpoints
   - Test error logging and monitoring integration

### Phase 3: API Contract Testing (Full HTTP Testing)
1. **Complete API contract tests** (3 hours)
   - Test all endpoints with real HTTP requests using TestClient
   - Test request/response serialization and validation
   - Test API documentation generation and accuracy
   - Test API versioning and backward compatibility

2. **Authentication and security tests** (1 hour)
   - Test service authentication across all endpoints
   - Test authentication header formats and edge cases
   - Test authorization bypass attempts
   - Test API access logging and security monitoring

## Automated Test Requirements

### FastAPI Test Setup
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Authentication test helper
def authenticated_headers():
    return {"X-API-Key": "internal_api_key_12345_valid"}

@pytest.fixture
def mock_oauth_service():
    """Mock OAuth service for testing"""
    with patch('app.services.oauth_service.WhoopOAuthService') as mock:
        yield mock

@pytest.fixture  
def mock_whoop_client():
    """Mock WHOOP API client for testing"""
    with patch('app.services.whoop_service.WhoopAPIClient') as mock:
        yield mock
```

### Endpoint Testing Examples
```python
def test_oauth_initiate_success():
    """Test OAuth initiation with valid user ID"""
    response = client.post(
        "/internal/oauth/initiate",
        json={"user_id": "test_user_12345"},
        headers=authenticated_headers()
    )
    assert response.status_code == 200
    assert "authorization_url" in response.json()
    assert "state" in response.json()

def test_health_data_combined():
    """Test combined health data endpoint"""
    response = client.get(
        "/internal/data/health/test_user_12345",
        headers=authenticated_headers()
    )
    assert response.status_code == 200
    data = response.json()
    assert "profile" in data
    assert "recovery" in data
    assert "sleep" in data
    assert "workouts" in data

def test_authentication_required():
    """Test endpoints require authentication"""
    response = client.get("/internal/oauth/status/test_user_12345")
    assert response.status_code == 401
```

### Mock External Services
```python
@pytest.fixture
def mock_whoop_api_responses():
    """Mock WHOOP API responses for testing"""
    with aioresponses() as m:
        # Profile endpoint
        m.get(
            re.compile(r'.*/user/profile'),
            payload={"user_id": 67890, "email": "test@example.com"}
        )
        
        # Recovery endpoint
        m.get(
            re.compile(r'.*/cycle/.*/recovery'),
            payload={"recovery_score": 85.5, "hrv_rmssd_milli": 45.2}
        )
        
        yield m
```

## Performance Criteria

### Response Time Requirements
- **OAuth endpoints**: < 2 seconds (including external API calls)
- **Health data endpoints**: < 3 seconds (including WHOOP API calls)
- **Combined health endpoint**: < 5 seconds (multiple API calls)
- **Status and validation endpoints**: < 1 second

### Concurrency Requirements
- **Concurrent requests**: Handle 10 simultaneous requests per endpoint
- **Authentication overhead**: < 10ms per request for API key validation
- **Database operations**: < 200ms for user token queries
- **Cache hit performance**: < 50ms for cached data responses

### Resource Usage Limits
- **Memory usage**: < 100MB for typical API operations
- **Database connections**: < 5 concurrent connections during testing
- **HTTP connections**: Proper connection pooling and cleanup
- **Error handling overhead**: < 5% performance impact

## Error Scenario Testing

### Authentication Error Scenarios
- **Missing API key**: No authentication header provided
- **Invalid API key**: Wrong or expired API key
- **Malformed API key**: Special characters or encoding issues
- **Authentication service failure**: Database unavailable for key validation

### OAuth Error Scenarios
- **OAuth service unavailable**: External OAuth service failures
- **Invalid authorization codes**: Expired or malformed codes
- **Database failures**: Token storage and retrieval failures
- **Token refresh failures**: Expired refresh tokens or API errors

### Health Data Error Scenarios
- **WHOOP API unavailable**: External service downtime
- **Token expiration**: Expired access tokens during data requests
- **Data parsing errors**: Invalid or malformed API responses
- **Partial data scenarios**: Some endpoints succeed, others fail

## Success Criteria

### Functional Success
- [ ] All internal API endpoints respond correctly with valid authentication
- [ ] OAuth flow endpoints handle complete authentication workflow
- [ ] Health data endpoints retrieve and format WHOOP data properly
- [ ] Combined endpoint aggregates all available health metrics
- [ ] Error handling provides clear and actionable error messages

### Security Success
- [ ] Service authentication protects all internal endpoints
- [ ] API key validation prevents unauthorized access
- [ ] Input validation prevents injection and manipulation attacks
- [ ] Error responses don't leak sensitive information

### Performance Success
- [ ] API responses meet performance criteria under normal load
- [ ] Caching improves performance for repeated requests
- [ ] Concurrent request handling works without conflicts
- [ ] Resource usage stays within defined limits

### Integration Success
- [ ] OAuth service integration handles authentication flows correctly
- [ ] WHOOP API client integration retrieves health data successfully
- [ ] Database integration stores and retrieves user connections properly
- [ ] Error propagation maintains system stability and user experience