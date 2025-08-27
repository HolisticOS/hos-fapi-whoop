# Sprint 1 - Internal APIs: Development Plan

## Feature Description
Implement internal FastAPI endpoints for OAuth management, user connection status, and health data retrieval. These APIs provide service-to-service communication interfaces for the main health system, enabling user authentication flows and data access without exposing external authentication requirements.

## Technical Requirements
- **FastAPI Framework**: RESTful API design with automatic documentation
- **Internal Authentication**: Service-to-service API key authentication
- **Data Serialization**: Pydantic models for request/response validation
- **Error Handling**: Consistent error responses with proper HTTP status codes
- **Logging**: Structured logging for API access and error tracking
- **Async Processing**: Full async/await support for database and API operations

## Dependencies
- **Internal**: Foundation setup, OAuth service, WHOOP API client
- **External**: Database connectivity for user token storage
- **Services**: WhoopOAuthService, WhoopAPIClient integration
- **Authentication**: Service API key for internal authentication
- **Configuration**: API routing and middleware setup

## Steps to Implement

### Step 1: Internal API Structure and Authentication (6 hours)
1. **API router setup** (2 hours)
   - Create app/api/internal.py with FastAPI router configuration
   - Set up internal API prefix and route organization
   - Configure API documentation metadata and descriptions
   - Implement API versioning structure for future growth

2. **Service authentication middleware** (2 hours)
   - Create authentication dependency for internal API access
   - Implement API key validation from headers or query parameters
   - Add service-to-service authentication with configurable keys
   - Create authentication exception handling and error responses

3. **Request/response models** (2 hours)
   - Create Pydantic models for OAuth and data API requests/responses
   - Implement UserConnectionStatus, OAuthInitiation, and data response models
   - Add request validation and response serialization models
   - Create error response models for consistent error formatting

### Step 2: OAuth Management Endpoints (8 hours)
1. **OAuth initiation endpoint** (3 hours)
   - Implement POST /internal/oauth/initiate endpoint for starting OAuth flows
   - Accept user_id parameter and generate WHOOP authorization URL
   - Return authorization URL and state parameter for client redirection
   - Add error handling for invalid user IDs and OAuth setup failures

2. **OAuth callback handling endpoint** (3 hours)
   - Implement POST /internal/oauth/callback endpoint for OAuth completion
   - Accept authorization code, state, and user_id from OAuth callback
   - Process token exchange and store user tokens in database
   - Return success/failure status with connection information

3. **User connection status endpoint** (2 hours)
   - Implement GET /internal/oauth/status/{user_id} for connection checking
   - Return user's WHOOP connection status, token expiry, and user info
   - Handle non-existent users and expired connections gracefully
   - Provide connection metadata for client decision-making

### Step 3: User Disconnection and Management (4 hours)
1. **User disconnection endpoint** (2 hours)
   - Implement DELETE /internal/oauth/disconnect/{user_id} for removing connections
   - Deactivate stored tokens and mark user as disconnected
   - Handle already disconnected users and invalid user IDs
   - Return disconnection status and cleanup confirmation

2. **Connection validation endpoint** (2 hours)
   - Implement POST /internal/oauth/validate/{user_id} for token testing
   - Test user's stored tokens by making WHOOP profile API call
   - Refresh expired tokens automatically during validation
   - Return detailed validation results and token status

### Step 4: Health Data Retrieval Endpoints (10 hours)
1. **User profile data endpoint** (2 hours)
   - Implement GET /internal/data/profile/{user_id} for WHOOP profile information
   - Retrieve user's WHOOP profile using stored access tokens
   - Handle token refresh if tokens are expired during request
   - Return formatted profile data with error handling

2. **Recovery data endpoint** (3 hours)
   - Implement GET /internal/data/recovery/{user_id} with date parameters
   - Retrieve recovery data for specified date or date range
   - Handle current cycle retrieval and recovery score extraction
   - Format recovery data for consistent API response structure

3. **Sleep data endpoint** (3 hours)
   - Implement GET /internal/data/sleep/{user_id} with date range support
   - Retrieve sleep collection data using WHOOP API client
   - Handle sleep data pagination and multi-day aggregation
   - Format sleep data with timing, scores, and efficiency metrics

4. **Workout data endpoint** (2 hours)
   - Implement GET /internal/data/workouts/{user_id} with date filtering
   - Retrieve workout collection data for specified time periods
   - Process workout data aggregation and activity classification
   - Return formatted workout data with strain, heart rate, and activity details

### Step 5: Combined Health Data Endpoint (6 hours)
1. **Comprehensive health data endpoint** (4 hours)
   - Implement GET /internal/data/health/{user_id} for all health metrics
   - Combine profile, recovery, sleep, and workout data in single response
   - Handle partial data availability and API failures gracefully
   - Optimize API calls to minimize WHOOP API requests

2. **Data caching and optimization** (2 hours)
   - Implement simple in-memory caching for frequently requested data
   - Add cache invalidation based on data age and request patterns
   - Optimize database queries for user token retrieval
   - Add request deduplication for concurrent identical requests

### Step 6: Error Handling and Validation (4 hours)
1. **Comprehensive error handling** (2 hours)
   - Implement custom exception handlers for OAuth and API errors
   - Create consistent error response format across all endpoints
   - Add proper HTTP status codes for different error scenarios
   - Implement error logging with request context and user information

2. **Request validation and sanitization** (2 hours)
   - Add input validation for user IDs, dates, and query parameters
   - Implement request sanitization to prevent injection attacks
   - Add parameter validation for date ranges and data filters
   - Create validation error responses with detailed field information

## Expected Output
1. **OAuth management APIs**:
   - OAuth initiation endpoint returning authorization URLs
   - OAuth callback processing with token storage
   - User connection status checking and validation
   - User disconnection and token cleanup functionality

2. **Health data retrieval APIs**:
   - User profile data with WHOOP account information
   - Recovery data with scores, HRV, and physiological metrics
   - Sleep data with timing, efficiency, and quality scores
   - Workout data with activity details, strain, and performance metrics
   - Combined health data endpoint for comprehensive information

3. **Production-ready features**:
   - Service authentication with API keys
   - Comprehensive error handling and logging
   - Request validation and response formatting
   - Performance optimization with caching

## Acceptance Criteria
1. **OAuth endpoints** handle complete authentication flow successfully
2. **User connection status** accurately reflects OAuth state and token validity
3. **Health data endpoints** return properly formatted data from WHOOP API
4. **Combined endpoint** aggregates all health data with error handling
5. **Authentication** protects all endpoints with service API keys
6. **Error responses** provide clear messages and appropriate HTTP status codes
7. **API documentation** automatically generated with request/response examples
8. **Logging** captures API access, errors, and performance metrics

## Definition of Done
- [ ] All internal API endpoints implemented with proper routing
- [ ] Service authentication middleware protecting all internal endpoints
- [ ] OAuth initiation endpoint generating valid authorization URLs
- [ ] OAuth callback endpoint processing tokens and storing user connections
- [ ] User connection status endpoint providing accurate connection information
- [ ] User disconnection endpoint properly cleaning up stored tokens
- [ ] Profile data endpoint retrieving WHOOP user information
- [ ] Recovery data endpoint providing physiological metrics
- [ ] Sleep data endpoint handling date ranges and pagination
- [ ] Workout data endpoint processing activity and performance data
- [ ] Combined health data endpoint aggregating all available metrics
- [ ] Comprehensive error handling with consistent response formats
- [ ] Request validation and parameter sanitization implemented
- [ ] API documentation generated with examples and schemas
- [ ] Integration tests verify end-to-end API functionality
- [ ] Performance optimization with caching and request deduplication

## Quality Gates
- **API Design**: RESTful design principles followed consistently
- **Authentication**: Service authentication prevents unauthorized access
- **Error Handling**: All error scenarios handled gracefully with proper codes
- **Performance**: API responses within 3 seconds for typical requests
- **Documentation**: Complete API documentation with examples
- **Security**: Input validation prevents injection and manipulation attacks