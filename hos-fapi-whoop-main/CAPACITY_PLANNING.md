# WHOOP API Capacity Planning

## Free Tier Limits

- **Per-Minute Limit**: 100 requests/minute (60-second rolling window)
- **Daily Limit**: 10,000 requests/24 hours
- **Error Response**: HTTP 429 with `Retry-After` header

## Your Usage Pattern Analysis

### Naive Approach (All Endpoints Every Sync)

```
Endpoints per sync: 4 (Recovery, Sleep, Workout, Cycle)
Syncs per day: 3 (Morning, Midday, Evening)
Total calls per user per day: 12

Maximum users = 10,000 / 12 = ~833 users
```

**Capacity: ~800 users (with safety margin)**

### Optimized Approach (Time-Aware Endpoint Selection)

#### Morning Sync (6-11 AM UTC)
```
✅ Recovery - New daily readiness score available
✅ Sleep - Previous night's sleep data
❌ Workout - Skip (unlikely morning data yet)
❌ Cycle - Skip (strain builds throughout day)

API Calls: 2
```

#### Midday Sync (11 AM - 6 PM UTC)
```
❌ Recovery - Skip (already fetched in morning)
❌ Sleep - Skip (already fetched in morning)
✅ Workout - Morning/afternoon exercise data
✅ Cycle - Mid-day strain updates

API Calls: 2
```

#### Evening Sync (6 PM - 6 AM UTC)
```
❌ Recovery - Skip (wait for tomorrow morning)
❌ Sleep - Skip (wait for tomorrow morning)
✅ Workout - Evening exercise data
✅ Cycle - End-of-day strain score

API Calls: 2
```

**Total: 6 calls per user per day**

```
Maximum users = 10,000 / 6 = ~1,666 users
```

**Capacity: ~1,600 users (with safety margin)**

### Comparison

| Strategy | Calls/User/Day | Max Users | Efficiency Gain |
|----------|----------------|-----------|-----------------|
| Naive (all endpoints) | 12 | 800 | Baseline |
| Optimized (time-aware) | 6 | 1,600 | **2x capacity** |

## Per-Minute Limit Impact

### Scenario: Batch Sync at Peak Time

Assuming 1,600 users sync simultaneously:

```
Peak load = 1,600 users × 2 endpoints = 3,200 requests
Time to complete = 3,200 / 100 req/min = 32 minutes

Per-user delay = 32 minutes / 1,600 = 1.2 seconds average
```

**Result**: ✅ Manageable queue, no significant delays

### Mitigation Strategy: Jittered Sync Windows

Instead of exact times (9:00 AM), add randomization:

```python
# Spread syncs across 2-hour window
morning_window = random.choice(range(6, 11))  # 6-10 AM
sync_time = f"{morning_window}:{random.randint(0, 59):02d}"
```

This naturally distributes load:
- 1,600 users / 120 minutes = ~13 users/minute
- 13 users × 2 calls = 26 requests/minute
- **Well within 100 req/min limit**

## Scaling Beyond Free Tier

### Option 1: Request Rate Limit Increase

**Process**:
1. Submit TypeForm to WHOOP
2. Provide justification:
   - Current user count
   - Projected growth
   - Use case description
3. Receive response in 1-2 business days

**Cost**: Free (no additional charges mentioned)

**When to request**: When approaching 1,000+ users

### Option 2: Implement Webhooks

WHOOP supports webhooks for event-driven data updates:

**Benefits**:
- Eliminates polling
- Instant notifications for new data
- Drastically reduces API calls

**Example**:
```
Without webhooks: 6 calls/user/day (scheduled)
With webhooks: 1-3 calls/user/day (on-demand)

Capacity increase: 3,000-10,000 users
```

**Webhook endpoints available**:
- `recovery.updated`
- `sleep.updated`
- `workout.updated`
- `cycle.updated`

### Option 3: Enterprise Partnership

For large-scale deployments (10,000+ users):
- Custom rate limits
- Dedicated support
- Priority access to new features

Contact: WHOOP Business Development Team

## Implementation Recommendations

### Phase 1: MVP (0-500 users)
```
✅ Use naive approach (all endpoints, 3x daily)
✅ Monitor daily API usage
✅ No optimization needed yet
```

### Phase 2: Growth (500-1,000 users)
```
✅ Implement optimized time-aware sync
✅ Add jittered sync windows
✅ Monitor per-minute rate limit
✅ Prepare rate limit increase request
```

### Phase 3: Scale (1,000-1,500 users)
```
✅ Request rate limit increase from WHOOP
✅ Implement caching layer (Redis)
✅ Add sync queue with priority system
✅ Monitor costs and prepare for webhooks
```

### Phase 4: Enterprise (1,500+ users)
```
✅ Implement webhook-based sync
✅ Reduce polling frequency
✅ Consider enterprise partnership
✅ Add multi-region failover
```

## Cost Considerations

### Free Tier Economics

**Per-user API costs**: $0 (free tier)

**Infrastructure costs** (your backend):
- Database storage: ~100 MB per 1,000 users/month
- API server: Standard compute (1-2 vCPU)
- Estimated: $20-50/month for 1,000 users

### Rate Limit Increase

**No additional API costs mentioned** in WHOOP documentation

**Likely scenarios**:
- Small increase (20K/day): Free upon request
- Large increase (100K/day): May require partnership discussion

## Monitoring Dashboard

### Key Metrics to Track

```python
# Daily
- Total API calls (target: < 10,000)
- Calls per user average (target: 6)
- Peak minute usage (target: < 100 req/min)

# Per-sync window
- Morning sync success rate
- Midday sync success rate
- Evening sync success rate
- Average response times

# User-level
- Sync failures per user
- Missing data gaps
- Token expiration rate
```

### Alert Thresholds

```
⚠️ Warning (80%): 8,000 calls/day or 80 req/min
🚨 Critical (95%): 9,500 calls/day or 95 req/min
🛑 Emergency: HTTP 429 errors detected
```

## Testing the Optimized Strategy

Run the provided test script:

```bash
# Test current sync window (auto-detected)
python tests/test_optimized_sync.py
# Choose option 1

# Simulate full day (all 3 windows)
python tests/test_optimized_sync.py
# Choose option 2

# This will show exact API call count per window
```

## Conclusion

### Your Current Setup

With incremental syncing (3 times/day) and time-aware endpoint selection:

**Free Tier Capacity: 1,600 users**

### Recommendations

1. **Start with naive approach** (800 user capacity) for simplicity
2. **Implement optimized sync** when you hit 500 users
3. **Request rate increase** at 1,000 users
4. **Implement webhooks** beyond 1,500 users

### Next Steps

1. Test the optimized sync script with your real users
2. Monitor API usage in production
3. Set up CloudWatch/Datadog alerts for rate limits
4. Document sync windows in your user settings

**Questions?** Reach out to WHOOP developer support when approaching limits.
