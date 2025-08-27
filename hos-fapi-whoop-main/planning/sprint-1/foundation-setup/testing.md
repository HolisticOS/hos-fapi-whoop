# Sprint 1 - Foundation Setup: Testing Plan

## Testing Strategy
Comprehensive testing approach to validate the foundational infrastructure, ensuring reliability and maintainability of the microservice foundation before proceeding with complex integrations.

## Test Scenarios

### 1. Application Startup and Configuration Tests
**Objective**: Verify application starts correctly and configuration loads properly

**Test Cases**:
- **TC1.1**: Application starts without errors
  - Start application using `python -m app.main`
  - Verify no exception thrown during startup
  - Confirm application listens on configured port (8001)

- **TC1.2**: Environment configuration loading
  - Test with valid .env file
  - Test with missing optional environment variables
  - Test with invalid environment variable values
  - Verify default values applied correctly

- **TC1.3**: CORS and middleware configuration
  - Verify CORS headers present in response
  - Test middleware chain execution order
  - Confirm request/response logging functionality

### 2. Database Connectivity and Schema Tests
**Objective**: Ensure database operations function correctly

**Test Cases**:
- **TC2.1**: Database connection establishment
  - Test successful connection with valid DATABASE_URL
  - Test connection failure handling with invalid URL
  - Verify connection pooling configuration

- **TC2.2**: Schema creation and validation
  - Execute migration scripts successfully
  - Verify all tables created with correct structure
  - Confirm indexes and constraints applied

- **TC2.3**: Basic CRUD operations
  - Test INSERT operations on all tables
  - Test SELECT queries with various conditions
  - Verify UUID generation and foreign key constraints
  - Test connection cleanup and resource management

### 3. Health Check Endpoint Tests
**Objective**: Validate service health monitoring capabilities

**Test Cases**:
- **TC3.1**: Readiness endpoint functionality
  - GET /health/ready returns 200 with valid JSON
  - Response includes database connectivity status
  - Endpoint responds within 2 seconds

- **TC3.2**: Liveness endpoint functionality  
  - GET /health/live returns 200 with basic status
  - Endpoint responds even during high load
  - Response format matches expected schema

- **TC3.3**: Health check error scenarios
  - Database disconnected scenario
  - High load/timeout scenarios
  - Verify appropriate error codes and messages

### 4. API Structure and Authentication Tests
**Objective**: Verify basic API structure and security measures

**Test Cases**:
- **TC4.1**: API router configuration
  - Verify routers mounted at correct prefixes
  - Test route resolution and path parameter handling
  - Confirm API documentation generation

- **TC4.2**: API key authentication
  - Test requests with valid API key header
  - Test requests with invalid/missing API key
  - Verify 401 status codes for unauthorized requests
  - Test API key validation logic

- **TC4.3**: Error handling and responses
  - Test 404 responses for non-existent endpoints
  - Verify error response format consistency
  - Test exception handling and error logging

### 5. Logging and Monitoring Tests
**Objective**: Ensure proper logging and debugging capabilities

**Test Cases**:
- **TC5.1**: Structured logging output
  - Verify JSON-formatted log messages
  - Test log levels and filtering
  - Confirm timestamp and metadata inclusion

- **TC5.2**: Request/response logging
  - Test HTTP request logging with proper details
  - Verify response time measurement
  - Test error scenario logging

- **TC5.3**: Application event logging
  - Test startup/shutdown event logging
  - Verify database operation logging
  - Test error and warning message formatting

## Test Data Requirements

### Environment Configuration
```bash
# Test .env file
DATABASE_URL=postgresql://test:test@localhost:5432/whoop_test_db
WHOOP_CLIENT_ID=test_client_id
WHOOP_CLIENT_SECRET=test_client_secret
WHOOP_REDIRECT_URL=https://test.com/callback
SERVICE_API_KEY=test_service_api_key_12345
PORT=8001
ENVIRONMENT=testing
```

### Test Database Setup
- **Clean test database** for each test run
- **Sample data fixtures** for CRUD operation tests
- **Migration scripts** executed in test environment
- **Test user tokens** for authentication testing

### Mock Services
- **Mock WHOOP API responses** for future integration tests
- **Test HTTP client** with configurable responses
- **Database transaction isolation** for test data cleanup

## Testing Steps

### Phase 1: Unit Testing (Individual Components)
1. **Configuration testing** (1 hour)
   - Test settings.py with various environment configurations
   - Verify validation and default value handling
   - Test configuration error scenarios

2. **Database model testing** (2 hours)
   - Test table creation and schema validation
   - Verify database connection management
   - Test async database operations

3. **API endpoint testing** (2 hours)
   - Test health check endpoints in isolation
   - Verify authentication dependency functionality
   - Test error handling and response formatting

### Phase 2: Integration Testing (Component Interactions)
1. **Application integration testing** (2 hours)
   - Test full application startup with database
   - Verify middleware chain and request processing
   - Test configuration integration across components

2. **Database integration testing** (1 hour)
   - Test database operations within application context
   - Verify transaction handling and connection pooling
   - Test error recovery and connection retry logic

3. **API integration testing** (1 hour)
   - Test complete HTTP request/response cycle
   - Verify authentication integration with endpoints
   - Test error propagation and response formatting

### Phase 3: End-to-End Testing (Full System)
1. **Development environment testing** (2 hours)
   - Test complete Docker development setup
   - Verify database migration execution
   - Test application restart and recovery

2. **Manual testing scenarios** (1 hour)
   - Test API endpoints using curl/Postman
   - Verify log output and monitoring capabilities
   - Test various error and edge case scenarios

## Automated Test Requirements

### Unit Tests (pytest)
```python
# Example test structure
def test_application_startup():
    """Test FastAPI application starts successfully"""
    
def test_database_connection():
    """Test database connectivity and basic operations"""
    
def test_health_endpoints():
    """Test health check endpoint responses"""
    
def test_authentication_dependency():
    """Test API key authentication functionality"""
```

### Integration Tests
```python
# Example integration test
@pytest.mark.asyncio
async def test_full_health_check_with_db():
    """Test health endpoints with real database connection"""
    
@pytest.mark.asyncio  
async def test_application_lifecycle():
    """Test startup and shutdown event handling"""
```

## Performance Criteria

### Response Time Requirements
- **Health check endpoints**: < 500ms response time
- **Application startup**: < 10 seconds to ready state
- **Database operations**: < 200ms for simple queries
- **Configuration loading**: < 1 second

### Resource Usage Limits
- **Memory usage**: < 100MB for basic application
- **CPU usage**: < 10% during idle state
- **Database connections**: < 5 concurrent connections for tests
- **Network timeouts**: 30 seconds maximum for external calls

## Security Testing

### Authentication Testing
- **Valid API key acceptance**
- **Invalid API key rejection**
- **Missing API key handling**
- **API key header validation**

### Data Security Testing  
- **Environment variable security** (no secrets in logs)
- **Database connection string protection**
- **Error message sanitization** (no sensitive data exposure)
- **Request/response data validation**

## Error Scenario Testing

### Database Error Scenarios
- **Database unavailable during startup**
- **Connection timeout during operation**
- **Invalid SQL queries or schema issues**
- **Database disk space exhaustion**

### Configuration Error Scenarios
- **Missing required environment variables**
- **Invalid configuration values**
- **File permission issues**
- **Network connectivity problems**

### Application Error Scenarios
- **Out of memory conditions**
- **High concurrent request load**
- **Malformed HTTP requests**
- **Unexpected exception handling**

## Success Criteria

### Automated Testing Success
- [ ] All unit tests pass with 100% success rate
- [ ] Integration tests complete without errors
- [ ] Test coverage > 80% for core functionality
- [ ] All tests execute in < 30 seconds total

### Manual Testing Success
- [ ] Application starts cleanly in Docker environment
- [ ] Health endpoints respond correctly to manual requests
- [ ] Database migration executes successfully
- [ ] Logging output formatted correctly and readable

### Performance Testing Success
- [ ] Response times meet performance criteria
- [ ] Memory usage stays within limits
- [ ] Application handles graceful shutdown
- [ ] No resource leaks detected during testing

### Quality Assurance Success
- [ ] Error scenarios handled gracefully
- [ ] Security requirements validated
- [ ] Documentation accuracy verified
- [ ] Code quality standards maintained