"""
Comprehensive test suite for WHOOP Microservice
Tests all major components: OAuth, API client, database operations, and endpoints
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.services.oauth_service import WhoopOAuthService
from app.services.whoop_api_client import WhoopAPIClient, RateLimitManager
from app.models.database import WhoopDataService
from app.models.schemas import WhoopUser, WhoopRecoveryRecord

# Test client for API testing
client = TestClient(app)


class TestBasicEndpoints:
    """Test basic application endpoints"""
    
    def test_root_endpoint(self):
        """Test that the root endpoint returns expected response"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "WHOOP Health Metrics API" in data["message"]
        assert data["version"] == "1.0.0-mvp"
    
    def test_health_endpoint_ready(self):
        """Test health check ready endpoint"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
    
    def test_health_endpoint_live(self):
        """Test health check liveness endpoint"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "uptime" in data


class TestOAuthService:
    """Test WHOOP OAuth 2.0 service functionality"""
    
    def setup_method(self):
        """Set up OAuth service for testing"""
        self.oauth_service = WhoopOAuthService()
    
    def test_oauth_service_initialization(self):
        """Test OAuth service initializes correctly"""
        assert self.oauth_service.client_id is not None
        assert self.oauth_service.auth_url == "https://api.prod.whoop.com/oauth/oauth2/auth"
        assert self.oauth_service.token_url == "https://api.prod.whoop.com/oauth/oauth2/token"
        assert len(self.oauth_service.default_scopes) == 6
        assert "offline" in self.oauth_service.default_scopes
        assert "read:recovery" in self.oauth_service.default_scopes
    
    def test_generate_pkce_pair(self):
        """Test PKCE code generation"""
        verifier, challenge = self.oauth_service._generate_pkce_pair()
        
        # Verify verifier length and format
        assert len(verifier) >= 43
        assert len(verifier) <= 128
        assert verifier.replace("-", "").replace("_", "").isalnum()
        
        # Verify challenge length and format
        assert len(challenge) >= 43
        assert challenge.replace("-", "").replace("_", "").isalnum()
    
    def test_generate_state(self):
        """Test OAuth state parameter generation"""
        user_id = "test_user_123"
        state = self.oauth_service._generate_state(user_id)
        
        assert len(state) >= 8  # WHOOP minimum requirement
        assert "." in state  # Our format includes separator
        
        # Test extraction
        extracted_user = self.oauth_service._extract_user_from_state(state)
        assert extracted_user == user_id
    
    @pytest.mark.asyncio
    async def test_initiate_oauth_flow(self):
        """Test OAuth flow initiation"""
        user_id = "test_user_123"
        
        auth_response = await self.oauth_service.initiate_oauth_flow(user_id)
        
        assert auth_response.authorization_url.startswith("https://api.prod.whoop.com/oauth/oauth2/auth")
        assert "client_id=" in auth_response.authorization_url
        assert "code_challenge=" in auth_response.authorization_url
        assert "code_challenge_method=S256" in auth_response.authorization_url
        assert len(auth_response.state) >= 8
    
    @pytest.mark.asyncio
    async def test_token_validation(self):
        """Test token validation logic"""
        user_id = "nonexistent_user"
        
        # Test with non-existent user
        is_valid = await self.oauth_service.is_token_valid(user_id)
        assert is_valid is False


class TestRateLimitManager:
    """Test rate limiting functionality"""
    
    def setup_method(self):
        """Set up rate limiter for testing"""
        self.rate_limiter = RateLimitManager()
    
    @pytest.mark.asyncio
    async def test_rate_limit_acquisition(self):
        """Test rate limit permit acquisition"""
        # First request should succeed
        permit = await self.rate_limiter.acquire_permit()
        assert permit is True
        
        # Check status
        status = self.rate_limiter.get_rate_limit_status()
        assert status["minute_used"] >= 1
        assert status["daily_used"] >= 1
        assert status["minute_remaining"] == status["minute_limit"] - status["minute_used"]
    
    def test_rate_limit_status(self):
        """Test rate limit status reporting"""
        status = self.rate_limiter.get_rate_limit_status()
        
        assert "minute_limit" in status
        assert "minute_used" in status
        assert "minute_remaining" in status
        assert "daily_limit" in status
        assert "daily_used" in status
        assert "daily_remaining" in status
        assert status["minute_limit"] == 100  # Default WHOOP limit
        assert status["daily_limit"] == 10000  # Default WHOOP limit


class TestWhoopAPIClient:
    """Test WHOOP API client functionality"""
    
    def setup_method(self):
        """Set up API client for testing"""
        self.api_client = WhoopAPIClient()
    
    def test_api_client_initialization(self):
        """Test API client initializes correctly"""
        assert self.api_client.base_url == "https://api.prod.whoop.com/developer/v1"
        assert self.api_client.max_retries == 3
        assert self.api_client.request_timeout == 30
        assert isinstance(self.api_client.rate_limiter, RateLimitManager)
    
    def test_client_status(self):
        """Test client status reporting"""
        status = self.api_client.get_client_status()
        
        assert status["status"] == "operational"
        assert status["base_url"] == self.api_client.base_url
        assert "cache_size" in status
        assert "rate_limiting" in status
        assert "configuration" in status
    
    @pytest.mark.asyncio
    @patch('app.services.whoop_api_client.WhoopOAuthService')
    async def test_authenticated_request_no_token(self, mock_oauth_service):
        """Test authenticated request with no valid token"""
        # Mock OAuth service to return None (no token)
        mock_oauth_instance = Mock()
        mock_oauth_instance.get_valid_access_token = AsyncMock(return_value=None)
        mock_oauth_service.return_value = mock_oauth_instance
        
        result = await self.api_client._make_authenticated_request(
            method="GET",
            endpoint="user/profile",
            user_id="test_user_123"
        )
        
        assert result is None


class TestDatabaseModels:
    """Test database model functionality"""
    
    def test_whoop_user_model(self):
        """Test WhoopUser model validation"""
        user = WhoopUser(
            user_id="test_user_123",
            access_token="test_token",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            scopes="read:profile read:recovery",
            is_active=True
        )
        
        assert user.user_id == "test_user_123"
        assert user.access_token == "test_token"
        assert user.is_active is True
        assert user.scopes == "read:profile read:recovery"
    
    def test_whoop_recovery_record(self):
        """Test WhoopRecoveryRecord model validation"""
        recovery = WhoopRecoveryRecord(
            user_id="test_user_123",
            cycle_id="cycle_456",
            recovery_score=75.5,
            hrv_rmssd=42.3,
            resting_heart_rate=52,
            skin_temp_celsius=36.2,
            respiratory_rate=14.5,
            date=date.today()
        )
        
        assert recovery.user_id == "test_user_123"
        assert recovery.recovery_score == 75.5
        assert recovery.hrv_rmssd == 42.3
        assert recovery.resting_heart_rate == 52
        assert recovery.date == date.today()


class TestAPIEndpoints:
    """Test API endpoints with authentication"""
    
    def setup_method(self):
        """Set up for API endpoint testing"""
        self.api_key = "dev-api-key-change-in-production"
        self.headers = {"X-API-Key": self.api_key}
    
    def test_oauth_config_endpoint(self):
        """Test OAuth configuration endpoint"""
        response = client.get("/api/v1/whoop/auth/oauth-config")
        assert response.status_code == 200
        
        data = response.json()
        assert data["authorization_url"] == "https://api.prod.whoop.com/oauth/oauth2/auth"
        assert data["pkce_supported"] is True
        assert data["pkce_required"] is True
        assert "offline" in data["default_scopes"]
        assert "read:recovery" in data["default_scopes"]
    
    def test_oauth_authorize_endpoint(self):
        """Test OAuth authorization endpoint"""
        request_data = {
            "user_id": "test_user_123",
            "redirect_uri": "http://localhost:8001/callback",
            "scopes": ["read:profile", "read:recovery", "offline"]
        }
        
        response = client.post("/api/v1/whoop/auth/authorize", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["authorization_url"].startswith("https://api.prod.whoop.com/oauth/oauth2/auth")
    
    def test_client_status_endpoint(self):
        """Test client status endpoint"""
        response = client.get("/api/v1/client-status", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["service_status"] == "operational"
        assert "whoop_client" in data
        assert "timestamp" in data
    
    def test_internal_endpoint_without_api_key(self):
        """Test internal endpoints require API key"""
        response = client.get("/api/v1/data/recovery/test_user_123")
        assert response.status_code == 422  # Missing required header
    
    def test_auth_status_endpoint_with_api_key(self):
        """Test auth status endpoint with valid API key"""
        response = client.get("/api/v1/auth/status/test_user_123", headers=self.headers)
        # Should return 200 even for non-existent user (just shows not connected)
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "connection_status" in data
        assert data["user_id"] == "test_user_123"


class TestDataValidation:
    """Test data validation and error handling"""
    
    def test_invalid_user_id_format(self):
        """Test validation with invalid user IDs"""
        api_key = "dev-api-key-change-in-production"
        headers = {"X-API-Key": api_key}
        
        # Test empty user ID
        response = client.get("/api/v1/auth/status/", headers=headers)
        assert response.status_code == 404  # Not found due to missing path parameter
        
        # Test very long user ID
        long_user_id = "x" * 1000
        response = client.get(f"/api/v1/auth/status/{long_user_id}", headers=headers)
        assert response.status_code == 200  # Should still process but show not connected
    
    def test_invalid_date_ranges(self):
        """Test endpoints with invalid date parameters"""
        api_key = "dev-api-key-change-in-production"
        headers = {"X-API-Key": api_key}
        
        # Test with invalid date format
        response = client.get(
            "/api/v1/health-metrics/test_user_123?start_date=invalid-date",
            headers=headers
        )
        assert response.status_code == 422  # Validation error
    
    def test_days_back_validation(self):
        """Test days_back parameter validation"""
        api_key = "dev-api-key-change-in-production"
        headers = {"X-API-Key": api_key}
        
        # Test with days_back too high
        response = client.get(
            "/api/v1/data/recovery/test_user_123?days=100",
            headers=headers
        )
        assert response.status_code == 422  # Should reject days > 30
        
        # Test with days_back too low
        response = client.get(
            "/api/v1/data/recovery/test_user_123?days=0",
            headers=headers
        )
        assert response.status_code == 422  # Should reject days < 1


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_oauth_flow_simulation(self):
        """Test simulated complete OAuth flow"""
        oauth_service = WhoopOAuthService()
        user_id = "integration_test_user"
        
        # Step 1: Initiate OAuth flow
        auth_response = await oauth_service.initiate_oauth_flow(user_id)
        assert auth_response.authorization_url is not None
        assert auth_response.state is not None
        
        # Step 2: Simulate user authorization (would happen in browser)
        # We can't actually complete this without real WHOOP credentials
        # but we can test the structure
        
        # Step 3: Test token validation logic
        is_valid = await oauth_service.is_token_valid(user_id)
        assert is_valid is False  # No token stored yet
        
        # Step 4: Test connection status
        status = await oauth_service.get_connection_status(user_id)
        assert status["connected"] is False
        assert status["status"] == "not_found"
    
    def test_api_error_handling(self):
        """Test API error handling scenarios"""
        api_key = "dev-api-key-change-in-production"
        headers = {"X-API-Key": api_key}
        
        # Test with non-existent user (should handle gracefully)
        response = client.get("/api/v1/auth/status/nonexistent_user_12345", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["connection_status"]["connected"] is False


# Test configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database for testing without real database calls"""
    return Mock()


@pytest.fixture
def sample_whoop_data():
    """Sample WHOOP data for testing"""
    return {
        "user_id": "test_user_123",
        "recovery": [
            {
                "recovery_score": 75.5,
                "hrv_rmssd": 42.3,
                "resting_heart_rate": 52,
                "date": "2024-01-15"
            }
        ],
        "sleep": [
            {
                "sleep_score": 82.0,
                "duration_seconds": 28800,
                "efficiency_percentage": 87.5,
                "date": "2024-01-15"
            }
        ],
        "workouts": [
            {
                "strain": 15.2,
                "duration_seconds": 3600,
                "average_heart_rate": 156,
                "date": "2024-01-15"
            }
        ]
    }


# Performance tests
class TestPerformance:
    """Test performance characteristics"""
    
    def test_rate_limit_manager_performance(self):
        """Test rate limit manager doesn't cause delays in normal usage"""
        rate_limiter = RateLimitManager()
        
        start_time = datetime.utcnow()
        status = rate_limiter.get_rate_limit_status()
        end_time = datetime.utcnow()
        
        # Should be very fast
        duration = (end_time - start_time).total_seconds()
        assert duration < 0.1  # Less than 100ms
        
        assert isinstance(status, dict)
        assert "minute_used" in status


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main(["-v", __file__])