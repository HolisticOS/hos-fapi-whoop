# Sprint 1 - OAuth Service: Development Plan

## Feature Description
Implement WHOOP OAuth 2.0 authentication flow to enable users to securely connect their WHOOP accounts to the health data system. This includes authorization URL generation, callback handling, token exchange, refresh token management, and secure token storage with database integration.

## Technical Requirements
- **OAuth 2.0 Standard**: Full compliance with WHOOP OAuth 2.0 implementation
- **Security**: Secure state parameter generation and validation using secrets library
- **Token Management**: Access token and refresh token handling with expiration tracking
- **Database Integration**: Secure token storage in PostgreSQL with encryption considerations
- **Error Handling**: Comprehensive error handling for OAuth failures and network issues
- **Rate Limiting**: Respect WHOOP API rate limits during token operations

## Dependencies
- **Internal**: Foundation setup must be completed (database, FastAPI app)
- **External**: WHOOP Developer Account with OAuth credentials configured
- **Database**: whoop_users table with token storage schema
- **Libraries**: aiohttp, python-jose, secrets, datetime
- **Environment**: WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, WHOOP_REDIRECT_URL

## Steps to Implement

### Step 1: OAuth Service Core Implementation (6 hours)
1. **Create OAuth service class** (2 hours)
   - Create app/services/oauth_service.py with WhoopOAuthService class
   - Implement constructor with OAuth configuration from settings
   - Set up OAuth endpoints (auth_url, token_url) and client credentials
   - Configure required scopes (read:profile, read:recovery, read:sleep, read:workouts, offline)

2. **Authorization URL generation** (2 hours)
   - Implement generate_authorization_url() method with proper parameter building
   - Generate secure state parameter using user_id and cryptographic random string
   - Build authorization URL with client_id, response_type, redirect_uri, scope, state
   - Validate state parameter format and return both URL and state

3. **State management and validation** (2 hours)
   - Implement secure state parameter generation using secrets.token_urlsafe()
   - Create state validation logic to extract user_id and verify authenticity
   - Implement anti-CSRF protection through state parameter validation
   - Handle state parameter errors and invalid format scenarios

### Step 2: Token Exchange Implementation (8 hours)
1. **Authorization code exchange** (4 hours)
   - Implement exchange_code_for_tokens() method for OAuth callback handling
   - Create HTTP client request to WHOOP token endpoint with proper parameters
   - Handle successful token response and extract access_token, refresh_token, expires_in
   - Calculate token expiration datetime and prepare data for storage

2. **Token storage implementation** (2 hours)
   - Implement _store_user_tokens() method for secure database storage
   - Fetch WHOOP user ID using new access token for profile linking
   - Upsert user record in whoop_users table with conflict resolution
   - Handle database errors and provide meaningful error messages

3. **Token refresh mechanism** (2 hours)
   - Implement refresh_access_token() method for expired token renewal
   - Retrieve stored refresh token from database for user
   - Make refresh token request to WHOOP token endpoint
   - Update stored tokens with new access token and extended expiration

### Step 3: Database Integration (4 hours)
1. **Database schema updates** (2 hours)
   - Enhance whoop_users table schema with all OAuth fields
   - Add proper indexes on user_id, whoop_user_id, is_active columns
   - Implement token expiration tracking with token_expires_at field
   - Add database constraints for data integrity and foreign keys

2. **Database operations** (2 hours)
   - Implement _get_user_tokens() method for token retrieval
   - Implement _update_user_tokens() method for token updates
   - Add database connection error handling and retry logic
   - Create helper methods for user connection status queries

### Step 4: WHOOP User Profile Integration (4 hours)
1. **Profile API integration** (2 hours)
   - Implement _get_whoop_user_id() method using WHOOP API client
   - Create temporary API client instance for profile data retrieval
   - Handle API errors during profile fetching gracefully
   - Extract and validate WHOOP user ID from profile response

2. **User connection validation** (2 hours)
   - Implement connection status validation after successful OAuth
   - Verify token validity by making test API call to profile endpoint
   - Handle invalid or expired tokens during initial validation
   - Provide user feedback for successful and failed connections

### Step 5: Error Handling and Security (6 hours)
1. **OAuth exception handling** (3 hours)
   - Create WhoopOAuthException custom exception class
   - Implement comprehensive error handling for token exchange failures
   - Handle network timeouts, invalid responses, and API errors
   - Provide user-friendly error messages for common OAuth failures

2. **Security implementations** (2 hours)
   - Add input validation for authorization codes and state parameters
   - Implement secure token storage considerations (encryption planning)
   - Add logging for security events and OAuth flow completion
   - Validate redirect URI and prevent open redirect vulnerabilities

3. **Testing and validation** (1 hour)
   - Create unit tests for OAuth flow components
   - Test authorization URL generation and parameter encoding
   - Validate token exchange with mock responses
   - Test error scenarios and edge cases

## Expected Output
1. **Functional OAuth service**:
   - WhoopOAuthService class with all OAuth methods implemented
   - Authorization URL generation working with proper state management
   - Token exchange functional with database storage
   - Refresh token mechanism operational

2. **Database integration**:
   - whoop_users table with complete OAuth schema
   - Token storage and retrieval operations working
   - User connection status tracking functional
   - Database migrations for OAuth schema

3. **Security features**:
   - Secure state parameter generation and validation
   - Proper error handling for OAuth failures
   - Token expiration tracking and refresh logic
   - Input validation and security logging

## Acceptance Criteria
1. **Authorization URL generation** produces valid WHOOP OAuth URLs
2. **Token exchange** successfully processes valid authorization codes
3. **Database operations** store and retrieve tokens without errors
4. **Refresh mechanism** renews expired tokens automatically
5. **Error handling** provides clear messages for OAuth failures
6. **Security validation** prevents common OAuth vulnerabilities
7. **User connection status** accurately reflects OAuth state
8. **Integration tests** verify complete OAuth flow functionality

## Definition of Done
- [ ] WhoopOAuthService class implemented with all required methods
- [ ] Authorization URL generation working with secure state parameters
- [ ] Token exchange functionality complete with error handling
- [ ] Database schema updated with OAuth fields and indexes
- [ ] Token storage and retrieval operations functional
- [ ] Refresh token mechanism implemented and tested
- [ ] WHOOP user profile integration working for user ID fetching
- [ ] Custom OAuth exceptions implemented with proper error messages
- [ ] Security measures implemented (state validation, input validation)
- [ ] Unit tests cover OAuth service functionality
- [ ] Integration tests verify complete OAuth flow
- [ ] Documentation updated with OAuth setup instructions
- [ ] Environment variables documented and validated
- [ ] Code follows security best practices for OAuth implementation

## Quality Gates
- **Security Review**: OAuth implementation reviewed for security vulnerabilities
- **Token Security**: Token storage approach reviewed and approved
- **Error Handling**: All OAuth error scenarios properly handled and tested
- **Integration Testing**: Complete OAuth flow tested end-to-end
- **Performance**: OAuth operations complete within 10 seconds
- **Documentation**: Setup instructions verified with clean environment