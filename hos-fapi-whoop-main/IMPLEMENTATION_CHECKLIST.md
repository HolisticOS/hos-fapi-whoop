# Supabase-WHOOP Integration - Implementation Checklist

## Overview

This checklist will guide you through integrating WHOOP with your existing Supabase authentication from `well-planned-api`.

**Estimated Time**: 2-3 hours
**Difficulty**: Intermediate
**Prerequisites**: Supabase database access, well-planned-api running

---

## Phase 1: Database Setup (30 minutes)

### ✅ Step 1.1: Backup Existing Data (if any)

```bash
# Connect to your database
psql -U your_user -d your_database

# Backup existing tables (if they exist)
CREATE TABLE whoop_users_backup AS SELECT * FROM whoop_users;
CREATE TABLE whoop_oauth_states_backup AS SELECT * FROM whoop_oauth_states;
```

### ✅ Step 1.2: Drop Old Tables

```sql
-- Drop old tables (if they exist)
DROP TABLE IF EXISTS whoop_recovery CASCADE;
DROP TABLE IF EXISTS whoop_sleep CASCADE;
DROP TABLE IF EXISTS whoop_workout CASCADE;
DROP TABLE IF EXISTS whoop_cycle CASCADE;
DROP TABLE IF EXISTS whoop_sync_log CASCADE;
DROP TABLE IF EXISTS whoop_users CASCADE;
DROP TABLE IF EXISTS whoop_oauth_states CASCADE;
```

### ✅ Step 1.3: Run New Migration

```bash
cd /mnt/c/dev_skoth/hos/hos-mvp/hos-fapi-whoop/hos-fapi-whoop-main

# Run migration
psql -U your_user -d your_database -f migrations/002_whoop_data_tables_supabase.sql
```

### ✅ Step 1.4: Verify Tables Created

```sql
-- Check all WHOOP tables exist with UUID user_id
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name LIKE 'whoop_%'
  AND column_name = 'user_id';

-- Should show data_type = 'uuid' for all tables
```

### ✅ Step 1.5: Verify RLS Enabled

```sql
-- Check Row Level Security is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'whoop_%';

-- All should show rowsecurity = true
```

**✅ Phase 1 Complete** when:
- [ ] All 7 WHOOP tables created
- [ ] All tables have `user_id UUID` column
- [ ] Foreign keys to `auth.users(id)` exist
- [ ] RLS policies are enabled

---

## Phase 2: Backend Auth Integration (45 minutes)

### ✅ Step 2.1: Copy Auth Files from well-planned-api

```bash
cd /mnt/c/dev_skoth/hos/hos-mvp/hos-fapi-whoop/hos-fapi-whoop-main

# Create core directory
mkdir -p app/core

# Copy auth files
cp /mnt/c/dev_skoth/hos/well-planned-api/app/core/auth.py app/core/
cp /mnt/c/dev_skoth/hos/well-planned-api/app/core/security.py app/core/
cp /mnt/c/dev_skoth/hos/well-planned-api/app/db/supabase_client.py app/db/
```

### ✅ Step 2.2: Update Repository to Use UUID

```python
# app/repositories/whoop_data_repository.py

# Change ALL instances of:
# - user_id: str  →  user_id: UUID (from typing import UUID)
# - TEXT user IDs  →  UUID user IDs

from uuid import UUID  # Add this import

class WhoopDataRepository:

    async def store_recovery_records(
        self,
        user_id: UUID,  # Changed from str
        records: List[Dict[str, Any]]
    ) -> int:
        # Convert UUID to string for Supabase
        user_id_str = str(user_id)

        for record in records:
            data = {
                'user_id': user_id_str,  # Use UUID string
                # ... rest of fields
            }
```

### ✅ Step 2.3: Update Auth Service OAuth Flow

```python
# app/services/auth_service.py

from uuid import UUID

class WhoopAuthService:

    async def initiate_oauth(
        self,
        supabase_user_id: UUID  # Changed from str
    ) -> Dict[str, Any]:
        """Initiate OAuth for Supabase authenticated user"""

        user_id_str = str(supabase_user_id)

        # Store with UUID
        await self.db.table('whoop_oauth_states').insert({
            'user_id': user_id_str,  # UUID as string
            'state': state,
            # ...
        }).execute()

    async def handle_callback(
        self,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """Link WHOOP account to Supabase user"""

        # Get Supabase user_id (UUID) from state
        oauth_state = await self.db.table('whoop_oauth_states') \
            .select('*').eq('state', state).single().execute()

        supabase_user_id = oauth_state.data['user_id']  # UUID string

        # Exchange code for tokens
        token_response = await self._exchange_code_for_token(code)

        # Get WHOOP user profile
        whoop_user = await self._get_whoop_user_profile(token_response['access_token'])

        # Store mapping
        await self.db.table('whoop_users').upsert({
            'user_id': supabase_user_id,  # Supabase UUID
            'whoop_user_id': whoop_user['user_id'],  # WHOOP's ID
            'access_token': token_response['access_token'],
            'refresh_token': token_response['refresh_token'],
            'is_active': True
        }).execute()
```

### ✅ Step 2.4: Update API Endpoints

```python
# app/api/v1/whoop.py

from fastapi import APIRouter, Depends
from app.core.auth import get_current_user  # Import from core
from uuid import UUID

router = APIRouter(prefix="/api/v1/whoop", tags=["whoop"])

@router.post("/auth/initiate")
async def initiate_oauth(
    current_user: str = Depends(get_current_user)  # UUID as string
):
    """
    Headers:
        Authorization: Bearer <supabase_jwt>
    """
    user_uuid = UUID(current_user)  # Convert to UUID
    auth_service = WhoopAuthService()

    return await auth_service.initiate_oauth(user_uuid)


@router.get("/daily-data/{date}")
async def get_daily_data(
    date: str,
    current_user: str = Depends(get_current_user)
):
    """
    Get daily data for authenticated Supabase user
    """
    user_uuid = UUID(current_user)
    repository = WhoopDataRepository()

    return await repository.get_daily_summary(user_uuid, date)
```

**✅ Phase 2 Complete** when:
- [ ] Auth files copied from well-planned-api
- [ ] Repository uses UUID throughout
- [ ] OAuth flow links WHOOP to Supabase user
- [ ] All endpoints require Supabase JWT

---

## Phase 3: Flutter App Updates (45 minutes)

### ✅ Step 3.1: Remove Hardcoded Test User

```dart
// lib/presentation/screens/health_screen.dart

// DELETE THIS LINE:
// final String _userId = 'test_user_123';  ❌

// ADD THIS:
String? get _userId {
  final user = Supabase.instance.client.auth.currentUser;
  return user?.id;  // Returns UUID or null
}
```

### ✅ Step 3.2: Add JWT Token to API Calls

```dart
// lib/core/services/whoop_service.dart

class WhoopService {

  String? _getAuthToken() {
    final session = Supabase.instance.client.auth.currentSession;
    return session?.accessToken;
  }

  Future<WhoopDailyData> getDailyData({
    DateTime? date,
  }) async {
    final token = _getAuthToken();
    if (token == null) {
      throw Exception('User not authenticated');
    }

    final targetDate = date ?? DateTime.now();
    final dateStr = targetDate.toIso8601String().split('T')[0];

    final url = Uri.parse(
      '${AppConfig.whoopApiBaseUrl}/api/v1/whoop/daily-data/$dateStr',
    );

    final response = await _client.get(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',  // ✅ Add JWT
      },
    );

    // ... rest of method
  }

  Future<Map<String, dynamic>> initiateOAuth() async {
    final token = _getAuthToken();
    if (token == null) {
      throw Exception('User not authenticated');
    }

    final url = Uri.parse(
      '${AppConfig.whoopApiBaseUrl}/api/v1/whoop/auth/initiate',
    );

    final response = await _client.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',  // ✅ Add JWT
      },
    );

    // ... rest of method
  }
}
```

### ✅ Step 3.3: Update Health Screen

```dart
// lib/presentation/screens/health_screen.dart

class _HealthScreenState extends State<HealthScreen> {

  @override
  void initState() {
    super.initState();
    _checkAuthentication();
    _loadData();
  }

  void _checkAuthentication() {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) {
      // Redirect to login
      Navigator.of(context).pushReplacementNamed('/login');
      return;
    }

    setState(() {
      // User is authenticated
    });
  }

  Future<void> _checkWhoopConnection() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;

    try {
      final status = await _whoopService.getConnectionStatus();
      setState(() {
        _isWhoopConnected = status == WhoopConnectionStatus.connected;
      });
    } catch (e) {
      setState(() {
        _isWhoopConnected = false;
      });
    }
  }
}
```

**✅ Phase 3 Complete** when:
- [ ] Removed test user ID
- [ ] Using Supabase currentUser.id
- [ ] JWT token added to all API calls
- [ ] App checks authentication before API calls

---

## Phase 4: Testing (30 minutes)

### ✅ Step 4.1: Test User Authentication

```bash
# Terminal 1: Start well-planned-api
cd /mnt/c/dev_skoth/hos/well-planned-api
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Start hos-fapi-whoop
cd /mnt/c/dev_skoth/hos/hos-mvp/hos-fapi-whoop/hos-fapi-whoop-main
source venv-whoop/bin/activate
python app/main.py  # Port 8009
```

**Test Login**:
```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com",
    "password": "your_password"
  }'

# Save response:
{
  "access_token": "eyJhbG...",  # Copy this JWT
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000"  # UUID
  }
}
```

### ✅ Step 4.2: Test WHOOP OAuth Initiation

```bash
JWT="<paste_jwt_from_step_4.1>"

curl -X POST http://localhost:8009/api/v1/whoop/auth/initiate \
  -H "Authorization: Bearer $JWT"

# Should return:
{
  "auth_url": "https://api.prod.whoop.com/oauth/authorize?...",
  "state": "..."
}
```

### ✅ Step 4.3: Test OAuth Callback (Complete in Browser)

1. Copy `auth_url` from Step 4.2
2. Paste in browser
3. Login to WHOOP
4. Grant permissions
5. You'll be redirected (may show error - that's OK)
6. Backend should log successful connection

### ✅ Step 4.4: Verify Database

```sql
-- Check WHOOP user was created
SELECT
    wu.user_id,
    wu.whoop_user_id,
    wu.is_active,
    au.email
FROM whoop_users wu
JOIN auth.users au ON au.id = wu.user_id;

-- Should show your Supabase user linked to WHOOP
```

### ✅ Step 4.5: Test Data Fetch

```bash
curl -X GET "http://localhost:8009/api/v1/whoop/daily-data/2025-01-20" \
  -H "Authorization: Bearer $JWT"

# First time: Should trigger sync and fetch from WHOOP
# Subsequent calls: Should return from database (fast!)
```

### ✅ Step 4.6: Test in Flutter App

1. Login to app with Supabase credentials
2. Navigate to Health tab
3. Tap devices icon → Connect WHOOP
4. Complete OAuth in browser
5. Return to app
6. Verify data appears in Health tab

**✅ Phase 4 Complete** when:
- [ ] Can login with Supabase credentials
- [ ] OAuth flow links WHOOP to Supabase user
- [ ] Database shows `whoop_users` entry
- [ ] Can fetch WHOOP data with JWT
- [ ] Flutter app shows real data

---

## Troubleshooting

### Issue: "Invalid authentication token"

**Cause**: JWT token expired or invalid

**Solution**:
1. Re-login to get fresh token
2. Check token is passed in `Authorization: Bearer <token>` header

### Issue: "Foreign key violation on user_id"

**Cause**: Trying to use UUID that doesn't exist in auth.users

**Solution**:
1. Verify user exists in Supabase:
   ```sql
   SELECT id, email FROM auth.users WHERE id = '<uuid>';
   ```
2. Make sure using UUID from `get_current_user()`

### Issue: "Cannot connect to database"

**Cause**: Wrong Supabase credentials

**Solution**:
1. Check `.env` file has correct `SUPABASE_URL` and `SUPABASE_KEY`
2. Verify credentials match well-planned-api

### Issue: "User data not visible"

**Cause**: Row Level Security blocking access

**Solution**:
1. Use service_role key for backend (not anon key)
2. Verify RLS policies:
   ```sql
   SELECT * FROM pg_policies WHERE tablename LIKE 'whoop_%';
   ```

---

## Verification Checklist

Before considering integration complete, verify:

- [ ] Database has all 7 WHOOP tables with UUID user_id
- [ ] Foreign keys link to auth.users(id)
- [ ] RLS policies are enabled
- [ ] Backend uses get_current_user() from well-planned-api
- [ ] OAuth flow links WHOOP to Supabase user
- [ ] whoop_users table has entries
- [ ] Flutter app uses Supabase auth
- [ ] No hardcoded user IDs
- [ ] JWT token in all API calls
- [ ] Can fetch data end-to-end

---

## Next Steps After Integration

Once basic integration works:

1. **Implement Scheduled Sync** (see `IMPLEMENTATION_PLAN.md`)
2. **Remove Mock Data** from Flutter UI
3. **Add "Connect WHOOP" UI** for non-connected users
4. **Test with Multiple Users** to verify data isolation
5. **Monitor API Usage** to stay within rate limits

---

## Support

If you encounter issues:

1. Check logs in both backends (well-planned-api + hos-fapi-whoop)
2. Verify database state with SQL queries
3. Test with curl before testing in Flutter app
4. Review `SUPABASE_AUTH_INTEGRATION.md` for architecture details

---

## Summary

You're implementing:
- ✅ Single authentication system (Supabase)
- ✅ WHOOP linked to authenticated users
- ✅ Database-first data fetching
- ✅ Row-level data isolation
- ✅ Automatic cascade deletion

Total implementation time: ~2-3 hours with testing
