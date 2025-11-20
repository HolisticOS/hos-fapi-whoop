# WHOOP-Supabase Authentication Integration Guide

## Overview

This guide explains how WHOOP authentication integrates with your existing Supabase authentication from `well-planned-api`.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Flutter App (hos_mvp_2)                                 │
│  - User logs in with Supabase (email/password)           │
│  - Gets JWT token from Supabase Auth                     │
│  - Uses same token for both APIs                         │
└───────────────┬──────────────────────────────────────────┘
                │
                ├→ Authorization: Bearer <supabase_jwt>
                │
                ↓
┌───────────────────────────────────────────────────────────┐
│  well-planned-api (Port 8000)                             │
│  - Calendar, Events, Nutrition                            │
│  - Uses get_current_user() → Returns UUID                 │
└───────────────────────────────────────────────────────────┘

                ↓
┌───────────────────────────────────────────────────────────┐
│  hos-fapi-whoop (Port 8009)                               │
│  - WHOOP data sync                                        │
│  - Uses get_current_user() → Returns UUID                 │
│  - Links WHOOP account to Supabase user_id (UUID)         │
└───────────────┬───────────────────────────────────────────┘
                │
                ├→ Supabase Database
                │  └→ auth.users (id: UUID) ← Supabase managed
                │     ├→ whoop_users (user_id: UUID) ← Links WHOOP
                │     ├→ whoop_recovery (user_id: UUID)
                │     ├→ whoop_sleep (user_id: UUID)
                │     └→ ... (all WHOOP data tables)
                │
                └→ WHOOP API
                   └→ OAuth with separate WHOOP user ID
```

## Data Model

### Supabase Auth User
```sql
auth.users (
    id UUID,                    -- Supabase user ID (PRIMARY)
    email TEXT,
    created_at TIMESTAMPTZ
)
```

### WHOOP User Mapping
```sql
whoop_users (
    id UUID,                    -- Internal ID
    user_id UUID → auth.users(id),  -- Supabase user (ONE-TO-ONE)
    whoop_user_id TEXT,          -- WHOOP's user ID (different system)
    access_token TEXT,           -- OAuth token for WHOOP API
    refresh_token TEXT,
    is_active BOOLEAN
)
```

**Key Point**: One Supabase user can have ONE WHOOP account

### WHOOP Data Tables
```sql
whoop_recovery (
    id TEXT,                    -- WHOOP record ID
    user_id UUID → auth.users(id),  -- Links to Supabase user
    recovery_score INTEGER,
    ...
)

whoop_sleep (
    id TEXT,
    user_id UUID → auth.users(id),
    ...
)

-- All WHOOP tables link to auth.users(id)
```

## Authentication Flow

### 1. User Login (Supabase)

```typescript
// Flutter app
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
});

const jwt_token = data.session.access_token;
const user_id = data.user.id;  // UUID (e.g., "550e8400-e29b-41d4-a716-446655440000")
```

### 2. Connect WHOOP Device

```
1. User taps "Connect WHOOP" in Flutter app

2. Flutter calls WHOOP backend with Supabase JWT:
   POST /api/v1/whoop/auth/initiate
   Headers: { Authorization: Bearer <supabase_jwt> }

3. Backend extracts user_id from JWT:
   user_id = await get_current_user(token)
   # Returns: UUID("550e8400-e29b-41d4-a716-446655440000")

4. Backend initiates WHOOP OAuth:
   - Stores user_id (UUID) in whoop_oauth_states table
   - Returns WHOOP authorization URL

5. User authorizes WHOOP in browser

6. WHOOP redirects back with code

7. Backend exchanges code for tokens:
   - Links WHOOP account to Supabase user_id (UUID)
   - Stores in whoop_users table
```

### 3. Fetch WHOOP Data

```
1. User opens Health tab in Flutter app

2. Flutter calls WHOOP backend:
   GET /api/v1/whoop/daily-data/2025-01-20
   Headers: { Authorization: Bearer <supabase_jwt> }

3. Backend extracts user_id from JWT:
   user_id = await get_current_user(token)
   # Returns UUID

4. Backend queries database:
   SELECT * FROM whoop_recovery
   WHERE user_id = '550e8400-e29b-41d4-a716-446655440000'
   AND DATE(created_at) = '2025-01-20'

5. Returns data to Flutter
```

## Implementation Files

### File 1: Auth Dependency (WHOOP backend)

```python
# app/core/auth.py
"""
Supabase authentication for WHOOP API
Reuses same auth logic as well-planned-api
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import structlog

from app.db.supabase_client import SupabaseClient, get_supabase

logger = structlog.get_logger()
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: SupabaseClient = Depends(get_supabase)
) -> str:  # Returns UUID as string
    """
    Extract and verify JWT token from Authorization header

    Returns:
        str: Supabase user ID (UUID format)
    """
    try:
        token = credentials.credentials
        response = db.client.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        user_id = response.user.id  # UUID string
        logger.info("User authenticated", user_id=user_id)

        return user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auth failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

### File 2: WHOOP Auth Service (Updated)

```python
# app/services/auth_service.py

from typing import Dict, Any
from uuid import UUID
import structlog

class WhoopAuthService:

    async def initiate_oauth(self, supabase_user_id: str) -> Dict[str, Any]:
        """
        Initiate OAuth flow for a Supabase authenticated user

        Args:
            supabase_user_id: UUID from auth.users.id (as string)
        """
        # Generate OAuth state
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)

        # Store state with Supabase user_id (UUID)
        await self.db.table('whoop_oauth_states').insert({
            'user_id': supabase_user_id,  # UUID string
            'state': state,
            'code_verifier': code_verifier,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }).execute()

        # Return WHOOP authorization URL
        return {
            'auth_url': whoop_auth_url,
            'state': state
        }

    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback and link WHOOP to Supabase user
        """
        # 1. Verify state and get Supabase user_id
        oauth_state = await self.db.table('whoop_oauth_states') \
            .select('*').eq('state', state).single().execute()

        supabase_user_id = oauth_state.data['user_id']  # UUID

        # 2. Exchange code for WHOOP tokens
        token_response = await self._exchange_code_for_token(code, ...)

        whoop_access_token = token_response['access_token']
        whoop_refresh_token = token_response['refresh_token']

        # 3. Get WHOOP user ID (different from Supabase ID)
        whoop_user = await self._get_whoop_user_profile(whoop_access_token)
        whoop_user_id = whoop_user['user_id']  # WHOOP's ID

        # 4. Store mapping in database
        await self.db.table('whoop_users').insert({
            'user_id': supabase_user_id,      # Supabase UUID
            'whoop_user_id': whoop_user_id,   # WHOOP's user ID
            'access_token': whoop_access_token,
            'refresh_token': whoop_refresh_token,
            'is_active': True
        }).execute()

        logger.info(
            "WHOOP account linked",
            supabase_user_id=supabase_user_id,
            whoop_user_id=whoop_user_id
        )

        return {'success': True}
```

### File 3: API Endpoints (Updated)

```python
# app/api/v1/whoop.py

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user  # Same as well-planned-api

router = APIRouter(prefix="/api/v1/whoop", tags=["whoop"])

@router.post("/auth/initiate")
async def initiate_whoop_oauth(
    current_user_id: str = Depends(get_current_user)  # UUID from Supabase JWT
):
    """
    Initiate WHOOP OAuth flow for authenticated Supabase user

    Headers:
        Authorization: Bearer <supabase_jwt>
    """
    auth_service = WhoopAuthService()
    oauth_data = await auth_service.initiate_oauth(current_user_id)

    return oauth_data


@router.get("/daily-data/{date}")
async def get_daily_data(
    date: str,
    current_user_id: str = Depends(get_current_user)  # UUID from Supabase JWT
):
    """
    Get daily WHOOP data for authenticated user

    Headers:
        Authorization: Bearer <supabase_jwt>

    Args:
        date: YYYY-MM-DD format
    """
    repository = WhoopDataRepository()

    # Query database with Supabase user_id (UUID)
    data = await repository.get_daily_summary(current_user_id, date)

    return data


@router.post("/sync")
async def trigger_sync(
    current_user_id: str = Depends(get_current_user)
):
    """
    Manually trigger WHOOP data sync for current user
    """
    sync_service = WhoopSyncService()

    # Sync data for this Supabase user
    result = await sync_service.sync_all_data(current_user_id)

    return result
```

## Flutter App Changes

### Before (Using test user ID)
```dart
final String _userId = 'test_user_123';  // ❌ Hardcoded

await _whoopService.getDailyData(userId: _userId, ...);
```

### After (Using Supabase authenticated user)
```dart
// Get current user from Supabase session
final user = supabase.auth.currentUser;
if (user == null) {
  // User not logged in
  return;
}

final String userId = user.id;  // ✅ Supabase UUID

// Get JWT token for API calls
final session = supabase.auth.currentSession;
final String jwtToken = session?.accessToken ?? '';

// Call WHOOP API with JWT token
await _whoopService.getDailyData(
  userId: userId,
  token: jwtToken,  // Pass JWT for authentication
  date: selectedDate
);
```

### Updated WHOOP Service (Flutter)

```dart
// lib/core/services/whoop_service.dart

class WhoopService {
  final http.Client _client = http.Client();

  Future<WhoopDailyData> getDailyData({
    required String userId,   // Supabase UUID
    required String token,    // Supabase JWT
    DateTime? date,
  }) async {
    final targetDate = date ?? DateTime.now();
    final dateStr = targetDate.toIso8601String().split('T')[0];

    final url = Uri.parse(
      '${AppConfig.whoopApiBaseUrl}/api/v1/whoop/daily-data/$dateStr',
    );

    final response = await _client.get(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',  // ✅ Include JWT
      },
    );

    // ... rest of the method
  }
}
```

## Database Migration Steps

### Step 1: Backup (If you have existing data)
```sql
-- Backup existing whoop data (if any)
CREATE TABLE whoop_recovery_backup AS SELECT * FROM whoop_recovery;
```

### Step 2: Drop old tables (if they exist)
```sql
DROP TABLE IF EXISTS whoop_recovery CASCADE;
DROP TABLE IF EXISTS whoop_sleep CASCADE;
DROP TABLE IF EXISTS whoop_workout CASCADE;
DROP TABLE IF EXISTS whoop_cycle CASCADE;
DROP TABLE IF EXISTS whoop_sync_log CASCADE;
DROP TABLE IF EXISTS whoop_users CASCADE;
DROP TABLE IF EXISTS whoop_oauth_states CASCADE;
```

### Step 3: Run new migration
```bash
psql -U your_user -d your_database -f migrations/002_whoop_data_tables_supabase.sql
```

### Step 4: Verify
```sql
-- Check all tables have user_id as UUID
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name LIKE 'whoop_%'
  AND column_name = 'user_id';

-- Should show: data_type = 'uuid' for all tables
```

## Testing

### Test 1: User Authentication
```bash
# Login to well-planned-api to get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# Response:
{
  "access_token": "eyJhbG...",  # JWT token
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000"  # UUID
  }
}
```

### Test 2: Initiate WHOOP OAuth
```bash
JWT_TOKEN="<token_from_step_1>"

curl -X POST http://localhost:8009/api/v1/whoop/auth/initiate \
  -H "Authorization: Bearer $JWT_TOKEN"

# Response:
{
  "auth_url": "https://api.prod.whoop.com/oauth/authorize?...",
  "state": "..."
}
```

### Test 3: Get Daily Data
```bash
curl -X GET "http://localhost:8009/api/v1/whoop/daily-data/2025-01-20" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Response:
{
  "recovery": { "score": 82, ... },
  "sleep": { "duration": "7h 32m", ... },
  ...
}
```

## Security Benefits

1. **Single Source of Truth**: Supabase manages all authentication
2. **Row Level Security**: Users can only see their own WHOOP data
3. **Token Validation**: JWT verified on every request
4. **Automatic Cleanup**: When Supabase user is deleted, all WHOOP data is CASCADE deleted
5. **Audit Trail**: All user actions tied to authenticated Supabase user

## Summary

✅ **Use Supabase UUID everywhere** - All tables reference `auth.users(id)`
✅ **Single JWT token** - Works for both well-planned-api and hos-fapi-whoop
✅ **Foreign key constraints** - Data integrity enforced at database level
✅ **Row Level Security** - Automatic data isolation per user
✅ **OAuth linking** - WHOOP account permanently tied to Supabase user

Ready to implement! Next step: Copy auth files from well-planned-api to hos-fapi-whoop.
