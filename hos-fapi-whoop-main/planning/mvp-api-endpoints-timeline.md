# MVP API Endpoints & Implementation Timeline

## 1. API Endpoint Specifications

### 1.1 Internal Whoop Service APIs (hos-fapi-whoop-main)

These endpoints are **internal only** - no external authentication required, designed for service-to-service communication.

#### Health Check Endpoints

```http
GET /health/ready
```
**Purpose:** Basic health check
**Response:**
```json
{
    "status": "ready",
    "service": "hos-fapi-whoop-main",
    "version": "1.0.0",
    "timestamp": "2025-08-27T10:00:00Z"
}
```

```http
GET /health/whoop-api
```
**Purpose:** Check Whoop API connectivity
**Response:**
```json
{
    "status": "healthy",
    "whoop_api": "available",
    "rate_limit_status": "ok"
}
```

#### User Connection Management

```http
GET /internal/user/{user_id}/status
```
**Purpose:** Check if user has active Whoop connection
**Parameters:**
- `user_id` (path): User identifier from Sahha system

**Response:**
```json
{
    "user_id": "sahha_user_123",
    "connected": true,
    "whoop_user_id": "12345",
    "connection_date": "2025-08-20T15:30:00Z",
    "token_expires_at": "2025-08-27T15:30:00Z",
    "scopes": ["read:recovery", "read:sleep", "read:workouts"]
}
```

```http
POST /internal/auth/connect/{user_id}
```
**Purpose:** Initiate OAuth connection for user
**Parameters:**
- `user_id` (path): User identifier

**Response:**
```json
{
    "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth?client_id=...",
    "state": "user123:randomstate",
    "expires_in": 600
}
```

```http
POST /internal/auth/callback
```
**Purpose:** Handle OAuth callback
**Request Body:**
```json
{
    "code": "auth_code_from_whoop",
    "state": "user123:randomstate",
    "user_id": "sahha_user_123"
}
```

**Response:**
```json
{
    "success": true,
    "user_id": "sahha_user_123",
    "whoop_user_id": "12345",
    "connected": true
}
```

#### Data Retrieval Endpoints

```http
GET /internal/data/recovery/{user_id}?date={date}
```
**Purpose:** Get recovery data for specific user and date
**Parameters:**
- `user_id` (path): User identifier
- `date` (query): "today", "yesterday", or "YYYY-MM-DD" format

**Response:**
```json
{
    "user_id": "sahha_user_123",
    "date": "2025-08-27",
    "recovery_score": 78.5,
    "hrv_rmssd": 42.3,
    "resting_heart_rate": 52,
    "skin_temp_celsius": 33.8,
    "respiratory_rate": 14.2,
    "recorded_at": "2025-08-27T08:00:00Z"
}
```

```http
GET /internal/data/sleep/{user_id}?date={date}
```
**Purpose:** Get sleep data for specific user and date

**Response:**
```json
{
    "user_id": "sahha_user_123",
    "date": "2025-08-27",
    "sleep_score": 82.0,
    "duration_seconds": 28800,
    "efficiency_percentage": 87.5,
    "start_time": "2025-08-26T23:30:00Z",
    "end_time": "2025-08-27T07:30:00Z",
    "sleep_stages": {
        "light_sleep_minutes": 210,
        "rem_sleep_minutes": 120,
        "deep_sleep_minutes": 90,
        "awake_minutes": 60
    }
}
```

```http
GET /internal/data/workouts/{user_id}?date={date}
```
**Purpose:** Get workout data for specific user and date

**Response:**
```json
{
    "user_id": "sahha_user_123",
    "date": "2025-08-27",
    "workouts": [
        {
            "workout_id": "workout_456",
            "sport_name": "Running",
            "start_time": "2025-08-27T06:00:00Z",
            "end_time": "2025-08-27T07:00:00Z",
            "duration_seconds": 3600,
            "strain": 16.8,
            "average_heart_rate": 162,
            "max_heart_rate": 189,
            "calories": 650
        }
    ]
}
```

### 1.2 Enhanced Entry Point APIs (hos-fapi-hm-sahha-main)

These endpoints extend the existing Sahha service with unified health data.

#### Unified Health Data

```http
GET /api/v1/unified-health/overview/{user_id}?period={period}&include_whoop={bool}
```
**Purpose:** Get unified health overview from all available sources
**Parameters:**
- `user_id` (path): User identifier
- `period` (query): "today", "yesterday", or "MM/DD/YYYY"
- `include_whoop` (query): boolean, default true

**Response:**
```json
{
    "user_id": "sahha_user_123",
    "period": "today",
    "data_sources": ["sahha", "whoop"],
    "enhanced_with_whoop": true,
    "merge_timestamp": "2025-08-27T10:00:00Z",
    
    // Original Sahha data structure preserved
    "readiness_score": 85,
    "activity_score": 92,
    "sleep_score": 78,
    "mental_wellbeing_score": 88,
    
    // Enhanced Whoop data
    "whoop_data": {
        "recovery": {
            "recovery_score": 78.5,
            "hrv_rmssd": 42.3,
            "resting_heart_rate": 52
        },
        "sleep": {
            "sleep_score": 82.0,
            "duration_seconds": 28800,
            "efficiency_percentage": 87.5
        },
        "workouts": [...]
    },
    
    // Summary metrics
    "whoop_summary": {
        "recovery_score": 78.5,
        "hrv_rmssd": 42.3,
        "resting_heart_rate": 52
    },
    
    // Performance metadata
    "processing_stats": {
        "total_time_ms": 1250,
        "sahha_time_ms": 800,
        "whoop_time_ms": 350,
        "merge_time_ms": 100
    }
}
```

#### Data Source Management

```http
GET /api/v1/unified-health/sources/{user_id}
```
**Purpose:** Check available data sources for user

**Response:**
```json
{
    "user_id": "sahha_user_123",
    "sahha": {
        "available": true,
        "status": "connected"
    },
    "whoop": {
        "available": true,
        "status": "connected",
        "connection_date": "2025-08-20T15:30:00Z"
    },
    "checked_at": "2025-08-27T10:00:00Z"
}
```

```http
POST /api/v1/unified-health/connect/whoop/{user_id}
```
**Purpose:** Initiate Whoop connection for user

**Response:**
```json
{
    "authorization_url": "https://api.prod.whoop.com/oauth/oauth2/auth?...",
    "instructions": "Redirect user to authorization_url to complete connection",
    "expires_in": 600
}
```

#### Service Health Monitoring

```http
GET /api/v1/unified-health/health/whoop
```
**Purpose:** Check Whoop integration health

**Response:**
```json
{
    "whoop_service": "available",
    "circuit_breaker_status": "closed",
    "integration_enabled": true,
    "last_successful_request": "2025-08-27T09:58:00Z"
}
```

```http
GET /api/v1/health/detailed
```
**Purpose:** Detailed health check including all integrations

**Response:**
```json
{
    "service": "hos-fapi-hm-sahha-main",
    "status": "healthy",
    "sahha_integration": {
        "status": "healthy"
    },
    "whoop_integration": {
        "enabled": true,
        "circuit_open": false,
        "failure_count": 0,
        "service_reachable": true
    },
    "timestamp": "2025-08-27T10:00:00Z"
}
```

## 2. Error Handling Specifications

### 2.1 Error Response Format

All APIs follow consistent error response format:

```json
{
    "error": "Description of the error",
    "type": "error_category",
    "timestamp": "2025-08-27T10:00:00Z",
    "request_id": "optional_request_id"
}
```

### 2.2 Error Categories

**Whoop Service Errors:**
- `whoop_service_error`: General Whoop service issues
- `whoop_auth_error`: Authentication/authorization issues
- `whoop_api_error`: Whoop API communication issues
- `user_not_connected`: User hasn't connected Whoop account
- `service_unavailable`: Whoop service is down (circuit breaker open)

**Entry Point Errors:**
- `sahha_service_error`: Critical Sahha service failure
- `data_merge_error`: Error merging data sources
- `timeout_error`: Request timeout
- `validation_error`: Invalid request parameters

### 2.3 HTTP Status Codes

| Status Code | Usage |
|-------------|-------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 401 | Authentication required |
| 404 | User not found or not connected |
| 429 | Rate limited |
| 500 | Internal server error |
| 503 | Service unavailable (circuit breaker open) |

## 3. Implementation Timeline

### Week 1: Foundation (Days 1-5)

#### Days 1-2: Infrastructure Setup
**Goals:**
- Set up hos-fapi-whoop-main project structure
- Configure Supabase database with MVP schema
- Set up development environment with Docker
- Create basic FastAPI application structure

**Deliverables:**
- ✅ Project directory structure
- ✅ Database schema deployed to dev environment
- ✅ Basic FastAPI app with health checks
- ✅ Environment configuration setup

**Success Criteria:**
- `GET /health/ready` returns 200
- Database connection successful
- Docker development environment working

#### Days 3-5: OAuth Implementation
**Goals:**
- Implement Whoop OAuth 2.0 flow
- Create user connection management
- Build token storage and refresh logic
- Test OAuth flow end-to-end

**Deliverables:**
- ✅ OAuth service implementation
- ✅ User connection status endpoint
- ✅ OAuth initiation and callback endpoints
- ✅ Token refresh functionality

**Success Criteria:**
- OAuth flow completes successfully in development
- Tokens stored and refreshed properly
- User connection status accurate

### Week 2: Core Data Integration (Days 6-10)

#### Days 6-8: Whoop API Client
**Goals:**
- Build Whoop API client with rate limiting
- Implement data fetching for recovery, sleep, workouts
- Add error handling and retry logic
- Create data transformation layer

**Deliverables:**
- ✅ WhoopAPIClient class with all methods
- ✅ Rate limiting implementation
- ✅ Data fetching endpoints
- ✅ Error handling and logging

**Success Criteria:**
- Can fetch recovery data from Whoop API
- Can fetch sleep and workout data
- Rate limiting prevents API violations
- Errors handled gracefully

#### Days 9-10: Internal APIs
**Goals:**
- Create internal API endpoints
- Implement data storage logic
- Add simple caching layer
- Build comprehensive error responses

**Deliverables:**
- ✅ All internal data endpoints
- ✅ Database storage implementation
- ✅ Basic caching functionality
- ✅ Consistent error responses

**Success Criteria:**
- All internal endpoints return valid responses
- Data persisted correctly in database
- Cache improves response times
- Error responses follow specification

### Week 3: Entry Point Enhancement (Days 11-15)

#### Days 11-13: Whoop Client Integration
**Goals:**
- Build HTTP client for Whoop service
- Implement sequential data fetching
- Add circuit breaker pattern
- Create unified data merging

**Deliverables:**
- ✅ WhoopIntegrationClient implementation
- ✅ Sequential processing logic
- ✅ Circuit breaker functionality
- ✅ Data merging service

**Success Criteria:**
- Sequential flow works (Sahha → Whoop → merge)
- Circuit breaker prevents cascading failures
- Data merging produces correct output
- Graceful degradation when Whoop unavailable

#### Days 14-15: Unified APIs
**Goals:**
- Implement unified health endpoints
- Add source status checking
- Create connection management endpoints
- Implement feature flags

**Deliverables:**
- ✅ Unified health overview endpoint
- ✅ Source status checking
- ✅ Connection management APIs
- ✅ Feature flag implementation

**Success Criteria:**
- Unified endpoints return combined data
- Feature flags control rollout
- Source status accurate for all users
- Connection flow works end-to-end

### Week 4: Testing & Production Readiness (Days 16-20)

#### Days 16-18: Integration & Performance Testing
**Goals:**
- End-to-end integration testing
- Performance testing with target 2-3 second response
- Error scenario testing
- Load testing with multiple users

**Deliverables:**
- ✅ Comprehensive test suite
- ✅ Performance benchmarks
- ✅ Error scenario validation
- ✅ Load testing results

**Success Criteria:**
- 95% of requests complete under 3 seconds
- System handles Whoop service failures gracefully
- No data corruption under load
- All error scenarios handled correctly

#### Days 19-20: Deployment & Documentation
**Goals:**
- Deploy to staging environment
- Create deployment documentation
- Set up monitoring and alerting
- Final MVP validation

**Deliverables:**
- ✅ Staging deployment working
- ✅ Production deployment guide
- ✅ Monitoring dashboards
- ✅ API documentation

**Success Criteria:**
- Both services deployed and communicating
- Monitoring shows healthy system status
- Documentation enables team maintenance
- MVP requirements fully satisfied

## 4. MVP Success Criteria

### 4.1 Functional Requirements

**Must Have:**
- ✅ Users can connect Whoop accounts via OAuth
- ✅ Sequential data fetching (Sahha first, then Whoop)
- ✅ System works without Whoop data (graceful degradation)
- ✅ Combined health data response includes both sources
- ✅ Response time under 3 seconds for 95% of requests

**Should Have:**
- ✅ Circuit breaker prevents cascading failures
- ✅ Feature flags enable controlled rollout
- ✅ Basic monitoring and health checks
- ✅ Clear error messages for troubleshooting

### 4.2 Technical Requirements

**Performance:**
- Response time: < 3 seconds (95th percentile)
- Availability: 99% uptime for entry point service
- Whoop service timeout: < 2 seconds
- Database queries: < 500ms average

**Reliability:**
- Zero impact on existing Sahha-only users
- Graceful degradation when Whoop service unavailable
- No data loss during service failures
- Consistent error handling across all endpoints

**Security:**
- OAuth tokens stored securely
- RLS policies protect user data
- API calls authenticated properly
- No sensitive data in logs

## 5. Post-MVP Enhancement Roadmap

### Phase 2 (Weeks 5-8): Advanced Features
- Real-time webhook integration
- Advanced data correlation
- Performance optimizations
- Enhanced error recovery

### Phase 3 (Weeks 9-12): Analytics & Intelligence
- Predictive insights from combined data
- Advanced health analytics
- Custom dashboards
- Mobile app enhancements

### Phase 4 (Weeks 13-16): Enterprise Features
- Multi-tenant architecture
- Advanced monitoring
- SLA management
- White-label solutions

## 6. Risk Mitigation Plan

### 6.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Whoop API changes | Medium | High | Comprehensive API wrapper with versioning |
| OAuth complexity | Low | Medium | Use proven OAuth libraries, extensive testing |
| Performance issues | Medium | Medium | Load testing, caching, timeouts |
| Database bottlenecks | Low | Medium | Proper indexing, query optimization |

### 6.2 Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| OAuth implementation delays | Medium | High | Start OAuth work immediately, use library |
| Integration complexity | Medium | Medium | Simple MVP approach, avoid over-engineering |
| Testing time overrun | High | Medium | Continuous testing throughout development |
| Deployment issues | Medium | High | Early staging deployment, automation |

### 6.3 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Low user adoption | Medium | Medium | Optional integration, existing users unaffected |
| Whoop partnership issues | Low | High | Direct API usage, no partnership required |
| Competitive pressure | High | Low | MVP approach enables quick market entry |

## 7. Monitoring & Success Metrics

### 7.1 System Health Metrics
- **Uptime:** 99%+ for entry point service
- **Response Time:** <3s for 95% of requests
- **Error Rate:** <1% for unified endpoints
- **Whoop Integration Success Rate:** >90%

### 7.2 Business Metrics
- **User Connections:** % of users who connect Whoop
- **Data Enhancement Rate:** % of requests enhanced with Whoop
- **Feature Adoption:** Usage of unified vs separate endpoints
- **User Satisfaction:** Feedback on combined data quality

### 7.3 Technical Metrics
- **Cache Hit Rate:** >80% for frequent queries
- **Database Performance:** <500ms average query time
- **Circuit Breaker Activation:** Frequency and recovery time
- **API Rate Limiting:** Staying within Whoop API limits

This comprehensive specification provides a clear roadmap for delivering the Whoop MVP integration within the 4-week timeline while maintaining high reliability and setting the foundation for future enhancements.