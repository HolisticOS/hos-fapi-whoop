"""
Smart Sync Service Tests
Tests for sync decision logic, caching, and data retrieval

USAGE:

1. Run unit tests (pytest):
   python -m pytest tests/test_smart_sync.py -v

2. Run interactive tester with JWT auth:
   python tests/test_smart_sync.py interactive

   This starts an interactive CLI where you can:
   - Authenticate with JWT tokens (manual input or test token)
   - Test all smart sync endpoints (recovery, sleep, cycle, workout)
   - Verify caching behavior (call endpoints twice)
   - Force refresh data
   - View sync status for all data types
   - Pretty print JSON responses

INTERACTIVE TESTER FEATURES:
- JWT token parsing and validation
- Extract user_id from token payload
- Backend health check
- Test each endpoint with/without force_refresh
- Caching verification (first call vs cached call vs force refresh)
- Sync status dashboard
- Pretty JSON formatting for responses
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import structlog
import sys
import os

# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.sync_service import SmartSyncService, SyncStatus, SyncThreshold


logger = structlog.get_logger(__name__)


@pytest.fixture
def user_id():
    """Test user ID"""
    return "a57f70b4-d0a4-4aef-b721-a4b526f64869"


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock = AsyncMock()
    mock.table = Mock()
    return mock


@pytest.fixture
def sync_service(mock_supabase):
    """SmartSyncService with mocked Supabase"""
    service = SmartSyncService()
    service.supabase = mock_supabase
    return service


class TestSyncDecisionLogic:
    """Test should_sync() decision making"""

    @pytest.mark.asyncio
    async def test_force_refresh_always_syncs(self, sync_service, user_id):
        """Test that force_refresh=True always returns should_sync=True"""
        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=True,
        )

        assert result['should_sync'] is True
        assert result['force_refresh'] is True
        assert 'User force refresh' in result['reason']

    @pytest.mark.asyncio
    async def test_no_sync_history_requires_sync(self, sync_service, user_id, mock_supabase):
        """Test that users with no sync history need to sync"""
        # Mock no previous sync
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=False,
        )

        assert result['should_sync'] is True
        assert 'No sync history' in result['reason']
        assert result['cached_record_count'] == 0

    @pytest.mark.asyncio
    async def test_recent_sync_uses_cache(self, sync_service, user_id, mock_supabase):
        """Test that recent sync (< 2 hours) uses cache"""
        # Mock recent sync (1 hour ago)
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                'last_sync_at': one_hour_ago,
                'sync_status': 'success',
                'records_synced': 5,
            }
        ]
        mock_supabase.table.return_value = mock_table

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=False,
        )

        assert result['should_sync'] is False
        assert 'fresh enough' in result['reason'].lower()
        assert result['cached_record_count'] == 5

    @pytest.mark.asyncio
    async def test_stale_sync_requires_refresh(self, sync_service, user_id, mock_supabase):
        """Test that stale sync (> 2 hours) requires refresh"""
        # Mock stale sync (3 hours ago)
        three_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                'last_sync_at': three_hours_ago,
                'sync_status': 'success',
                'records_synced': 5,
            }
        ]
        mock_supabase.table.return_value = mock_table

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=False,
        )

        assert result['should_sync'] is True
        assert 'NEEDS REFRESH' in result['reason']
        assert 'hours ago' in result['reason'].lower()

    @pytest.mark.asyncio
    async def test_different_thresholds_per_data_type(self, sync_service, user_id, mock_supabase):
        """Test that different data types have different thresholds"""
        # Workout has 1-hour threshold, recovery has 2-hour threshold
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                'last_sync_at': one_hour_ago,
                'sync_status': 'success',
                'records_synced': 5,
            }
        ]
        mock_supabase.table.return_value = mock_table

        # Recovery: 1 hour ago should be fresh (2-hour threshold)
        recovery_result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=False,
        )
        assert recovery_result['should_sync'] is False

        # Workout: 1 hour ago should be stale (1-hour threshold)
        workout_result = await sync_service.should_sync(
            user_id=user_id,
            data_type='workout',
            force_refresh=False,
        )
        assert workout_result['should_sync'] is True


class TestCachedDataRetrieval:
    """Test get_cached_data() method"""

    @pytest.mark.asyncio
    async def test_get_cached_recovery_data(self, sync_service, user_id, mock_supabase):
        """Test retrieving cached recovery data from database"""
        mock_recovery_records = [
            {'id': '123', 'recovery_score': 75.0, 'created_at': '2025-11-21T10:00:00Z'},
            {'id': '124', 'recovery_score': 80.0, 'created_at': '2025-11-21T09:00:00Z'},
        ]

        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_recovery_records
        mock_supabase.table.return_value = mock_table

        result = await sync_service.get_cached_data(
            user_id=user_id,
            data_type='recovery',
            limit=30,
        )

        assert result['source'] == 'cache'
        assert result['count'] == 2
        assert len(result['data']) == 2
        assert result['data'][0]['id'] == '123'

    @pytest.mark.asyncio
    async def test_get_cached_data_empty(self, sync_service, user_id, mock_supabase):
        """Test retrieving cached data when none exists"""
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        result = await sync_service.get_cached_data(
            user_id=user_id,
            data_type='recovery',
            limit=30,
        )

        assert result['count'] == 0
        assert result['data'] == []
        assert result['source'] == 'cache'

    @pytest.mark.asyncio
    async def test_get_cached_data_respects_limit(self, sync_service, user_id, mock_supabase):
        """Test that limit parameter is respected"""
        mock_records = [{'id': str(i)} for i in range(50)]
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_records[:30]
        mock_supabase.table.return_value = mock_table

        result = await sync_service.get_cached_data(
            user_id=user_id,
            data_type='recovery',
            limit=30,
        )

        # Verify limit was passed to query
        mock_table.select.return_value.eq.return_value.order.return_value.limit.assert_called_with(30)

    @pytest.mark.asyncio
    async def test_invalid_data_type(self, sync_service, user_id):
        """Test error handling for invalid data type"""
        result = await sync_service.get_cached_data(
            user_id=user_id,
            data_type='invalid_type',
            limit=30,
        )

        assert result['count'] == 0
        assert 'Unknown data type' in result['error']


class TestSyncLogging:
    """Test log_sync_attempt() method"""

    @pytest.mark.asyncio
    async def test_log_successful_sync(self, sync_service, user_id, mock_supabase):
        """Test logging successful sync"""
        mock_table = AsyncMock()
        mock_upsert = AsyncMock()
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = {'data': [{'id': '1'}]}
        mock_supabase.table.return_value = mock_table

        result = await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='recovery',
            status=SyncStatus.SUCCESS,
            records_synced=5,
        )

        assert result is True
        mock_table.upsert.assert_called_once()
        call_args = mock_table.upsert.call_args
        assert call_args[0][0]['sync_status'] == 'success'
        assert call_args[0][0]['records_synced'] == 5

    @pytest.mark.asyncio
    async def test_log_failed_sync(self, sync_service, user_id, mock_supabase):
        """Test logging failed sync with error message"""
        mock_table = AsyncMock()
        mock_upsert = AsyncMock()
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = {'data': [{'id': '1'}]}
        mock_supabase.table.return_value = mock_table

        result = await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='recovery',
            status=SyncStatus.FAILED,
            records_synced=0,
            error_message='Connection timeout',
        )

        assert result is True
        call_args = mock_table.upsert.call_args
        assert call_args[0][0]['sync_status'] == 'failed'
        assert call_args[0][0]['error_message'] == 'Connection timeout'

    @pytest.mark.asyncio
    async def test_upsert_conflict_handling(self, sync_service, user_id, mock_supabase):
        """Test that upsert handles existing records correctly"""
        mock_table = AsyncMock()
        mock_upsert = AsyncMock()
        mock_table.upsert.return_value = mock_upsert
        mock_upsert.execute.return_value = {'data': []}
        mock_supabase.table.return_value = mock_table

        await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='recovery',
            status=SyncStatus.SUCCESS,
            records_synced=10,
        )

        # Verify on_conflict parameter
        call_args = mock_table.upsert.call_args
        assert call_args[1]['on_conflict'] == 'user_id,data_type'


class TestSyncStatusForAllTypes:
    """Test get_sync_status_all() method"""

    @pytest.mark.asyncio
    async def test_get_sync_status_all_types(self, sync_service, user_id, mock_supabase):
        """Test retrieving sync status for all data types"""
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        three_hours_ago = (now - timedelta(hours=3)).isoformat()

        mock_sync_logs = [
            {
                'data_type': 'recovery',
                'last_sync_at': one_hour_ago,
                'sync_status': 'success',
                'records_synced': 5,
                'error_message': None,
            },
            {
                'data_type': 'sleep',
                'last_sync_at': three_hours_ago,
                'sync_status': 'success',
                'records_synced': 1,
                'error_message': None,
            },
        ]

        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = mock_sync_logs
        mock_supabase.table.return_value = mock_table

        result = await sync_service.get_sync_status_all(user_id)

        assert result['user_id'] == user_id
        assert 'recovery' in result['sync_status']
        assert 'sleep' in result['sync_status']

        # Recovery should not need sync (1 hour < 2 hour threshold)
        assert result['sync_status']['recovery']['needs_sync'] is False

        # Sleep should need sync (3 hours > 2 hour threshold)
        assert result['sync_status']['sleep']['needs_sync'] is True


class TestErrorHandling:
    """Test error handling in sync service"""

    @pytest.mark.asyncio
    async def test_should_sync_error_defaults_to_sync(self, sync_service, user_id, mock_supabase):
        """Test that errors in should_sync default to syncing"""
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception(
            'Database error'
        )
        mock_supabase.table.return_value = mock_table

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=False,
        )

        # On error, should sync to be safe
        assert result['should_sync'] is True
        assert 'Error checking sync log' in result['reason']

    @pytest.mark.asyncio
    async def test_log_sync_error_handling(self, sync_service, user_id, mock_supabase):
        """Test that log_sync_attempt handles errors gracefully"""
        mock_table = AsyncMock()
        mock_table.upsert.side_effect = Exception('Database write failed')
        mock_supabase.table.return_value = mock_table

        result = await sync_service.log_sync_attempt(
            user_id=user_id,
            data_type='recovery',
            status=SyncStatus.SUCCESS,
            records_synced=5,
        )

        # Should return False on error but not raise
        assert result is False


class TestThresholdConfiguration:
    """Test threshold configuration"""

    def test_recovery_threshold(self):
        """Test recovery threshold is 2 hours"""
        threshold = SyncThreshold.RECOVERY_THRESHOLD
        assert threshold == timedelta(hours=2)

    def test_workout_threshold(self):
        """Test workout threshold is 1 hour (more frequent)"""
        threshold = SyncThreshold.WORKOUT_THRESHOLD
        assert threshold == timedelta(hours=1)

    def test_get_threshold_method(self, sync_service):
        """Test _get_threshold returns correct threshold per data type"""
        assert sync_service._get_threshold('recovery') == timedelta(hours=2)
        assert sync_service._get_threshold('sleep') == timedelta(hours=2)
        assert sync_service._get_threshold('cycle') == timedelta(hours=2)
        assert sync_service._get_threshold('workout') == timedelta(hours=1)
        assert sync_service._get_threshold('unknown') == timedelta(hours=2)  # Default


class TestDataTypeSpecificLogic:
    """Test logic specific to different data types"""

    @pytest.mark.asyncio
    async def test_recovery_threshold_respected(self, sync_service, user_id, mock_supabase):
        """Test recovery uses 2-hour threshold"""
        # 1.5 hours ago should be fresh
        ninety_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat()
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                'last_sync_at': ninety_min_ago,
                'sync_status': 'success',
                'records_synced': 5,
            }
        ]
        mock_supabase.table.return_value = mock_table

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='recovery',
            force_refresh=False,
        )

        assert result['should_sync'] is False

    @pytest.mark.asyncio
    async def test_workout_threshold_stricter(self, sync_service, user_id, mock_supabase):
        """Test workout uses 1-hour threshold (stricter)"""
        # 45 minutes ago should be fresh for workout
        forty_five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        mock_table = AsyncMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                'last_sync_at': forty_five_min_ago,
                'sync_status': 'success',
                'records_synced': 3,
            }
        ]
        mock_supabase.table.return_value = mock_table

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='workout',
            force_refresh=False,
        )

        assert result['should_sync'] is False

        # 70 minutes ago should be stale for workout
        seventy_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=70)).isoformat()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                'last_sync_at': seventy_min_ago,
                'sync_status': 'success',
                'records_synced': 3,
            }
        ]

        result = await sync_service.should_sync(
            user_id=user_id,
            data_type='workout',
            force_refresh=False,
        )

        assert result['should_sync'] is True


class TestSyncEnumValues:
    """Test SyncStatus enum"""

    def test_sync_status_values(self):
        """Test SyncStatus enum has correct values"""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.SUCCESS.value == "success"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.PARTIAL.value == "partial"


# ============================================================================
# INTERACTIVE JWT TESTING MODE
# ============================================================================

import asyncio
import json
import base64
from typing import Optional
import httpx
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class SmartSyncTester:
    """Interactive CLI for testing smart sync endpoints with JWT authentication"""

    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.jwt_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None
        self.supabase: Optional[Client] = None
        self.logger = logger

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    def _print_header(self, text: str) -> None:
        """Print formatted header"""
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}\n")

    def _print_success(self, text: str) -> None:
        """Print success message"""
        print(f"✓ {text}")

    def _print_error(self, text: str) -> None:
        """Print error message"""
        print(f"✗ {text}")

    def _print_info(self, text: str) -> None:
        """Print info message"""
        print(f"ℹ {text}")

    def _extract_user_id_from_jwt(self) -> bool:
        """Extract user_id from JWT token payload"""
        try:
            # JWT format: header.payload.signature
            parts = self.jwt_token.split('.')
            if len(parts) != 3:
                self._print_error("Invalid JWT format")
                return False

            # Decode payload (add padding if needed)
            payload = parts[1]
            # Add padding
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            payload_json = json.loads(decoded)

            # Try different user_id field names
            self.user_id = (
                payload_json.get('sub') or
                payload_json.get('user_id') or
                payload_json.get('uid') or
                payload_json.get('email')
            )

            if self.user_id:
                self._print_success(f"Extracted user_id: {self.user_id}")
                return True
            else:
                self._print_error("Could not extract user_id from token. Available fields:")
                for key in payload_json.keys():
                    print(f"  - {key}")
                return False

        except Exception as e:
            self._print_error(f"Failed to decode JWT: {e}")
            return False

    async def _health_check(self) -> bool:
        """Check if backend is running"""
        try:
            response = await self.client.get(f"{self.base_url}/health", follow_redirects=True)
            if response.status_code == 200:
                self._print_success("Backend is running")
                return True
            elif response.status_code in [307, 308, 301, 302]:
                # Try the root endpoint instead
                response = await self.client.get(f"{self.base_url}/", follow_redirects=True)
                if response.status_code == 200:
                    self._print_success("Backend is running")
                    return True
                else:
                    self._print_success("Backend is running (detected)")
                    return True
            else:
                self._print_error(f"Backend returned status {response.status_code}")
                return False
        except Exception as e:
            self._print_error(f"Cannot reach backend at {self.base_url}: {e}")
            return False

    async def _authenticate_supabase(self) -> bool:
        """Authenticate via Supabase with email and password"""
        try:
            # Load Supabase config
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")

            if not supabase_url or not supabase_key:
                self._print_error("Missing SUPABASE_URL or SUPABASE_KEY in .env")
                return False

            # Initialize Supabase
            self.supabase = create_client(supabase_url, supabase_key)
            self._print_success("Supabase client initialized")

            # Get credentials
            print("\nEnter Supabase credentials:")
            email = input("  Email: ").strip()
            password = input("  Password: ").strip()

            # Login
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            self.jwt_token = response.session.access_token
            self.user_id = response.user.id

            self._print_success("Authenticated successfully")
            self._print_info(f"Extracted user_id: {self.user_id}")
            return True

        except Exception as e:
            self._print_error(f"Supabase authentication failed: {e}")
            return False

    async def _authenticate_manual(self) -> bool:
        """Manually input JWT token"""
        self._print_info("Paste your JWT token (from authentication provider)")
        self.jwt_token = input("JWT Token: ").strip()

        if not self.jwt_token:
            self._print_error("Token cannot be empty")
            return False

        return self._extract_user_id_from_jwt()

    async def _authenticate_test_token(self) -> bool:
        """Use a test JWT token"""
        # Example test token (you should use a real one from your auth system)
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNTdmNzBiNC1kMGE0LTRhZWYtYjcyMS1hNGI1MjZmNjQ4NjkiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJpYXQiOjE3MDA2MjAwMDB9.test_signature"
        self.jwt_token = test_token
        self._print_success("Using test JWT token")
        return self._extract_user_id_from_jwt()

    async def _authenticate(self) -> bool:
        """Authentication menu"""
        self._print_header("AUTHENTICATION")

        print("Select authentication method:")
        print("1. Supabase (email & password)")
        print("2. Manual JWT token input")
        print("3. Test token")
        print("4. Exit")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == '1':
            return await self._authenticate_supabase()
        elif choice == '2':
            return await self._authenticate_manual()
        elif choice == '3':
            return await self._authenticate_test_token()
        elif choice == '4':
            return False
        else:
            self._print_error("Invalid choice")
            return await self._authenticate()

    async def _test_recovery_endpoint(self, force_refresh: bool = False) -> None:
        """Test recovery smart sync endpoint"""
        try:
            params = {'force_refresh': force_refresh}
            response = await self.client.get(
                f"{self.base_url}/api/v1/smart/recovery",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params=params,
            )

            await self._print_response("Recovery Data", response)

        except Exception as e:
            self._print_error(f"Failed to fetch recovery data: {e}")

    async def _test_sleep_endpoint(self, force_refresh: bool = False) -> None:
        """Test sleep smart sync endpoint"""
        try:
            params = {'force_refresh': force_refresh}
            response = await self.client.get(
                f"{self.base_url}/api/v1/smart/sleep",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params=params,
            )

            await self._print_response("Sleep Data", response)

        except Exception as e:
            self._print_error(f"Failed to fetch sleep data: {e}")

    async def _test_cycle_endpoint(self, force_refresh: bool = False) -> None:
        """Test cycle smart sync endpoint"""
        try:
            params = {'force_refresh': force_refresh}
            response = await self.client.get(
                f"{self.base_url}/api/v1/smart/cycle",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params=params,
            )

            await self._print_response("Cycle Data", response)

        except Exception as e:
            self._print_error(f"Failed to fetch cycle data: {e}")

    async def _test_workout_endpoint(self, force_refresh: bool = False) -> None:
        """Test workout smart sync endpoint"""
        try:
            params = {'force_refresh': force_refresh}
            response = await self.client.get(
                f"{self.base_url}/api/v1/smart/workout",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params=params,
            )

            await self._print_response("Workout Data", response)

        except Exception as e:
            self._print_error(f"Failed to fetch workout data: {e}")

    async def _test_sync_status(self) -> None:
        """Test sync status endpoint"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/smart/sync-status",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
            )

            await self._print_response("Sync Status", response)

        except Exception as e:
            self._print_error(f"Failed to fetch sync status: {e}")

    async def _print_response(self, title: str, response: httpx.Response) -> None:
        """Pretty print API response"""
        print(f"\n{title}:")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            self._print_success("Request successful")
            try:
                data = response.json()
                self._print_formatted_json(data)
            except:
                print(response.text)
        else:
            self._print_error(f"Request failed")
            print(response.text)

    def _print_formatted_json(self, data: dict, indent: int = 0) -> None:
        """Pretty print JSON data"""
        for key, value in data.items():
            if isinstance(value, dict):
                print("  " * indent + f"{key}:")
                self._print_formatted_json(value, indent + 1)
            elif isinstance(value, list):
                print("  " * indent + f"{key}: ({len(value)} items)")
                if value and isinstance(value[0], dict):
                    print("  " * (indent + 1) + "Sample item:")
                    self._print_formatted_json(value[0], indent + 2)
            else:
                print("  " * indent + f"{key}: {value}")

    async def _test_caching(self) -> None:
        """Test caching behavior by calling endpoint twice"""
        self._print_header("CACHING VERIFICATION TEST")
        self._print_info("Calling recovery endpoint twice to verify caching...")

        # First call - should be from API or cache
        print("\n1. First call (should fetch from API or return cached data):")
        try:
            response1 = await self.client.get(
                f"{self.base_url}/api/v1/smart/recovery",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params={'force_refresh': False},
            )

            if response1.status_code == 200:
                data1 = response1.json()
                source1 = data1.get('metadata', {}).get('source', 'unknown')
                self._print_success(f"First call succeeded - Source: {source1}")
                timestamp1 = data1.get('metadata', {}).get('last_sync_at')
                if timestamp1:
                    print(f"   Timestamp: {timestamp1}")
            else:
                self._print_error(f"First call failed: {response1.status_code}")
                return

        except Exception as e:
            self._print_error(f"First call failed: {e}")
            return

        # Brief delay
        await asyncio.sleep(1)

        # Second call - should return cache
        print("\n2. Second call (should return from cache):")
        try:
            response2 = await self.client.get(
                f"{self.base_url}/api/v1/smart/recovery",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params={'force_refresh': False},
            )

            if response2.status_code == 200:
                data2 = response2.json()
                source2 = data2.get('metadata', {}).get('source', 'unknown')
                timestamp2 = data2.get('metadata', {}).get('last_sync_at')

                if source2 == 'cache':
                    self._print_success("Cache working correctly!")
                    print(f"   Source: {source2}")
                    print(f"   Timestamp: {timestamp2}")
                else:
                    self._print_info(f"Got source: {source2} (may be fresh API call)")
            else:
                self._print_error(f"Second call failed: {response2.status_code}")

        except Exception as e:
            self._print_error(f"Second call failed: {e}")

        # Force refresh
        print("\n3. Force refresh (should ignore cache):")
        try:
            response3 = await self.client.get(
                f"{self.base_url}/api/v1/smart/recovery",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params={'force_refresh': True},
            )

            if response3.status_code == 200:
                data3 = response3.json()
                source3 = data3.get('metadata', {}).get('source', 'unknown')
                self._print_success(f"Force refresh succeeded - Source: {source3}")
            else:
                self._print_error(f"Force refresh failed: {response3.status_code}")

        except Exception as e:
            self._print_error(f"Force refresh failed: {e}")

    async def _test_all_endpoint(self, force_refresh: bool = False) -> None:
        """Test all data endpoint"""
        try:
            params = {'force_refresh': force_refresh}
            response = await self.client.get(
                f"{self.base_url}/api/v1/smart/all",
                headers={"Authorization": f"Bearer {self.jwt_token}"},
                params=params,
            )

            await self._print_response("All Data", response)

        except Exception as e:
            self._print_error(f"Failed to fetch all data: {e}")

    async def _data_menu(self) -> None:
        """Menu for testing data endpoints"""
        while True:
            self._print_header("DATA ENDPOINTS")
            print("Select endpoint to test:")
            print("1. All Data (GET /api/v1/smart/all) ⭐ NEW")
            print("2. Recovery Data (GET /api/v1/smart/recovery)")
            print("3. Sleep Data (GET /api/v1/smart/sleep)")
            print("4. Cycle Data (GET /api/v1/smart/cycle)")
            print("5. Workout Data (GET /api/v1/smart/workout)")
            print("6. Sync Status (GET /api/v1/smart/sync-status)")
            print("7. Verify Caching (call recovery twice)")
            print("8. Force Refresh Recovery")
            print("9. Back to main menu")
            print("10. Exit")

            choice = input("\nEnter choice (1-10): ").strip()

            if choice == '1':
                await self._test_all_endpoint(force_refresh=False)
            elif choice == '2':
                await self._test_recovery_endpoint(force_refresh=False)
            elif choice == '3':
                await self._test_sleep_endpoint(force_refresh=False)
            elif choice == '4':
                await self._test_cycle_endpoint(force_refresh=False)
            elif choice == '5':
                await self._test_workout_endpoint(force_refresh=False)
            elif choice == '6':
                await self._test_sync_status()
            elif choice == '7':
                await self._test_caching()
            elif choice == '8':
                await self._test_recovery_endpoint(force_refresh=True)
            elif choice == '9':
                return
            elif choice == '10':
                break
            else:
                self._print_error("Invalid choice")

    async def main(self) -> None:
        """Main interactive menu"""
        async with self:
            self._print_header("SMART SYNC INTERACTIVE TESTER")
            self._print_info(f"Backend URL: {self.base_url}")

            # Health check
            if not await self._health_check():
                self._print_error("Cannot connect to backend. Make sure it's running.")
                return

            # Authenticate
            if not await self._authenticate():
                self._print_info("Authentication skipped")
                return

            self._print_success("Authentication successful")

            # Main menu
            while True:
                print("\n" + "="*70)
                print("  MAIN MENU")
                print("="*70)
                print("1. Test data endpoints")
                print("2. Test sync status")
                print("3. Verify caching behavior")
                print("4. Change JWT token")
                print("5. Exit")

                choice = input("\nEnter choice (1-5): ").strip()

                if choice == '1':
                    await self._data_menu()
                elif choice == '2':
                    await self._test_sync_status()
                elif choice == '3':
                    await self._test_caching()
                elif choice == '4':
                    if await self._authenticate():
                        self._print_success("Token updated")
                    else:
                        self._print_error("Token update failed")
                elif choice == '5':
                    self._print_success("Goodbye!")
                    break
                else:
                    self._print_error("Invalid choice")


if __name__ == '__main__':
    import sys

    # Check if running in interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        # Remove 'interactive' from sys.argv so pytest doesn't complain
        sys.argv.pop(1)
        # Run in interactive mode
        import asyncio
        asyncio.run(SmartSyncTester().main())
    else:
        # Run pytest normally
        pytest.main([__file__, '-v'])
