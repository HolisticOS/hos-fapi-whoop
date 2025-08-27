# Sprint 1 - OAuth Service: Testing Plan

## Testing Strategy
Comprehensive testing approach for OAuth 2.0 implementation, focusing on security, functionality, and error handling to ensure reliable user authentication and token management.

## Test Scenarios

### 1. Authorization URL Generation Tests
**Objective**: Verify OAuth authorization URL generation and security measures

**Test Cases**:
- **TC1.1**: Valid authorization URL generation
  - Call generate_authorization_url() with valid user_id
  - Verify URL contains correct client_id, redirect_uri, scope parameters
  - Confirm state parameter format includes user_id and random component
  - Validate URL encoding and parameter structure

- **TC1.2**: State parameter security
  - Generate multiple authorization URLs for same user
  - Verify state parameters are unique and cryptographically secure
  - Confirm state contains user_id and can be validated later
  - Test state parameter length and character set compliance

- **TC1.3**: Scope parameter validation
  - Verify all required scopes included (read:profile, read:recovery, read:sleep, read:workouts, offline)
  - Confirm scope parameter properly formatted and encoded
  - Test scope string generation for different permission sets
  - Validate scope parameter matches WHOOP API requirements

### 2. Token Exchange Process Tests
**Objective**: Ensure secure and reliable authorization code to token exchange

**Test Cases**:
- **TC2.1**: Successful token exchange
  - Mock valid authorization code and state from WHOOP OAuth callback
  - Call exchange_code_for_tokens() with valid parameters
  - Verify access_token, refresh_token, and expires_in extracted correctly
  - Confirm token expiration datetime calculated accurately

- **TC2.2**: Invalid authorization code handling
  - Test with expired authorization code
  - Test with already-used authorization code
  - Test with malformed authorization code
  - Verify appropriate WhoopOAuthException raised with clear messages

- **TC2.3**: State parameter validation during exchange
  - Test with valid state parameter matching user_id
  - Test with invalid state parameter format
  - Test with state parameter for different user
  - Verify state validation prevents CSRF attacks

### 3. Database Token Storage Tests
**Objective**: Validate secure token storage and retrieval operations

**Test Cases**:
- **TC3.1**: Token storage operations
  - Test _store_user_tokens() with complete token data
  - Verify upsert operation handles new and existing users
  - Confirm all token fields stored correctly (access_token, refresh_token, expires_at)
  - Test database constraint validation and error handling

- **TC3.2**: Token retrieval operations
  - Test _get_user_tokens() with valid user_id
  - Test retrieval with non-existent user_id
  - Verify only active tokens returned (is_active = true)
  - Test token expiration checking during retrieval

- **TC3.3**: Token update operations
  - Test _update_user_tokens() with new token data
  - Verify update operations don't affect other users
  - Test concurrent update scenarios and database locking
  - Confirm updated_at timestamp updated correctly

### 4. Token Refresh Mechanism Tests
**Objective**: Ensure reliable refresh token functionality for expired access tokens

**Test Cases**:
- **TC4.1**: Successful token refresh
  - Mock valid refresh token for user
  - Call refresh_access_token() with expired access token
  - Verify new access token retrieved and stored
  - Confirm token expiration extended correctly

- **TC4.2**: Invalid refresh token handling
  - Test with expired refresh token
  - Test with invalid refresh token format
  - Test with refresh token for non-existent user
  - Verify graceful failure returns None without raising exceptions

- **TC4.3**: Refresh token HTTP errors
  - Mock WHOOP API 400 response for invalid refresh token
  - Mock network timeout during refresh request
  - Mock WHOOP API 429 rate limiting response
  - Verify appropriate error handling and logging

### 5. WHOOP User Profile Integration Tests
**Objective**: Validate user profile fetching and WHOOP user ID extraction

**Test Cases**:
- **TC5.1**: Profile API integration
  - Mock successful profile API response with user_id
  - Test _get_whoop_user_id() with valid access token
  - Verify WHOOP user ID extracted and returned correctly
  - Test profile API call with proper authentication headers

- **TC5.2**: Profile API error handling
  - Mock 401 unauthorized response from profile API
  - Mock network timeout during profile request
  - Mock malformed JSON response from profile API
  - Verify graceful error handling returns None with logging

- **TC5.3**: Profile integration during OAuth
  - Test complete OAuth flow with profile fetching
  - Verify WHOOP user ID stored correctly during token storage
  - Test OAuth completion with profile API failure
  - Confirm OAuth can complete without WHOOP user ID if needed

## Test Data Requirements

### Environment Configuration for Testing
```bash
# Test environment variables
WHOOP_CLIENT_ID=test_client_id_12345
WHOOP_CLIENT_SECRET=test_client_secret_12345
WHOOP_REDIRECT_URL=https://testapp.com/oauth/callback
WHOOP_API_BASE_URL=https://api.test.whoop.com/developer/v1
WHOOP_OAUTH_BASE_URL=https://api.test.whoop.com/oauth/oauth2
DATABASE_URL=postgresql://test:test@localhost:5432/whoop_test
```

### Mock API Responses
```json
// Successful token exchange response
{
  "access_token": "test_access_token_12345",
  "refresh_token": "test_refresh_token_12345",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read:profile read:recovery read:sleep read:workouts offline"
}

// WHOOP user profile response
{
  "user_id": 12345,
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User"
}

// Error responses for testing
{
  "error": "invalid_grant",
  "error_description": "The provided authorization grant is invalid"
}
```

### Test Database Setup
- **Clean test database** reset before each test suite
- **Test user records** with various OAuth states (new, existing, expired)
- **Sample tokens** for testing refresh and validation scenarios
- **Database transaction isolation** for concurrent testing

## Testing Steps

### Phase 1: Unit Testing (Individual Methods)
1. **OAuth service unit tests** (3 hours)
   - Test generate_authorization_url() with various parameters
   - Test state parameter generation and validation functions
   - Test token exchange parameter building and validation
   - Mock all external HTTP calls for isolated testing

2. **Database operations unit tests** (2 hours)
   - Test token storage methods with mock database
   - Test token retrieval with various query scenarios
   - Test update operations with concurrent access patterns
   - Verify database error handling and exception propagation

3. **Error handling unit tests** (1 hour)
   - Test custom exception creation and message formatting
   - Test error handling for network failures
   - Test validation error scenarios
   - Verify logging output for various error conditions

### Phase 2: Integration Testing (Component Interactions)
1. **OAuth flow integration tests** (3 hours)
   - Test complete OAuth flow with mock WHOOP API
   - Test authorization URL to token exchange workflow
   - Test profile fetching integration during OAuth completion
   - Verify database state after successful OAuth completion

2. **Token management integration tests** (2 hours)
   - Test token refresh with database integration
   - Test token expiration detection and refresh triggering
   - Test user connection status with various token states
   - Verify database consistency after token operations

3. **Error recovery integration tests** (1 hour)
   - Test OAuth flow recovery after network failures
   - Test database connection recovery during token operations
   - Test partial OAuth completion scenarios
   - Verify system state consistency after error recovery

### Phase 3: Security Testing (OAuth Vulnerabilities)
1. **CSRF protection testing** (2 hours)
   - Test state parameter validation prevents CSRF attacks
   - Test authorization request replay prevention
   - Test state parameter tampering detection
   - Verify secure random generation for state parameters

2. **Token security testing** (1 hour)
   - Test token storage security (encryption readiness)
   - Test access control for token retrieval operations
   - Test token scope validation and enforcement
   - Verify no token leakage in logs or error messages

## Automated Test Requirements

### Unit Tests (pytest)
```python
# Example OAuth service tests
@pytest.mark.asyncio
async def test_generate_authorization_url():
    """Test OAuth authorization URL generation"""
    
@pytest.mark.asyncio  
async def test_exchange_code_for_tokens_success():
    """Test successful authorization code exchange"""
    
@pytest.mark.asyncio
async def test_refresh_access_token():
    """Test refresh token functionality"""
    
def test_state_parameter_validation():
    """Test state parameter security and validation"""
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_complete_oauth_flow():
    """Test end-to-end OAuth flow with database"""
    
@pytest.mark.asyncio
async def test_token_refresh_with_database():
    """Test token refresh with real database operations"""
```

### Mock Configuration
```python
# Mock WHOOP API responses
@pytest.fixture
def mock_whoop_api():
    with aioresponses() as m:
        m.post('https://api.test.whoop.com/oauth/oauth2/token', payload={
            'access_token': 'test_token',
            'refresh_token': 'test_refresh',
            'expires_in': 3600
        })
        yield m
```

## Performance Criteria

### Response Time Requirements
- **Authorization URL generation**: < 100ms
- **Token exchange request**: < 5 seconds (including network)
- **Database token operations**: < 500ms
- **Token refresh operation**: < 5 seconds (including network)

### Security Requirements
- **State parameter entropy**: > 128 bits of randomness
- **Token storage**: Prepared for encryption (documented approach)
- **Error message sanitization**: No sensitive data in error responses
- **Request validation**: All OAuth parameters validated and sanitized

## Error Scenario Testing

### OAuth Protocol Errors
- **Invalid authorization code**: Expired or malformed codes
- **Invalid client credentials**: Wrong client_id or client_secret
- **Invalid redirect URI**: Mismatched or unauthorized redirect URLs
- **Invalid scope**: Unsupported or malformed scope parameters

### Network and API Errors
- **WHOOP API unavailable**: Service downtime during OAuth flow
- **Rate limiting**: 429 responses during token operations
- **Network timeouts**: Slow or interrupted network connections
- **Malformed API responses**: Invalid JSON or missing fields

### Database Errors
- **Database unavailable**: Connection failures during token storage
- **Constraint violations**: Duplicate key or foreign key errors
- **Transaction failures**: Concurrent access and locking issues
- **Data corruption**: Invalid token data or schema mismatches

## Success Criteria

### Functional Success
- [ ] Authorization URL generation works for all valid user scenarios
- [ ] Token exchange completes successfully with valid authorization codes
- [ ] Database operations store and retrieve tokens correctly
- [ ] Token refresh mechanism handles expired tokens automatically
- [ ] Profile integration fetches WHOOP user ID during OAuth completion

### Security Success
- [ ] State parameter validation prevents CSRF attacks
- [ ] No sensitive data leaked in logs or error messages
- [ ] Token storage prepared for production security requirements
- [ ] Input validation prevents injection and manipulation attacks

### Performance Success
- [ ] OAuth operations complete within performance criteria
- [ ] Database operations optimized and properly indexed
- [ ] Memory usage remains stable during OAuth flows
- [ ] Error handling doesn't impact system performance

### Quality Success
- [ ] Test coverage > 90% for OAuth service functionality
- [ ] All error scenarios tested and handled gracefully
- [ ] Integration tests verify complete OAuth workflow
- [ ] Security tests validate OAuth vulnerability protections