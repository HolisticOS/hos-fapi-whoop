# WHOOP API Comprehensive Research Report

## Executive Summary

WHOOP offers a robust API platform that provides access to comprehensive physiological and health metrics through their wearable devices. The API supports OAuth 2.0 authentication, real-time webhook integrations, and structured access to sleep, recovery, workout, and strain data. With v2 now available and migration required by October 1, 2025, this represents an excellent opportunity to integrate advanced health monitoring capabilities into existing health data sync infrastructure.

**Key Strengths:**
- Comprehensive 24/7 physiological monitoring
- Professional-grade accuracy and data quality
- Real-time webhook delivery capabilities
- Well-documented OAuth 2.0 implementation
- Reasonable default rate limits with increase options
- Strong developer ecosystem and SDK support

**Primary Use Cases:**
- High-performance athlete monitoring
- Corporate wellness programs
- Health research and analysis
- Personal optimization applications

---

## 1. Complete API Documentation Analysis

### 1.1 Official Documentation Resources

**Primary Developer Portal:** https://developer.whoop.com/
- Comprehensive documentation with API reference
- Interactive tutorials and code examples
- Developer dashboard for app management
- Support channels and community resources

**Key Documentation Sections:**
- **Introduction & Overview:** Platform goals and core concepts
- **Getting Started Guide:** App registration and initial setup
- **API Reference:** Complete endpoint documentation with schemas
- **OAuth 2.0 Guide:** Authentication flow implementation
- **Webhooks Documentation:** Real-time integration setup
- **Tutorials:** Practical implementation examples
- **Rate Limiting:** Usage quotas and request management

### 1.2 API Versions and Migration

**CRITICAL:** v2 of the WHOOP API is now available with **mandatory migration required by October 1, 2025**. The current v1 API and webhooks will be completely removed after this date.

**V2 Improvements:**
- Enhanced data structures and consistency
- Improved webhook reliability
- Better error handling and response codes
- UUID-based identifiers instead of integers
- Expanded authentication scopes

### 1.3 Developer Program Requirements

**Prerequisites:**
- WHOOP membership and device required
- Developer Dashboard account creation
- App approval process for production use
- Maximum of 5 apps per developer account

**Access Levels:**
- Free access to API with standard rate limits
- Rate limit increases available upon request
- Enterprise partnerships for high-volume usage

---

## 2. API Endpoints & Authentication Analysis

### 2.1 Authentication System

**OAuth 2.0 Implementation:**
- Industry-standard OAuth 2.0 protocol (RFC-6749)
- Authorization URL: `https://api.prod.whoop.com/oauth/oauth2/auth`
- Token URL: `https://api.prod.whoop.com/oauth/oauth2/token`
- Token Revocation: Supported for user privacy compliance

**Required Configuration:**
- Client ID and Client Secret from Developer Dashboard
- Registered Redirect URLs (must match exactly)
- State parameter (8 characters minimum, CSRF protection)
- Scope selection based on data access needs

**OAuth Scopes:**
- `offline`: Enables refresh token for background processing
- `read:profile`: Access user profile and measurement data
- `read:cycles`: Access cycle and recovery data
- `read:recovery`: Access detailed recovery metrics
- `read:sleep`: Access sleep tracking data
- `read:workouts`: Access workout and strain data

### 2.2 Token Management

**Access Token Characteristics:**
- Short-lived tokens (typically 1 hour)
- Bearer token authentication in Authorization header
- Expiry time provided in `expires_in` parameter
- Automatic invalidation on user permission revocation

**Refresh Token Process:**
- Requires `offline` scope during initial authorization
- First refresh request succeeds, subsequent requests fail
- Recommended to refresh tokens every hour
- Background job implementation recommended

**Security Considerations:**
- Client Secret must be used server-side only
- State parameter required for CSRF protection
- Token invalidation when user disables integration
- Signature validation for webhook security

### 2.3 Core API Endpoints

**Base URL:** `https://api.prod.whoop.com/developer/v1/`

#### User Profile Endpoints
```
GET /user/profile
- Returns basic profile information (name, email)
- Body measurements (height, weight, max heart rate)
- Requires read:profile scope
```

#### Recovery Endpoints
```
GET /cycle
- Get user's current cycle information
- Parameters: limit (default 1)
- Returns cycle details with associated recovery data

GET /cycle/{cycleId}/recovery
- Get specific recovery score for a cycle
- Includes HRV, RHR, respiratory rate
- Requires read:recovery scope
```

#### Sleep Endpoints
```
GET /activity/sleep
- Retrieve sleep data collection
- Date range filtering supported
- Sleep stages, efficiency, duration metrics
- Requires read:sleep scope
```

#### Workout Endpoints
```
GET /activity/workout
- Access workout and strain data
- Heart rate zones, calories burned
- Activity type classification
- Requires read:workouts scope
```

#### Cycle Endpoints
```
GET /cycle
- Core WHOOP data structure
- Links recovery, sleep, and strain data
- Pagination support with cursor-based navigation
- Maximum 50 records per request
```

---

## 3. Rate Limiting & Usage Quotas

### 3.1 Default Rate Limits

**Standard Limits (Applied to All Clients):**
- **100 requests per minute** (60-second window)
- **10,000 requests per 24-hour period** (86,400 seconds)

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100, 100;window=60, 10000;window=86400
X-RateLimit-Remaining: [remaining requests in current window]
X-RateLimit-Reset: [seconds until rate limit resets]
```

### 3.2 Rate Limit Management

**Error Response:**
- **HTTP 429 - Too Many Requests** when limit exceeded
- Includes `Retry-After` header with wait time
- Exponential backoff recommended for retries

**Best Practices:**
- Monitor rate limit headers in responses
- Implement request queuing and throttling
- Use webhooks to reduce polling frequency
- Cache frequently accessed data locally

### 3.3 Rate Limit Increases

**Process:**
- Submit request via TypeForm link in documentation
- Provide detailed justification and usage projections
- Response typically within 1-2 business days
- Enterprise partnerships available for high-volume needs

**Considerations for Increase Requests:**
- Document expected usage patterns
- Demonstrate webhook implementation to reduce API calls
- Show data caching strategies
- Provide business justification and user impact

---

## 4. Available Health Metrics & Data Structures

### 4.1 Core WHOOP Metrics

#### Strain (0-21 Scale)
**Measurement Basis:** Perceived exertion and cardiovascular load
```json
{
  "strain": 15.2,
  "category": "high", // light(0-9), moderate(10-13), high(14-17), all_out(18-21)
  "kilojoules": 1847,
  "average_heart_rate": 156,
  "max_heart_rate": 184,
  "zone_durations": {
    "zone_1": 480, // seconds
    "zone_2": 720,
    "zone_3": 1200,
    "zone_4": 600,
    "zone_5": 300
  }
}
```

#### Recovery (0-100% Scale)
**Calculation Factors:**
- Resting heart rate (RHR)
- Heart rate variability (HRV) 
- Respiratory rate
- Sleep duration and quality
- Skin temperature
- Blood oxygen levels

```json
{
  "recovery_score": 67,
  "category": "green", // green(67-100), yellow(34-66), red(0-33)
  "hrv": {
    "rmssd": 42.5,
    "baseline": 38.2
  },
  "rhr": 52,
  "respiratory_rate": 14.2,
  "skin_temp_celsius": 33.8
}
```

#### Sleep Data Structure
```json
{
  "id": "uuid-string",
  "start": "2024-01-15T23:30:00.000Z",
  "end": "2024-01-16T07:15:00.000Z",
  "duration_seconds": 27900,
  "efficiency_percentage": 87,
  "stages": {
    "light_sleep_seconds": 12600,
    "rem_sleep_seconds": 7200,
    "deep_sleep_seconds": 5400,
    "awake_seconds": 2700
  },
  "score": {
    "stage_summary": 85,
    "sleep_needed": 28800, // 8 hours in seconds
    "respiratory_rate": 13.8,
    "sleep_consistency": 78
  }
}
```

#### Workout Data Structure
```json
{
  "id": "uuid-string",
  "sport_id": 1, // Running
  "start": "2024-01-15T18:00:00.000Z",
  "end": "2024-01-15T19:30:00.000Z",
  "strain": 16.8,
  "distance_meters": 8047,
  "altitude_gain_meters": 145,
  "average_heart_rate": 162,
  "max_heart_rate": 189,
  "kilojoules": 2156,
  "percent_recorded": 98.5
}
```

### 4.2 Data Availability Timing

**Real-time Data:**
- Heart rate: Continuous during wear
- Activity tracking: Live during workouts
- Basic strain accumulation: Throughout day

**Processed Data Timing:**
- **Recovery scores:** Available upon waking (typically 6-9 AM)
- **Sleep analysis:** Processed within 30-60 minutes of wake
- **Workout summaries:** Available within 5-15 minutes post-workout
- **Daily strain:** Continuous updates, final score at end of day

**Historical Data Access:**
- Complete historical data available via API
- No apparent retention limits mentioned
- Pagination required for large date ranges
- Efficient cursor-based pagination system

### 4.3 Data Quality & Accuracy

**WHOOP Advantages:**
- 24/7 continuous monitoring (no gaps)
- Professional-grade sensors and algorithms
- Individual baseline calibration
- Validated against laboratory equipment
- Focus on physiological optimization vs basic activity tracking

**Data Reliability Factors:**
- Requires consistent wear for accurate baselines
- New user calibration period (typically 1-2 weeks)
- Environmental factors can affect skin temperature readings
- Battery life considerations for continuous monitoring

---

## 5. Webhook Integration Capabilities

### 5.1 Webhook Overview

**Real-time Data Delivery:**
- Event-based notifications when new data becomes available
- Eliminates need for constant API polling
- Reduces API request volume significantly
- Supports multiple event types simultaneously

**Webhook URL Requirements:**
- HTTPS endpoint required (no HTTP allowed)
- Must accept POST requests with JSON payloads
- Should respond with 2XX status codes within 1 second
- Must implement signature validation for security

### 5.2 Supported Webhook Events

**Available Event Types:**
- `recovery.updated`: New recovery score calculated
- `recovery.deleted`: Recovery data removed (rare)
- `sleep.updated`: Sleep session processed and scored
- `sleep.deleted`: Sleep data removed (rare)
- `workout.updated`: Workout completed and processed
- `workout.deleted`: Workout data removed (rare)

**Event Payload Structure:**
```json
{
  "user_id": 10129,
  "id": 10235,
  "type": "workout.updated",
  "trace_id": "d3709ee7-104e-4f70-a928-2932964b017b"
}
```

### 5.3 Webhook Security & Validation

**Security Headers:**
- `X-WHOOP-Signature`: SHA256 HMAC signature
- `X-WHOOP-Signature-Timestamp`: Unix timestamp

**Validation Process:**
1. Extract signature and timestamp from headers
2. Construct payload string: `timestamp + '.' + body`
3. Generate HMAC-SHA256 using app secret key
4. Base64 encode and compare with provided signature
5. Verify timestamp is within acceptable window (5 minutes)

**Example Validation (Python):**
```python
import hashlib
import hmac
import base64
import time

def validate_webhook(signature, timestamp, body, secret):
    # Check timestamp freshness
    if abs(time.time() - int(timestamp)) > 300:  # 5 minutes
        return False
    
    # Construct message
    message = f"{timestamp}.{body}"
    
    # Generate signature
    expected = base64.b64encode(
        hmac.new(
            secret.encode(), 
            message.encode(), 
            hashlib.sha256
        ).digest()
    ).decode()
    
    return signature == expected
```

### 5.4 Webhook Delivery & Reliability

**Delivery Guarantees:**
- 5 retry attempts over approximately 1 hour
- Exponential backoff between retry attempts
- Retries triggered by non-2XX responses or timeouts
- No retries after 5 failed attempts

**Reliability Considerations:**
- Webhook events are notifications, not data transfers
- Must make subsequent API calls to retrieve actual data
- Possible duplicate events (implement idempotency)
- Potential missed webhooks (implement reconciliation)

**Recommended Implementation Pattern:**
```python
@app.post("/webhook/whoop")
async def handle_whoop_webhook(request):
    # 1. Validate signature
    if not validate_webhook_signature(request):
        return 401
    
    # 2. Parse event
    event = request.json()
    
    # 3. Queue for background processing
    await queue_webhook_processing(event)
    
    # 4. Respond quickly
    return 200

async def process_webhook_event(event):
    # Background processing
    if event['type'] == 'sleep.updated':
        sleep_data = await fetch_sleep_data(event['user_id'], event['id'])
        await store_sleep_data(sleep_data)
```

---

## 6. Integration Requirements & Setup

### 6.1 Developer Dashboard Setup

**App Creation Process:**
1. Navigate to https://developer-dashboard.whoop.com/apps/create
2. Create or join a development team
3. Configure app details and branding
4. Select required OAuth scopes (minimum one required)
5. Add redirect URLs (must match OAuth requests exactly)
6. Configure webhook URL (if using real-time features)
7. Submit for approval (production apps only)

**Team Management:**
- Multiple developers can collaborate on apps
- Role-based permissions within teams
- Centralized app management and monitoring

### 6.2 Development Environment Setup

**Prerequisites:**
- WHOOP membership and active device
- Development environment with HTTPS capability
- OAuth 2.0 library (recommended vs manual implementation)
- Webhook endpoint for real-time integration (optional)

**Recommended OAuth Libraries:**
- **Python:** `authlib`, `requests-oauthlib`
- **JavaScript:** `passport-oauth2`, `oauth2-server`
- **Go:** `golang.org/x/oauth2`
- **Java:** `spring-security-oauth2`

**Environment Variables:**
```bash
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
WHOOP_REDIRECT_URL=https://yourapp.com/auth/callback
WHOOP_WEBHOOK_SECRET=your_webhook_secret
```

### 6.3 Authentication Flow Implementation

**Step 1: Authorization Request**
```http
GET https://api.prod.whoop.com/oauth/oauth2/auth
  ?client_id=YOUR_CLIENT_ID
  &response_type=code
  &redirect_uri=YOUR_REDIRECT_URL
  &scope=read:profile read:recovery read:sleep read:workouts offline
  &state=RANDOM_8_CHAR_STRING
```

**Step 2: Handle Authorization Callback**
```python
@app.get("/auth/callback")
async def handle_whoop_callback(code: str, state: str):
    # Verify state parameter
    if not verify_state(state):
        raise HTTPException(401, "Invalid state")
    
    # Exchange code for tokens
    token_response = await exchange_code_for_tokens(code)
    
    # Store tokens securely
    await store_user_tokens(user_id, token_response)
    
    return redirect("/dashboard")
```

**Step 3: Token Exchange**
```python
async def exchange_code_for_tokens(code):
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URL,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    
    response = await http_client.post(
        'https://api.prod.whoop.com/oauth/oauth2/token',
        data=data
    )
    
    return response.json()
```

### 6.4 API Request Implementation

**Base Request Pattern:**
```python
class WhoopClient:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.prod.whoop.com/developer/v1"
        
    async def make_request(self, method, endpoint, **kwargs):
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        response = await http_client.request(
            method, 
            f"{self.base_url}{endpoint}",
            headers=headers,
            **kwargs
        )
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            await asyncio.sleep(retry_after)
            return await self.make_request(method, endpoint, **kwargs)
        
        response.raise_for_status()
        return response.json()
```

---

## 7. Comparison with Existing Sahha Integration

### 7.1 Architecture Comparison

| Aspect | WHOOP API | Sahha API (Current) |
|--------|-----------|---------------------|
| **Authentication** | OAuth 2.0 standard | Custom token system with Firebase UID |
| **Data Access** | User-centric, permission-based | Profile-based with external IDs |
| **Real-time Updates** | Webhooks with event notifications | Webhook support available |
| **Rate Limiting** | 100/min, 10K/day (increasable) | Custom rate limiting implementation |
| **Data Quality** | Professional-grade sensors | Health platform aggregation |
| **Device Requirement** | WHOOP device + membership | Multi-platform health data |

### 7.2 Data Structure Comparison

**WHOOP Advantages:**
- More focused, consistent data quality
- Direct device measurement (no intermediary platforms)
- Specialized for performance optimization
- Real-time physiological monitoring

**Sahha Advantages:**
- Broader health data ecosystem integration
- Multi-device support (Apple Health, Google Fit, etc.)
- More comprehensive biomarker categories
- Flexible data source integration

### 7.3 Integration Complexity

**WHOOP Integration Characteristics:**
- **Simpler:** Standard OAuth 2.0 flow
- **More Standardized:** Industry-standard authentication patterns
- **Better Documentation:** Comprehensive developer resources
- **Cleaner API Design:** RESTful endpoints with consistent schemas

**Sahha Integration Characteristics:**
- **More Complex:** Custom authentication and profile management
- **More Flexible:** Supports multiple data sources
- **Broader Scope:** Comprehensive health data aggregation
- **Custom Implementation:** Tailored for specific use cases

### 7.4 Use Case Alignment

**WHOOP Best For:**
- High-performance athlete monitoring
- Recovery and training optimization
- Corporate wellness programs focused on performance
- Research requiring continuous physiological data

**Sahha Best For:**
- Comprehensive health data aggregation
- Multi-platform health ecosystem integration
- Broad population health monitoring
- General wellness and lifestyle tracking

---

## 8. Implementation Roadmap & Recommendations

### 8.1 Phase 1: Foundation Setup (Weeks 1-2)

**Immediate Actions:**
1. **WHOOP Developer Account Setup**
   - Create developer account and team
   - Register initial application in dashboard
   - Configure OAuth scopes and redirect URLs
   - Obtain Client ID and Client Secret

2. **Development Environment**
   - Set up HTTPS development environment
   - Install OAuth 2.0 library dependencies
   - Create webhook endpoint infrastructure
   - Implement basic authentication flow

3. **Database Schema Extensions**
   - Design WHOOP-specific data tables
   - Plan integration with existing Supabase schema
   - Consider data isolation vs integration strategies
   - Implement migration scripts for new structures

### 8.2 Phase 2: Core Integration (Weeks 3-4)

**Authentication Implementation:**
```python
# New service class following existing pattern
class WhoopService:
    def __init__(self):
        self.client_id = settings.WHOOP_CLIENT_ID
        self.client_secret = settings.WHOOP_CLIENT_SECRET
        self.base_url = "https://api.prod.whoop.com/developer/v1"
        
    async def initiate_oauth_flow(self, user_id: str, redirect_uri: str):
        # Generate authorization URL
        # Store state parameter for validation
        # Return authorization URL for user redirect
        
    async def handle_oauth_callback(self, code: str, state: str):
        # Validate state parameter
        # Exchange code for access/refresh tokens
        # Store tokens securely in database
        # Return user authentication status
        
    async def refresh_access_token(self, user_id: str):
        # Retrieve stored refresh token
        # Request new access token
        # Update stored tokens
        # Handle refresh failures
```

**Basic Data Retrieval:**
```python
# Core data fetching methods
async def get_current_recovery(self, user_id: str):
    # Get current cycle
    # Fetch recovery data
    # Transform to standard schema
    
async def get_sleep_data(self, user_id: str, start_date: datetime, end_date: datetime):
    # Paginated sleep data retrieval
    # Handle rate limiting
    # Transform and store data
    
async def get_workout_data(self, user_id: str, start_date: datetime, end_date: datetime):
    # Fetch workout collections
    # Process strain and performance metrics
    # Store in standardized format
```

### 8.3 Phase 3: Webhook Integration (Weeks 5-6)

**Webhook Infrastructure:**
```python
@app.post("/webhooks/whoop")
async def handle_whoop_webhook(request: Request):
    # Signature validation
    # Event parsing and queuing
    # Quick response for reliability
    
async def process_whoop_webhook_event(event: dict):
    # Background event processing
    # API calls to retrieve actual data
    # Database updates and synchronization
    # Error handling and retry logic
```

**Real-time Data Pipeline:**
1. Webhook receives event notification
2. Queue event for background processing
3. Fetch updated data via API
4. Transform and store in database
5. Trigger downstream updates
6. Update user interface in real-time

### 8.4 Phase 4: Advanced Features (Weeks 7-8)

**Data Synchronization Service:**
```python
class WhoopSyncService:
    async def full_historical_sync(self, user_id: str):
        # Comprehensive data backfill
        # Efficient pagination handling
        # Progress tracking and resumption
        
    async def incremental_sync(self, user_id: str):
        # Latest data synchronization
        # Smart date range detection
        # Duplicate prevention
        
    async def reconciliation_sync(self, user_id: str):
        # Periodic data verification
        # Gap detection and filling
        # Data integrity checks
```

**Integration with Existing Analysis:**
- Extend health-agent-main to support WHOOP data
- Update bio-coach-hub dashboard for WHOOP metrics
- Integrate with HolisticOS analysis system
- Add WHOOP-specific archetype analysis

### 8.5 Production Deployment Considerations

**Security Requirements:**
- Secure token storage with encryption
- Webhook signature validation
- Rate limit monitoring and alerting
- User permission management

**Scalability Considerations:**
- Database indexing for WHOOP data
- Efficient webhook processing queues
- Connection pooling for API requests
- Monitoring and observability

**Data Privacy & Compliance:**
- GDPR compliance for EU users
- User consent and data portability
- Secure data deletion capabilities
- Audit logging for data access

---

## 9. Technical Implementation Examples

### 9.1 Authentication Service Implementation

```python
from datetime import datetime, timedelta
import aiohttp
import secrets
from typing import Optional, Dict, Any

class WhoopAuthService:
    def __init__(self):
        self.client_id = settings.WHOOP_CLIENT_ID
        self.client_secret = settings.WHOOP_CLIENT_SECRET
        self.auth_url = "https://api.prod.whoop.com/oauth/oauth2/auth"
        self.token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
        
    def generate_authorization_url(self, redirect_uri: str, scopes: list) -> tuple[str, str]:
        """Generate OAuth authorization URL and state parameter"""
        state = secrets.token_urlsafe(16)
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'state': state
        }
        
        url = f"{self.auth_url}?" + urlencode(params)
        return url, state
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Calculate expiry time
                    expires_in = token_data.get('expires_in', 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    return {
                        'access_token': token_data['access_token'],
                        'refresh_token': token_data.get('refresh_token'),
                        'expires_at': expires_at,
                        'scope': token_data.get('scope', '')
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Token exchange failed: {response.status} {error_text}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token using refresh token"""
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    expires_in = token_data.get('expires_in', 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    return {
                        'access_token': token_data['access_token'],
                        'refresh_token': token_data.get('refresh_token', refresh_token),
                        'expires_at': expires_at
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Token refresh failed: {response.status} {error_text}")
```

### 9.2 Data Service Implementation

```python
class WhoopDataService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.prod.whoop.com/developer/v1"
        self.rate_limiter = AsyncRateLimiter(100, 60)  # 100 per minute
        
    async def _make_authenticated_request(self, method: str, endpoint: str, **kwargs):
        """Make rate-limited authenticated request to WHOOP API"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, 
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            ) as response:
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._make_authenticated_request(method, endpoint, **kwargs)
                
                # Handle successful responses
                if response.status in [200, 201]:
                    return await response.json()
                
                # Handle errors
                error_text = await response.text()
                raise Exception(f"API request failed: {response.status} {error_text}")
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Fetch user profile information"""
        return await self._make_authenticated_request('GET', '/user/profile')
    
    async def get_current_recovery(self) -> Optional[Dict[str, Any]]:
        """Get current recovery score and metrics"""
        # First get current cycle
        cycle_data = await self._make_authenticated_request('GET', '/cycle?limit=1')
        
        if not cycle_data or not cycle_data.get('data'):
            return None
        
        current_cycle = cycle_data['data'][0]
        cycle_id = current_cycle['id']
        
        # Get recovery for this cycle
        recovery_data = await self._make_authenticated_request(
            'GET', f'/cycle/{cycle_id}/recovery'
        )
        
        return recovery_data
    
    async def get_sleep_collection(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch sleep data for date range with pagination"""
        all_sleep_data = []
        next_token = None
        
        while True:
            params = {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'limit': 50
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            response = await self._make_authenticated_request(
                'GET', '/activity/sleep', params=params
            )
            
            sleep_records = response.get('data', [])
            all_sleep_data.extend(sleep_records)
            
            next_token = response.get('next_token')
            if not next_token:
                break
        
        return all_sleep_data
    
    async def get_workout_collection(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch workout data for date range with pagination"""
        all_workouts = []
        next_token = None
        
        while True:
            params = {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'limit': 50
            }
            
            if next_token:
                params['nextToken'] = next_token
            
            response = await self._make_authenticated_request(
                'GET', '/activity/workout', params=params
            )
            
            workouts = response.get('data', [])
            all_workouts.extend(workouts)
            
            next_token = response.get('next_token')
            if not next_token:
                break
        
        return all_workouts
```

### 9.3 Webhook Handler Implementation

```python
import hmac
import hashlib
import base64
import time
from fastapi import Request, HTTPException

class WhoopWebhookHandler:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret.encode()
    
    def validate_webhook_signature(self, signature: str, timestamp: str, body: bytes) -> bool:
        """Validate WHOOP webhook signature"""
        try:
            # Check timestamp freshness (5 minutes)
            if abs(time.time() - int(timestamp)) > 300:
                return False
            
            # Construct message
            message = f"{timestamp}.{body.decode()}"
            
            # Generate expected signature
            expected = base64.b64encode(
                hmac.new(
                    self.webhook_secret,
                    message.encode(),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            return hmac.compare_digest(signature, expected)
            
        except Exception as e:
            logger.error(f"Webhook signature validation error: {e}")
            return False
    
    @app.post("/webhooks/whoop")
    async def handle_webhook(self, request: Request):
        """Handle incoming WHOOP webhooks"""
        body = await request.body()
        
        # Extract security headers
        signature = request.headers.get('X-WHOOP-Signature')
        timestamp = request.headers.get('X-WHOOP-Signature-Timestamp')
        
        if not signature or not timestamp:
            raise HTTPException(status_code=400, detail="Missing security headers")
        
        # Validate signature
        if not self.validate_webhook_signature(signature, timestamp, body):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook event
        try:
            event = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        
        # Queue for background processing
        await self.queue_webhook_event(event)
        
        return {"status": "received"}
    
    async def queue_webhook_event(self, event: Dict[str, Any]):
        """Queue webhook event for background processing"""
        # Add to processing queue (Redis, Celery, etc.)
        await webhook_queue.put({
            'event_type': event['type'],
            'user_id': event['user_id'],
            'resource_id': event['id'],
            'trace_id': event.get('trace_id'),
            'received_at': datetime.utcnow().isoformat()
        })
    
    async def process_webhook_event(self, event: Dict[str, Any]):
        """Background processing of webhook events"""
        try:
            user_id = event['user_id']
            event_type = event['event_type']
            resource_id = event['resource_id']
            
            # Get user's access token
            user_tokens = await self.get_user_tokens(user_id)
            if not user_tokens:
                logger.error(f"No tokens found for user {user_id}")
                return
            
            # Create data service
            whoop_service = WhoopDataService(user_tokens['access_token'])
            
            # Process based on event type
            if event_type == 'recovery.updated':
                recovery_data = await whoop_service.get_recovery_by_id(resource_id)
                await self.store_recovery_data(user_id, recovery_data)
                
            elif event_type == 'sleep.updated':
                sleep_data = await whoop_service.get_sleep_by_id(resource_id)
                await self.store_sleep_data(user_id, sleep_data)
                
            elif event_type == 'workout.updated':
                workout_data = await whoop_service.get_workout_by_id(resource_id)
                await self.store_workout_data(user_id, workout_data)
            
            logger.info(f"Successfully processed {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}")
            # Implement retry logic or dead letter queue
```

---

## 10. Strategic Recommendations

### 10.1 Integration Strategy

**Recommended Approach: Parallel Integration**
- Maintain existing Sahha integration for broad health data
- Add WHOOP as specialized high-performance data source
- Create unified data layer that combines both sources
- Allow users to choose primary data source based on needs

**Benefits:**
- Expanded market reach (casual wellness + performance optimization)
- Data redundancy and validation opportunities
- Specialized use case optimization
- Competitive differentiation

### 10.2 Technical Architecture Recommendations

**Database Strategy:**
```sql
-- WHOOP-specific tables alongside existing Sahha tables
CREATE TABLE whoop_users (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    whoop_user_id INTEGER UNIQUE,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    scopes TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE whoop_recovery_data (
    id UUID PRIMARY KEY,
    whoop_user_id UUID REFERENCES whoop_users(id),
    cycle_id UUID,
    recovery_score FLOAT,
    hrv_rmssd FLOAT,
    resting_heart_rate INTEGER,
    skin_temp_celsius FLOAT,
    recorded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Similar tables for sleep, workouts, strain data
```

**Service Layer Architecture:**
```python
# Unified health data service
class UnifiedHealthService:
    def __init__(self):
        self.sahha_service = SahhaService()
        self.whoop_service = WhoopService()
    
    async def get_recovery_data(self, user_id: str, date_range: tuple) -> Dict[str, Any]:
        """Get recovery data from available sources"""
        recovery_data = {}
        
        # Try WHOOP first (higher fidelity for recovery)
        if await self.whoop_service.user_has_connection(user_id):
            recovery_data['whoop'] = await self.whoop_service.get_recovery_data(user_id, date_range)
        
        # Get Sahha data as well/fallback
        if await self.sahha_service.user_has_connection(user_id):
            recovery_data['sahha'] = await self.sahha_service.get_recovery_data(user_id, date_range)
        
        return self._merge_recovery_data(recovery_data)
```

### 10.3 Product Strategy

**Target User Segments:**
1. **Elite Athletes:** WHOOP primary, Sahha supplementary
2. **Fitness Enthusiasts:** Both sources with preference settings
3. **General Wellness:** Sahha primary, WHOOP optional
4. **Corporate Wellness:** Mixed deployment based on user preference

**Feature Differentiation:**
- WHOOP users get advanced recovery insights
- Performance optimization recommendations
- Training load management
- Professional athlete comparison metrics

### 10.4 Business Model Considerations

**Revenue Opportunities:**
- Premium tier focused on WHOOP integration features
- Corporate partnerships with performance-focused businesses
- Advanced analytics and coaching based on WHOOP data
- Professional athlete monitoring services

**Cost Considerations:**
- WHOOP device requirement may limit user base
- Higher engagement from committed users
- Potential for higher-value B2B partnerships
- Reduced churn due to device investment

---

## 11. Conclusion

The WHOOP API represents a significant opportunity to enhance the existing health data infrastructure with professional-grade physiological monitoring capabilities. The API's mature OAuth 2.0 implementation, comprehensive webhook system, and high-quality health metrics make it an excellent complement to the existing Sahha integration.

**Key Success Factors:**
1. **Proper OAuth Implementation:** Leverage existing authentication patterns
2. **Webhook-First Integration:** Minimize API calls through real-time notifications
3. **Data Quality Focus:** Capitalize on WHOOP's superior physiological accuracy
4. **User Experience Integration:** Seamlessly blend with existing dashboard
5. **Progressive Rollout:** Start with core features, expand based on user feedback

**Implementation Timeline:** 8-10 weeks for full integration
**Resource Requirements:** 1-2 backend developers, 1 frontend developer
**Expected ROI:** Higher user engagement, expanded market reach, premium feature differentiation

The WHOOP API integration aligns perfectly with the existing health data ecosystem while providing opportunities for product differentiation and market expansion into the high-performance health monitoring segment.