# Whoop MVP Sequential Architecture Plan
*Generated: 2025-08-27 - MVP Focus*

## Executive Summary

This document outlines a simplified MVP architecture for integrating Whoop API as a standalone microservice using **sequential calls**. The design prioritizes speed to market, reliability, and minimal complexity over advanced features. Target delivery: **4 weeks**.

## MVP Architecture Overview

### Core Principle: **Keep It Simple**
- Sequential processing (no parallel complexity)
- Graceful degradation (works without Whoop)
- Independent services with separate databases
- Basic error handling and logging
- MVP-focused feature set

### System Architecture

```
Flutter App
    ↓
hos-fapi-hm-sahha-main (Entry Point)
    ↓
[Sequential Processing]
    ↓
1. Get Sahha Data (existing)
    ↓
2. Check Whoop Connection
    ↓
3. Get Whoop Data (if connected)
    ↓ ↓ ↓
hos-fapi-whoop-main → Whoop Database
    ↓
4. Merge Data & Return
    ↓
Combined Response
```

## Service Design

### 1. hos-fapi-whoop-main (Standalone Microservice)

#### Purpose
Pure Whoop API integration service with minimal complexity.

#### MVP Endpoints (Internal Only)
```
GET  /internal/data/recovery/{user_id}    # Recovery scores & HRV
GET  /internal/data/sleep/{user_id}       # Sleep analysis
GET  /internal/data/workouts/{user_id}    # Workout strain data
POST /internal/auth/connect/{user_id}     # Initiate OAuth flow
GET  /internal/auth/status/{user_id}      # Check connection status
GET  /health/ready                        # Service health check
```

#### MVP Database (Separate from Sahha)
```sql
whoop_users           # User OAuth connections
whoop_recovery_data   # Recovery metrics
whoop_sleep_data      # Sleep analysis
whoop_workout_data    # Workout data
```

#### Key Features
- OAuth 2.0 token management
- Rate limiting for Whoop API (100/min, 10K/day)
- Basic error handling and retry logic
- Simple data storage and retrieval
- Health checks for service discovery

### 2. hos-fapi-hm-sahha-main (Enhanced Entry Point)

#### New Sequential Integration
```python
# Simplified MVP approach
async def get_health_data(user_id):
    # Step 1: Get Sahha data (existing - always works)
    sahha_data = await sahha_service.get_data(user_id)
    
    # Step 2: Try Whoop data (sequential, optional)
    whoop_data = None
    try:
        if await whoop_client.is_connected(user_id):
            whoop_data = await whoop_client.get_data(user_id)
    except Exception as e:
        logger.warning("Whoop unavailable", error=e)
    
    # Step 3: Simple merge
    return merge_data(sahha_data, whoop_data)
```

#### Enhanced MVP Endpoints
```
GET  /api/v1/health/{user_id}           # Enhanced with optional Whoop data
GET  /api/v1/health/sources/{user_id}   # Available data sources
POST /api/v1/whoop/connect/{user_id}    # Initiate Whoop connection
```

## MVP Implementation Timeline (4 Weeks)

### Week 1: Whoop Microservice Foundation
**Goals:**
- Set up hos-fapi-whoop-main project structure
- Implement basic FastAPI application
- Set up separate Whoop database
- Create OAuth 2.0 service structure

**Deliverables:**
- [ ] Project scaffolding complete
- [ ] Database schema deployed
- [ ] Basic service running on localhost
- [ ] OAuth flow skeleton implemented

### Week 2: Core Whoop Integration
**Goals:**
- Implement Whoop API client with rate limiting
- Complete OAuth token management
- Create internal API endpoints
- Add basic error handling

**Deliverables:**
- [ ] Working Whoop API integration
- [ ] Token refresh mechanism
- [ ] Internal endpoints functional
- [ ] Basic data retrieval working

### Week 3: Entry Point Enhancement
**Goals:**
- Create Whoop service client in entry point
- Implement sequential data retrieval
- Add basic data merging logic
- Enhance existing endpoints

**Deliverables:**
- [ ] Sequential integration working
- [ ] Enhanced health endpoints
- [ ] Basic error handling for service failures
- [ ] Simple data combination logic

### Week 4: Testing & Deployment
**Goals:**
- End-to-end testing
- Performance optimization
- Deploy to staging environment
- Bug fixes and stability improvements

**Deliverables:**
- [ ] MVP fully functional
- [ ] Performance within targets (<3s response)
- [ ] Deployed to staging
- [ ] Ready for user testing

## MVP Scope Definition

### ✅ IN SCOPE (MVP v1.0)
- Sequential data retrieval (Sahha → Whoop)
- Basic OAuth 2.0 flow for Whoop
- Simple data combination (JSON merging)
- Basic error handling and logging
- Service health checks
- Core Whoop metrics (recovery, sleep, workouts)
- Graceful degradation when Whoop unavailable

### ❌ OUT OF SCOPE (Future Versions)
- Real-time webhooks
- Advanced data correlation/analytics
- Complex caching strategies
- Parallel processing
- Advanced error recovery
- Data synchronization jobs
- Advanced monitoring/alerting
- User preference management
- Data export functionality

## Technical Specifications

### Performance Targets (MVP)
- **Response Time**: <3 seconds for combined data
- **Availability**: 99% uptime target
- **Error Rate**: <5% for Whoop integration
- **Timeout Handling**: 10 seconds per service call

### MVP Error Handling Strategy
```python
# Simple but effective error handling
try:
    whoop_data = await whoop_client.get_data(user_id, timeout=10)
except TimeoutError:
    logger.warning("Whoop service timeout")
    whoop_data = None  # Continue with Sahha only
except Exception as e:
    logger.error("Whoop service error", error=e)
    whoop_data = None  # Graceful degradation
```

### Security (MVP Level)
- Service-to-service API key authentication
- OAuth 2.0 for user Whoop connections
- Basic input validation
- HTTPS for all communications
- Token encryption in database

## Deployment Architecture

### Development Environment
```
localhost:8000 → hos-fapi-hm-sahha-main
localhost:8001 → hos-fapi-whoop-main
localhost:5432 → PostgreSQL (separate DBs)
```

### Production Environment (Render/Similar)
```
api.yourapp.com → hos-fapi-hm-sahha-main
whoop.yourapp.com → hos-fapi-whoop-main
supabase.com → Hosted databases
```

## Risk Mitigation

### Technical Risks
1. **Whoop Service Down**: Entry point works normally with Sahha only
2. **Rate Limiting**: Implemented with proper queuing and delays
3. **OAuth Complexity**: Using proven libraries and simple flow
4. **Database Issues**: Separate DBs prevent cross-contamination

### Business Risks
1. **Delayed Delivery**: Conservative 4-week timeline with buffer
2. **User Adoption**: MVP focuses on core functionality first
3. **Support Load**: Simple design reduces support complexity
4. **Scale Issues**: MVP targets low-moderate usage initially

## Success Criteria

### Technical Success
- [ ] Sequential data retrieval working reliably
- [ ] Whoop OAuth flow functional end-to-end
- [ ] Error handling prevents system crashes
- [ ] Response times under 3 seconds
- [ ] Service health checks operational

### Business Success
- [ ] Existing Sahha users unaffected
- [ ] New Whoop users can connect and see data
- [ ] Combined health insights visible in dashboard
- [ ] No critical bugs in production
- [ ] Foundation ready for future enhancements

## Post-MVP Roadmap (v2.0+)

### Phase 2: Performance & Features
- Parallel processing for faster responses
- Real-time webhooks for live data updates
- Advanced data correlation and insights
- User preference management

### Phase 3: Analytics & Intelligence
- Cross-source trend analysis
- Predictive health insights
- Custom health scoring algorithms
- Advanced dashboard visualizations

## Technology Stack

### hos-fapi-whoop-main
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL via Supabase
- **Auth**: OAuth 2.0 with python-jose
- **HTTP**: aiohttp for Whoop API calls
- **Logging**: structlog

### Integration Components
- **Service Communication**: Direct HTTP calls
- **Error Handling**: Try/catch with logging
- **Data Format**: JSON throughout
- **Authentication**: API key for service-to-service

## Development Resources

### Team Requirements
- **1-2 Backend Developers** (Python/FastAPI experience)
- **Access to Whoop Developer Account**
- **Existing hos-fapi-hm-sahha-main codebase**

### Infrastructure Requirements
- **Separate Database Instance** for Whoop data
- **Development Environment** with Docker
- **HTTPS Domain** for OAuth callbacks
- **Basic Monitoring** (logs, health checks)

---

## Implementation Notes

This MVP architecture prioritizes:

1. **Reliability over Performance**: Sequential calls are slower but more reliable
2. **Simplicity over Features**: Core functionality only, advanced features later
3. **Speed to Market**: 4-week delivery vs 8-week full solution
4. **Low Risk**: Existing system completely unaffected
5. **Future-Ready**: Foundation for advanced features in v2.0+

The design ensures that your current Sahha users continue to work perfectly while new users can benefit from enhanced Whoop data when available. This sequential approach provides a solid foundation that can be enhanced with parallel processing and advanced features in future iterations.