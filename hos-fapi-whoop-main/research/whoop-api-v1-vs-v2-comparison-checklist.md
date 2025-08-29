# WHOOP API v1 vs v2 Comprehensive Comparison & Migration Checklist

## Critical Migration Information

**DEADLINE: October 1, 2025**
- WHOOP API v1 will be completely removed
- All v1 webhooks will be disabled
- No grace period or backward compatibility after deadline
- Migration is MANDATORY for continued service

---

## 1. Complete v1 to v2 Endpoint Comparison

### 1.1 Base URL Changes
| Component | v1 | v2 |
|-----------|----|----|
| **Base URL** | `https://api.prod.whoop.com/developer/v1/` | `https://api.prod.whoop.com/developer/v2/` |
| **Authentication** | `https://api.prod.whoop.com/oauth/oauth2/auth` | `https://api.prod.whoop.com/oauth/oauth2/auth` |
| **Token Exchange** | `https://api.prod.whoop.com/oauth/oauth2/token` | `https://api.prod.whoop.com/oauth/oauth2/token` |

### 1.2 Endpoint Mapping Table

| Functionality | v1 Endpoint | v2 Endpoint | Breaking Changes |
|---------------|-------------|-------------|------------------|
| **User Profile** | `GET /v1/user/profile` | `GET /v2/user/profile/basic` | ✅ Minor path change |
| **Body Measurements** | `GET /v1/user/profile` | `GET /v2/user/measurement/body` | ✅ Separated endpoint |
| **Cycles Collection** | `GET /v1/cycle` | `GET /v2/cycle` | ✅ No change |
| **Specific Cycle** | `GET /v1/cycle/{id}` | `GET /v2/cycle/{id}` | ✅ No change |
| **Cycle Sleep** | ❌ Not available | `GET /v2/cycle/{cycleId}/sleep` | 🆕 New in v2 |
| **Recovery Collection** | `GET /v1/recovery` | `GET /v2/recovery` | ✅ No change |
| **Specific Recovery** | `GET /v1/recovery/{id}` | `GET /v2/recovery/{id}` | ✅ No change |
| **Recovery by Cycle** | `GET /v1/cycle/{cycleId}/recovery` | `GET /v2/cycle/{cycleId}/recovery` | ✅ No change |
| **Sleep Collection** | `GET /v1/activity/sleep` | `GET /v2/activity/sleep` | 🚨 UUID identifiers |
| **Specific Sleep** | `GET /v1/activity/sleep/{id}` | `GET /v2/activity/sleep/{uuid}` | 🚨 UUID identifiers |
| **Workout Collection** | `GET /v1/activity/workout` | `GET /v2/activity/workout` | 🚨 UUID identifiers |
| **Specific Workout** | `GET /v1/activity/workout/{id}` | `GET /v2/activity/workout/{uuid}` | 🚨 UUID identifiers |

**Legend:**
- ✅ = No breaking changes
- 🆕 = New feature in v2
- 🚨 = Breaking change requiring code update

---

## 2. Data Structure Changes

### 2.1 Identifier Format Changes

#### Sleep Resource IDs
```json
// v1 Response
{
  "id": 12345,
  "start": "2024-01-15T23:30:00.000Z"
}

// v2 Response
{
  "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
  "activityV1Id": 12345,
  "start": "2024-01-15T23:30:00.000Z"
}
```

#### Workout Resource IDs
```json
// v1 Response
{
  "id": 56789,
  "sport_id": 1,
  "strain": 16.8
}

// v2 Response
{
  "id": "7bfc6a15-5521-612f-b9a4-e274dd7afae9",
  "activityV1Id": 56789,
  "sport_id": 1,
  "strain": 16.8
}
```

### 2.2 New v2 Fields

| Resource | New v2 Fields | Description |
|----------|---------------|-------------|
| **Sleep** | `activityV1Id` | Backward compatibility with v1 integer ID |
| **Workout** | `activityV1Id` | Backward compatibility with v1 integer ID |
| **All Resources** | Enhanced timestamp handling | All times in UTC with explicit timezone_offset |
| **All Resources** | Improved optional fields | Better null-safety and field presence validation |

### 2.3 Webhook Event Changes

#### v1 Webhook Event
```json
{
  "user_id": 10129,
  "id": 10235,
  "type": "sleep.updated",
  "trace_id": "d3709ee7-104e-4f70-a928-2932964b017b"
}
```

#### v2 Webhook Event
```json
{
  "user_id": 10129,
  "id": "ecfc6a15-4661-442f-a9a4-f160dd7afae8",
  "type": "sleep.updated",
  "trace_id": "d3709ee7-104e-4f70-a928-2932964b017b"
}
```

**Key Webhook Changes:**
- v2 recovery webhooks use sleep UUID instead of cycle ID
- All sleep and workout webhook events use UUID identifiers
- Webhook version must match API version being used

---

## 3. Authentication & Technical Specifications

### 3.1 OAuth 2.0 Flow (No Changes)
| Component | v1 & v2 (Same) |
|-----------|----------------|
| **Authorization URL** | `https://api.prod.whoop.com/oauth/oauth2/auth` |
| **Token URL** | `https://api.prod.whoop.com/oauth/oauth2/token` |
| **Revocation URL** | `https://api.prod.whoop.com/oauth/oauth2/revoke` |
| **Grant Types** | `authorization_code`, `refresh_token` |
| **Token Types** | `Bearer` |

### 3.2 Scopes (No Changes)
| Scope | Description | v1 & v2 Support |
|-------|-------------|-----------------|
| `offline` | Refresh token capability | ✅ |
| `read:profile` | Basic profile + measurements | ✅ |
| `read:cycles` | Cycle data access | ✅ |
| `read:recovery` | Recovery scores | ✅ |
| `read:sleep` | Sleep data access | ✅ |
| `read:workouts` | Workout data access | ✅ |

### 3.3 Rate Limiting (No Changes)
| Limit Type | v1 & v2 (Same) |
|------------|----------------|
| **Per Minute** | 100 requests |
| **Per Day** | 10,000 requests |
| **Rate Limit Headers** | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| **Error Response** | `HTTP 429` with `Retry-After` header |

### 3.4 Security (No Changes)
- Webhook signature validation remains the same
- OAuth client credentials handling unchanged
- SSL/TLS requirements unchanged

---

## 4. Migration Checklist

### 4.1 Pre-Migration Assessment
- [ ] **Audit Current Integration**
  - [ ] Identify all v1 API usage in codebase
  - [ ] Document all Sleep and Workout ID storage locations
  - [ ] List all webhook event handlers
  - [ ] Review database schema for ID fields
  - [ ] Identify external integrations dependent on current data structure

- [ ] **Plan Database Changes**
  - [ ] Design UUID columns for Sleep and Workout tables
  - [ ] Plan migration script for existing data
  - [ ] Create backup strategy for existing data
  - [ ] Design rollback procedures

### 4.2 Development Phase Checklist

#### Phase 1: Foundation Updates
- [ ] **Update API Client**
  - [ ] Change base URL from `/v1/` to `/v2/`
  - [ ] Update Sleep endpoint calls to handle UUID identifiers
  - [ ] Update Workout endpoint calls to handle UUID identifiers
  - [ ] Add backward compatibility handling for `activityV1Id`
  - [ ] Test new endpoint access with existing authentication

- [ ] **Database Schema Updates**
  - [ ] Add UUID columns to Sleep data tables
  - [ ] Add UUID columns to Workout data tables
  - [ ] Add migration status tracking columns
  - [ ] Create indexes for new UUID columns
  - [ ] Maintain backward compatibility with existing integer ID columns

#### Phase 2: Code Implementation
- [ ] **Data Handling Updates**
  - [ ] Update Sleep data parsing to handle UUID format
  - [ ] Update Workout data parsing to handle UUID format
  - [ ] Implement UUID validation functions
  - [ ] Add conversion utilities for v1 ID to UUID mapping
  - [ ] Update all database queries to use UUID fields

- [ ] **Error Handling**
  - [ ] Update error handlers for UUID format validation
  - [ ] Add specific error handling for migration scenarios
  - [ ] Implement fallback logic for missing v2 data
  - [ ] Add logging for migration tracking

#### Phase 3: Webhook Migration
- [ ] **Webhook Handler Updates**
  - [ ] Set up separate v2 webhook endpoint for testing
  - [ ] Update webhook processing to handle UUID identifiers
  - [ ] Test signature validation (unchanged in v2)
  - [ ] Update event routing based on resource types
  - [ ] Test v2 recovery webhook changes (sleep UUID vs cycle ID)

- [ ] **Production Webhook Switchover**
  - [ ] Configure v2 webhook URL in WHOOP Developer Dashboard
  - [ ] Update webhook version setting
  - [ ] Verify webhook and API version alignment
  - [ ] Monitor webhook event processing

### 4.3 Testing & Validation Phase
- [ ] **Unit Testing**
  - [ ] Test UUID format handling in all functions
  - [ ] Test backward compatibility with `activityV1Id`
  - [ ] Test error handling for malformed UUIDs
  - [ ] Test data conversion utilities
  - [ ] Test webhook event processing with v2 format

- [ ] **Integration Testing**
  - [ ] End-to-end testing of OAuth flow
  - [ ] Test all v2 endpoints with real data
  - [ ] Validate webhook signature processing
  - [ ] Test rate limiting behavior
  - [ ] Test pagination with v2 responses

- [ ] **Data Integrity Testing**
  - [ ] Verify no data loss during migration
  - [ ] Test backward compatibility queries
  - [ ] Validate UUID uniqueness and format
  - [ ] Test historical data access
  - [ ] Verify webhook event completeness

### 4.4 Production Migration
- [ ] **Pre-Deployment**
  - [ ] Complete data backup
  - [ ] Run migration scripts on staging environment
  - [ ] Validate migrated data integrity
  - [ ] Test rollback procedures
  - [ ] Prepare monitoring and alerting

- [ ] **Deployment Execution**
  - [ ] Deploy v2 client code
  - [ ] Execute database migration scripts
  - [ ] Switch webhook endpoints to v2
  - [ ] Update API endpoint configurations
  - [ ] Enable v2-specific monitoring

- [ ] **Post-Deployment Validation**
  - [ ] Verify all v2 endpoints are functioning
  - [ ] Validate webhook event processing
  - [ ] Check data synchronization accuracy
  - [ ] Monitor error rates and performance
  - [ ] Confirm backward compatibility features

### 4.5 Final Cleanup
- [ ] **Code Cleanup**
  - [ ] Remove v1 endpoint references
  - [ ] Clean up temporary migration code
  - [ ] Update documentation to reflect v2 usage
  - [ ] Remove v1 compatibility layers (after validation period)

- [ ] **Monitoring & Maintenance**
  - [ ] Update monitoring dashboards for v2 metrics
  - [ ] Set up alerts for UUID format errors
  - [ ] Monitor v2 webhook reliability
  - [ ] Track migration success metrics
  - [ ] Document lessons learned and best practices

---

## 5. Risk Mitigation Strategies

### 5.1 Technical Risks
| Risk | Mitigation Strategy | Contingency Plan |
|------|--------------------|--------------------|
| **UUID Format Errors** | Implement strict UUID validation | Add error logging and graceful fallback |
| **Data Loss During Migration** | Complete backup before migration | Rollback procedures and data restoration |
| **Webhook Event Loss** | Implement event replay mechanism | Manual data synchronization procedures |
| **Performance Impact** | Test with production data volumes | Database optimization and indexing |
| **Integration Failures** | Phased rollout and canary deployment | Feature flags and rollback capability |

### 5.2 Timeline Risks
| Risk | Mitigation Strategy |
|------|---------------------|
| **Missing October 2025 Deadline** | Start migration immediately, allocate sufficient resources |
| **Longer Testing Phase** | Begin testing early, automate testing procedures |
| **Complex Data Migration** | Design and test migration scripts thoroughly |
| **External Dependencies** | Identify and coordinate with external system owners |

### 5.3 Business Risks
| Risk | Mitigation Strategy |
|------|---------------------|
| **Service Interruption** | Plan maintenance windows, implement graceful degradation |
| **User Experience Impact** | Maintain functionality during migration, clear communication |
| **Compliance Issues** | Review data handling changes, ensure continued compliance |
| **Cost Overruns** | Detailed project planning, regular progress reviews |

---

## 6. Migration Timeline Template

### Recommended 8-Week Migration Schedule

**Weeks 1-2: Assessment & Planning**
- Complete integration audit
- Database schema design
- Migration script development
- Testing environment setup

**Weeks 3-4: Development**
- v2 API client implementation
- Database schema updates
- Webhook handler modifications
- Migration utility development

**Weeks 5-6: Testing**
- Unit and integration testing
- Data migration testing
- Performance testing
- Security validation

**Weeks 7-8: Production Migration**
- Staging deployment and validation
- Production migration execution
- Post-migration monitoring
- Final cleanup and documentation

---

## 7. Success Metrics

### 7.1 Technical Metrics
- [ ] **100% v1 endpoint elimination** - No remaining v1 API calls
- [ ] **Zero data loss** - All historical data preserved and accessible
- [ ] **Webhook reliability** - All webhook events processed successfully
- [ ] **Performance maintenance** - No degradation in response times
- [ ] **Error rate** - Less than 0.1% UUID-related errors

### 7.2 Business Metrics  
- [ ] **Service continuity** - No service interruptions during migration
- [ ] **User experience** - No impact on user-facing functionality
- [ ] **Compliance maintenance** - All regulatory requirements continue to be met
- [ ] **Timeline adherence** - Migration completed before October 1, 2025

---

## 8. Post-Migration Considerations

### 8.1 Monitoring & Alerting
- Set up UUID format validation alerts
- Monitor v2 webhook event processing rates
- Track v2 API response times and error rates
- Alert on any remaining v1 endpoint usage

### 8.2 Documentation Updates
- Update API integration documentation
- Revise troubleshooting guides for UUID identifiers
- Update webhook event handling procedures
- Document migration lessons learned

### 8.3 Future Preparedness
- Implement version detection utilities
- Create automated migration testing
- Establish API version monitoring
- Plan for future API version transitions

---

## 9. Emergency Procedures

### 9.1 Migration Failure Recovery
If migration fails:
1. **Immediate Response**
   - Execute rollback procedures
   - Restore from backup if necessary
   - Revert to v1 endpoints temporarily
   - Assess root cause of failure

2. **Recovery Actions**
   - Fix identified issues
   - Re-test migration procedures
   - Execute migration retry
   - Validate data integrity

### 9.2 Post-Deadline Support
If issues arise after October 1, 2025:
- v1 API will be unavailable - no rollback option
- Focus on fixing v2 integration issues
- Use backup data for service restoration
- Contact WHOOP developer support for assistance

---

## 10. Resources & Support

### 10.1 Official Resources
- **Migration Guide:** https://developer.whoop.com/docs/developing/v1-v2-migration/
- **API Documentation:** https://developer.whoop.com/api/
- **Developer Support:** https://developer.whoop.com/docs/developing/support/
- **Changelog:** https://developer.whoop.com/docs/api-changelog/

### 10.2 Community Support
- Search Stack Overflow with tags: `whoop-api`, `api-migration`
- GitHub repositories with WHOOP API v2 examples
- Developer community forums and discussions

### 10.3 Professional Services
- Consider WHOOP professional migration services if available
- Engage external consultants for complex integrations
- Partner with experienced WHOOP integration specialists

---

## Conclusion

The migration from WHOOP API v1 to v2 is mandatory and must be completed by October 1, 2025. The primary focus should be on handling UUID identifiers for Sleep and Workout resources while maintaining backward compatibility during the transition period.

**Critical Success Factors:**
1. **Start Immediately** - Don't delay migration planning
2. **Focus on UUIDs** - This is the primary breaking change
3. **Test Thoroughly** - Validate all data migration and webhook handling
4. **Monitor Closely** - Track migration progress and system health
5. **Plan for Rollback** - Have contingency plans ready

The migration, while requiring significant effort, will result in a more robust and future-proof integration with the WHOOP platform. Following this comprehensive checklist and timeline will ensure a successful transition to v2 before the mandatory deadline.