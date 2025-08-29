# WHOOP API v2 Comprehensive Migration Research

## Executive Summary

**CRITICAL DEADLINE: WHOOP API v1 will be completely removed on October 1, 2025**

This document provides comprehensive research on the WHOOP API v2 migration requirements, including all breaking changes, new features, endpoint mappings, and implementation guidelines needed to successfully migrate from v1 to v2.

**Key Migration Requirements:**
- Update all API endpoints from `/v1/` to `/v2/`
- Handle UUID identifiers instead of integer IDs for Sleep and Workout resources
- Update webhook processing for v2 webhook model
- Implement new authentication scope constants
- Update data structure handling for improved consistency

**Migration Timeline:** Must be completed by October 1, 2025

---

## 1. WHOOP API v2 Overview

### 1.1 Official Documentation
- **Main API Docs:** https://developer.whoop.com/api/
- **Migration Guide:** https://developer.whoop.com/docs/developing/v1-v2-migration/
- **API Changelog:** https://developer.whoop.com/docs/api-changelog/
- **OAuth 2.0 Guide:** https://developer.whoop.com/docs/developing/oauth/

### 1.2 v2 API Improvements
- **Enhanced Data Models:** More consistent resource paths and data modeling
- **UUID Identifiers:** Transition from integer IDs to UUIDs for key resources
- **Improved Webhook Reliability:** v2 webhook model with better identifier handling
- **Standardized Timezone Handling:** All timestamps in UTC
- **Better Error Handling:** More precise Optional field handling
- **Future-Proof Architecture:** Support for upcoming features

### 1.3 Migration Criticality
- **Mandatory Migration:** All v1 APIs and webhooks will be removed October 1, 2025
- **No Grace Period:** v1 endpoints will be completely unavailable after deadline
- **Complete System Impact:** All WHOOP integrations must be updated

---

## 2. Complete v2 Endpoint Catalog

### 2.1 Base URL Changes
- **v1 Base URL:** `https://api.prod.whoop.com/developer/v1/`
- **v2 Base URL:** `https://api.prod.whoop.com/developer/v2/`

### 2.2 Authentication Endpoints (Unchanged)
```
OAuth Authorization: https://api.prod.whoop.com/oauth/oauth2/auth
Token Exchange: https://api.prod.whoop.com/oauth/oauth2/token
Token Revocation: https://api.prod.whoop.com/oauth/oauth2/revoke
```

### 2.3 v2 API Endpoints

#### User Profile Endpoints
```
GET /v2/user/profile/basic
- Basic profile information (name, email)
- Requires: read:profile scope

GET /v2/user/measurement/body
- Body measurements (height, weight, max heart rate)
- Requires: read:profile scope
```

#### Cycle Endpoints
```
GET /v2/cycle
- All physiological cycles for authenticated user
- Supports pagination with limit and nextToken
- Returns: cycle data with start/end times, timezone_offset, score data

GET /v2/cycle/{cycleId}
- Specific cycle by ID
- Returns: detailed cycle information

GET /v2/cycle/{cycleId}/sleep
- Sleep data associated with specific cycle (NEW in v2)
- Returns: sleep information linked to cycle
```

#### Recovery Endpoints
```
GET /v2/recovery
- All recovery scores for authenticated user
- Supports pagination
- Returns: recovery data with HRV, RHR, respiratory rate

GET /v2/recovery/{recoveryId}
- Specific recovery by ID
```

#### Sleep Endpoints
```
GET /v2/activity/sleep
- All sleep sessions for authenticated user
- Supports date range filtering and pagination
- Returns: sleep data with UUID identifiers (BREAKING CHANGE)

GET /v2/activity/sleep/{sleepId}
- Specific sleep session by UUID (BREAKING CHANGE)
- sleepId is now UUID format: "ecfc6a15-4661-442f-a9a4-f160dd7afae8"
```

#### Workout Endpoints
```
GET /v2/activity/workout
- All workouts for authenticated user
- Supports date range filtering and pagination
- Returns: workout data with UUID identifiers (BREAKING CHANGE)

GET /v2/activity/workout/{workoutId}
- Specific workout by UUID (BREAKING CHANGE)
- workoutId is now UUID format: "7bfc6a15-5521-612f-b9a4-e274dd7afae9"
```

---

## 3. v1 to v2 Migration Breaking Changes

### 3.1 Critical ID Format Changes

#### Sleep IDs
**v1 Format:**
```json
{
  "id": 12345,
  "start": "2024-01-15T23:30:00.000Z",
  "end": "2024-01-16T07:15:00.000Z"
}
```

**v2 Format:**
```json
{
  "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
  "activityV1Id": 12345,
  "start": "2024-01-15T23:30:00.000Z",
  "end": "2024-01-16T07:15:00.000Z"
}
```

#### Workout IDs
**v1 Format:**
```json
{
  "id": 56789,
  "sport_id": 1,
  "strain": 16.8
}
```

**v2 Format:**
```json
{
  "id": "7bfc6a15-5521-612f-b9a4-e274dd7afae9",
  "activityV1Id": 56789,
  "sport_id": 1,
  "strain": 16.8
}
```

### 3.2 Code Migration Examples

#### Database Schema Updates
```sql
-- v1 Schema
CREATE TABLE whoop_sleep (
    id SERIAL PRIMARY KEY,
    whoop_sleep_id INTEGER UNIQUE,  -- v1 integer ID
    user_id UUID,
    sleep_data JSONB
);

-- v2 Schema (REQUIRED CHANGES)
CREATE TABLE whoop_sleep (
    id SERIAL PRIMARY KEY,
    whoop_sleep_id UUID UNIQUE,     -- v2 UUID ID
    whoop_sleep_v1_id INTEGER,      -- Keep v1 ID for migration
    user_id UUID,
    sleep_data JSONB
);
```

#### API Client Updates
```python
# v1 Implementation
class WhoopV1Client:
    def get_sleep_by_id(self, sleep_id: int):
        return self.request(f"/v1/activity/sleep/{sleep_id}")

# v2 Implementation (REQUIRED CHANGES)
class WhoopV2Client:
    def get_sleep_by_id(self, sleep_id: str):  # UUID as string
        return self.request(f"/v2/activity/sleep/{sleep_id}")
    
    def migrate_from_v1_id(self, v1_sleep_id: int):
        # Search by activityV1Id if needed for migration
        sleep_data = self.request("/v2/activity/sleep")
        for sleep in sleep_data.get('data', []):
            if sleep.get('activityV1Id') == v1_sleep_id:
                return sleep
        return None
```

### 3.3 Webhook Migration Requirements

#### v1 Webhook Model
```json
{
  "user_id": 10129,
  "id": 10235,
  "type": "recovery.updated",
  "trace_id": "d3709ee7-104e-4f70-a928-2932964b017b"
}
```

#### v2 Webhook Model (REQUIRED CHANGES)
```json
{
  "user_id": 10129,
  "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",  // UUID format
  "type": "recovery.updated",
  "trace_id": "d3709ee7-104e-4f70-a928-2932964b017b"
}
```

**Key Webhook Changes:**
- v2 recovery webhooks use sleep UUID instead of cycle ID
- All resource IDs in webhooks are now UUIDs where applicable
- Webhook version must match API version being called

---

## 4. v2 Data Models & Schemas

### 4.1 Enhanced Data Structures

#### Cycle Data Structure (v2)
```json
{
  "id": "cycle-uuid-string",
  "user_id": 10129,
  "created_at": "2024-01-15T00:00:00.000Z",
  "updated_at": "2024-01-16T08:00:00.000Z",
  "start": "2024-01-15T00:00:00.000Z",
  "end": "2024-01-16T00:00:00.000Z",
  "timezone_offset": "-05:00",
  "score_state": "SCORED",
  "score": {
    "strain": 15.2,
    "kilojoule": 1847.5,
    "average_heart_rate": 156,
    "max_heart_rate": 184
  }
}
```

#### Sleep Data Structure (v2)
```json
{
  "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
  "activityV1Id": 12345,
  "user_id": 10129,
  "created_at": "2024-01-16T08:00:00.000Z",
  "updated_at": "2024-01-16T08:00:00.000Z",
  "start": "2024-01-15T23:30:00.000Z",
  "end": "2024-01-16T07:15:00.000Z",
  "timezone_offset": "-05:00",
  "nap": false,
  "score_state": "SCORED",
  "score": {
    "stage_summary": 85,
    "sleep_needed": 28800,
    "respiratory_rate": 13.8,
    "sleep_consistency": 78,
    "sleep_efficiency": 87
  }
}
```

#### Workout Data Structure (v2)
```json
{
  "id": "7bfc6a15-5521-612f-b9a4-e274dd7afae9",
  "activityV1Id": 56789,
  "user_id": 10129,
  "created_at": "2024-01-15T19:30:00.000Z",
  "updated_at": "2024-01-15T19:30:00.000Z",
  "start": "2024-01-15T18:00:00.000Z",
  "end": "2024-01-15T19:30:00.000Z",
  "timezone_offset": "-05:00",
  "sport_id": 1,
  "score_state": "SCORED",
  "score": {
    "strain": 16.8,
    "average_heart_rate": 162,
    "max_heart_rate": 189,
    "kilojoule": 2156.7,
    "percent_recorded": 98.5,
    "distance_meter": 8047.2,
    "altitude_gain_meter": 145.3,
    "altitude_change_meter": -23.1,
    "zone_duration": {
      "zone_zero_milli": 0,
      "zone_one_milli": 480000,
      "zone_two_milli": 720000,
      "zone_three_milli": 1200000,
      "zone_four_milli": 600000,
      "zone_five_milli": 300000
    }
  }
}
```

#### Recovery Data Structure (v2)
```json
{
  "cycle_id": "cycle-uuid-string",
  "sleep_id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
  "user_id": 10129,
  "created_at": "2024-01-16T08:00:00.000Z",
  "updated_at": "2024-01-16T08:00:00.000Z",
  "score_state": "SCORED",
  "score": {
    "user_calibrating": false,
    "recovery_score": 67,
    "resting_heart_rate": 52,
    "hrv_rmssd_milli": 42.5,
    "spo2_percentage": 98.2,
    "skin_temp_celsius": 33.8
  }
}
```

### 4.2 New v2 Fields
- **activityV1Id:** Backward compatibility field containing original v1 integer ID
- **Enhanced timestamps:** All times in UTC with explicit timezone_offset
- **Improved optional handling:** Better null-safety and field presence validation
- **Consistent score_state:** Standardized scoring state across all resources

---

## 5. Authentication & Technical Specifications

### 5.1 OAuth 2.0 (No Changes)
The OAuth 2.0 implementation remains the same between v1 and v2:
- **Authorization URL:** `https://api.prod.whoop.com/oauth/oauth2/auth`
- **Token URL:** `https://api.prod.whoop.com/oauth/oauth2/token`
- **Scopes:** No changes to available scopes

### 5.2 Rate Limiting (No Changes)
Rate limits remain the same for v2:
- **100 requests per minute** (60-second window)
- **10,000 requests per 24-hour period**
- Same rate limit headers and 429 error handling

### 5.3 Security Constants
v2 introduces security scopes defined as constants for better consistency:

```python
# v2 Scope Constants
class WhoopScopes:
    OFFLINE = "offline"
    READ_PROFILE = "read:profile"
    READ_CYCLES = "read:cycles"
    READ_RECOVERY = "read:recovery"
    READ_SLEEP = "read:sleep"
    READ_WORKOUTS = "read:workouts"
```

---

## 6. Migration Implementation Guide

### 6.1 Migration Checklist

#### Phase 1: Preparation (Week 1)
- [ ] Review all current v1 API usage in codebase
- [ ] Identify all Sleep and Workout ID storage/processing
- [ ] Plan database schema migration for UUID support
- [ ] Set up v2 API testing environment
- [ ] Update development environment with v2 endpoints

#### Phase 2: Code Updates (Weeks 2-3)
- [ ] Update all API endpoints from `/v1/` to `/v2/`
- [ ] Modify Sleep ID handling to support UUIDs
- [ ] Modify Workout ID handling to support UUIDs
- [ ] Update database schemas to store UUID identifiers
- [ ] Add activityV1Id fields for backward compatibility
- [ ] Update data parsing for new v2 response structures

#### Phase 3: Webhook Migration (Week 4)
- [ ] Set up separate v2 webhook endpoint for testing
- [ ] Update webhook signature validation (no changes needed)
- [ ] Modify webhook processing for UUID identifiers
- [ ] Test v2 webhook events thoroughly
- [ ] Switch production webhook to v2 model

#### Phase 4: Testing & Validation (Week 5)
- [ ] Comprehensive testing of all v2 endpoints
- [ ] Validate UUID handling in all code paths
- [ ] Test webhook processing with v2 events
- [ ] Verify backward compatibility with stored v1 IDs
- [ ] Performance testing with new data structures

#### Phase 5: Production Deployment (Week 6)
- [ ] Deploy v2 integration to production
- [ ] Monitor API calls and webhook processing
- [ ] Validate data synchronization
- [ ] Remove v1 endpoint references
- [ ] Update monitoring and alerting

### 6.2 Database Migration Script

```sql
-- Migration script for v1 to v2 ID format changes

-- Add UUID columns for v2 compatibility
ALTER TABLE whoop_sleep 
ADD COLUMN whoop_sleep_uuid UUID,
ADD COLUMN migration_status VARCHAR(20) DEFAULT 'pending';

ALTER TABLE whoop_workouts 
ADD COLUMN whoop_workout_uuid UUID,
ADD COLUMN migration_status VARCHAR(20) DEFAULT 'pending';

-- Create indexes for new UUID fields
CREATE INDEX idx_whoop_sleep_uuid ON whoop_sleep(whoop_sleep_uuid);
CREATE INDEX idx_whoop_workouts_uuid ON whoop_workouts(whoop_workout_uuid);

-- Migration tracking table
CREATE TABLE whoop_v2_migration_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100),
    record_id INTEGER,
    old_whoop_id INTEGER,
    new_whoop_uuid UUID,
    migration_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'completed'
);
```

### 6.3 Code Migration Examples

#### Sleep Data Handling
```python
# v1 Implementation
class SleepDataHandler:
    def store_sleep_data(self, sleep_data):
        return self.db.execute(
            "INSERT INTO whoop_sleep (whoop_sleep_id, data) VALUES (?, ?)",
            [sleep_data['id'], sleep_data]  # Integer ID
        )

# v2 Implementation (REQUIRED CHANGES)
class SleepDataHandlerV2:
    def store_sleep_data(self, sleep_data):
        return self.db.execute(
            "INSERT INTO whoop_sleep (whoop_sleep_uuid, whoop_sleep_v1_id, data) VALUES (?, ?, ?)",
            [
                sleep_data['id'],  # UUID string
                sleep_data.get('activityV1Id'),  # Backward compatibility
                sleep_data
            ]
        )
    
    def migrate_existing_sleep_record(self, v1_sleep_id: int, v2_uuid: str):
        return self.db.execute(
            "UPDATE whoop_sleep SET whoop_sleep_uuid = ?, migration_status = 'completed' WHERE whoop_sleep_id = ?",
            [v2_uuid, v1_sleep_id]
        )
```

#### API Client Migration
```python
# Complete v2 Client Implementation
class WhoopV2ApiClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.prod.whoop.com/developer/v2"
        
    def get_sleep_collection(self, start_date: str = None, end_date: str = None):
        params = {}
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date
            
        return self._make_request('GET', '/activity/sleep', params=params)
    
    def get_sleep_by_uuid(self, sleep_uuid: str):
        return self._make_request('GET', f'/activity/sleep/{sleep_uuid}')
    
    def get_workout_collection(self, start_date: str = None, end_date: str = None):
        params = {}
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date
            
        return self._make_request('GET', '/activity/workout', params=params)
    
    def get_workout_by_uuid(self, workout_uuid: str):
        return self._make_request('GET', f'/activity/workout/{workout_uuid}')
    
    def _make_request(self, method: str, endpoint: str, params: dict = None):
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            params=params
        )
        
        response.raise_for_status()
        return response.json()
```

### 6.4 Webhook Handler Updates

```python
# v2 Webhook Handler Implementation
class WhoopV2WebhookHandler:
    def process_webhook_event(self, event: dict):
        event_type = event['type']
        user_id = event['user_id']
        resource_id = event['id']  # Now UUID format for sleep/workout events
        
        if event_type == 'sleep.updated':
            # resource_id is now UUID
            sleep_data = self.whoop_client.get_sleep_by_uuid(resource_id)
            self.store_sleep_data(user_id, sleep_data)
            
        elif event_type == 'workout.updated':
            # resource_id is now UUID
            workout_data = self.whoop_client.get_workout_by_uuid(resource_id)
            self.store_workout_data(user_id, workout_data)
            
        elif event_type == 'recovery.updated':
            # Note: v2 recovery webhooks use sleep UUID instead of cycle ID
            recovery_data = self.whoop_client.get_recovery_by_id(resource_id)
            self.store_recovery_data(user_id, recovery_data)
```

---

## 7. Testing & Validation Strategy

### 7.1 v2 API Testing Checklist
- [ ] Test all v2 endpoints with proper authentication
- [ ] Validate UUID format handling in all responses
- [ ] Test pagination with nextToken parameters
- [ ] Verify activityV1Id presence for backward compatibility
- [ ] Test date range filtering on activity endpoints
- [ ] Validate webhook signature verification (unchanged)
- [ ] Test webhook processing with UUID identifiers

### 7.2 Data Migration Validation
- [ ] Verify all existing v1 integer IDs are preserved
- [ ] Confirm UUID fields are populated for new records
- [ ] Test backward compatibility queries using v1 IDs
- [ ] Validate data integrity during migration process
- [ ] Confirm no data loss during v1 to v2 transition

### 7.3 Integration Testing
- [ ] End-to-end testing of OAuth flow (unchanged)
- [ ] Real-time webhook event processing
- [ ] Rate limiting behavior validation
- [ ] Error handling with v2 error responses
- [ ] Performance impact assessment

---

## 8. Timeline & Migration Strategy

### 8.1 Recommended Migration Timeline

**Immediate (Now - End of Month 1):**
- Complete comprehensive code audit for v1 usage
- Begin development environment setup with v2 endpoints
- Start database schema planning and migration scripts

**Month 2-3: Development Phase**
- Implement all v2 API endpoint changes
- Update UUID handling throughout codebase
- Develop migration utilities and scripts
- Comprehensive testing of v2 integration

**Month 4-5: Testing & Validation**
- Extensive testing in staging environment
- Performance and load testing
- Security validation and webhook testing
- User acceptance testing if applicable

**Month 6-7: Production Migration**
- Gradual rollout to production
- Data migration execution
- Monitoring and validation
- v1 deprecation and cleanup

**Month 8 (Before October 2025):**
- Final validation and monitoring
- Complete removal of v1 references
- Documentation updates

### 8.2 Risk Mitigation
- **Parallel Testing:** Run v1 and v2 integrations in parallel during migration
- **Data Backup:** Complete data backup before migration
- **Rollback Plan:** Maintain ability to rollback if issues arise
- **Monitoring:** Enhanced monitoring during migration period
- **Gradual Migration:** Migrate users/features incrementally

---

## 9. Best Practices & Recommendations

### 9.1 Implementation Best Practices
1. **UUID Handling:** Always treat UUIDs as strings in code
2. **Backward Compatibility:** Maintain activityV1Id mapping during transition
3. **Database Design:** Use separate columns for v1 and v2 identifiers
4. **Error Handling:** Implement robust error handling for UUID format validation
5. **Testing:** Comprehensive testing with both v1 and v2 data formats

### 9.2 Performance Considerations
- **Database Indexing:** Ensure proper indexing on UUID columns
- **Query Optimization:** Update queries to use UUID efficiently
- **Memory Usage:** Monitor memory usage with UUID vs integer comparisons
- **Cache Keys:** Update caching strategies to use UUID identifiers

### 9.3 Security Considerations
- **UUID Validation:** Implement proper UUID format validation
- **Access Control:** Ensure UUID-based access control is secure
- **Logging:** Update logging to handle UUID identifiers appropriately
- **Data Privacy:** Maintain data privacy compliance during migration

---

## 10. Support & Resources

### 10.1 Official Support Channels
- **Developer Support:** https://developer.whoop.com/docs/developing/support/
- **API Documentation:** https://developer.whoop.com/api/
- **Migration Guide:** https://developer.whoop.com/docs/developing/v1-v2-migration/
- **Changelog:** https://developer.whoop.com/docs/api-changelog/

### 10.2 Community Resources
- **WHOOP Developer Community:** Available through official support channels
- **Stack Overflow:** Tag questions with 'whoop-api' and 'api-migration'
- **GitHub Examples:** Search for WHOOP API v2 implementation examples

### 10.3 Migration Assistance
- **Official Migration Support:** Available through WHOOP developer support
- **Implementation Examples:** Request examples for complex migration scenarios
- **Rate Limit Increases:** Available during migration period if needed

---

## 11. Conclusion

The WHOOP API v2 migration is mandatory and must be completed by October 1, 2025. The primary changes involve:

1. **Endpoint Updates:** All endpoints move from `/v1/` to `/v2/`
2. **UUID Identifiers:** Sleep and Workout IDs change from integers to UUIDs
3. **Enhanced Data Models:** Improved consistency and new fields
4. **Webhook Updates:** v2 webhook model with UUID identifiers

**Critical Success Factors:**
- Start migration immediately due to fixed deadline
- Focus on UUID handling as primary breaking change
- Maintain backward compatibility during transition period
- Comprehensive testing of all integration points
- Monitor and validate throughout migration process

**Resource Requirements:**
- 6-8 weeks development time recommended
- Database migration planning and execution
- Comprehensive testing across all integration points
- Production migration with monitoring and validation

The migration, while requiring significant effort, will result in a more robust and future-proof integration with the WHOOP platform.