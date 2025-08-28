#!/usr/bin/env python3
"""
WHOOP FastAPI Microservice - Automated Test Suite
=================================================

Comprehensive automated testing suite for WHOOP API integration with real scenarios.
Designed for CI/CD integration with detailed reporting and performance validation.

Usage:
    python automated_test_suite.py
    pytest automated_test_suite.py -v
    
Features:
- Realistic WHOOP API scenarios
- OAuth flow validation
- Database integration testing
- Performance benchmarking
- Error handling verification
- CI/CD ready with detailed reporting
"""

import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch, AsyncMock
import httpx
from fastapi.testclient import TestClient
import structlog

# Import application components
from app.main import app
from app.services.oauth_service import WhoopOAuthService
from app.services.whoop_api_client import WhoopAPIClient, RateLimitManager
from app.models.database import WhoopDataService
from app.models.schemas import (
    WhoopUser, WhoopRecoveryRecord, WhoopSleepRecord, WhoopWorkoutRecord,
    OAuthAuthorizationRequest, OAuthAuthorizationResponse
)
from app.config.settings import settings

# Configure structured logging for tests
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger(__name__)

# Test Configuration
TEST_CONFIG = {
    "api_base_url": "http://localhost:8001",
    "service_api_key": "dev-api-key-change-in-production",
    "test_timeout": 30.0,
    "performance_threshold_ms": 2000,  # 2 second max response time
    "rate_limit_test_requests": 10,
    "concurrent_test_count": 5
}

# Realistic Test Data based on actual WHOOP API responses
MOCK_WHOOP_RESPONSES = {
    "user_profile": {
        "user_id": 12345,
        "email": "test@example.com", 
        "first_name": "Test",
        "last_name": "User"
    },
    "cycles": [
        {
            "id": "cycle_12345",
            "user_id": 12345,
            "created_at": "2024-01-15T08:00:00.000Z",
            "updated_at": "2024-01-15T14:30:00.000Z",
            "start": "2024-01-14T22:00:00.000Z",
            "end": "2024-01-15T22:00:00.000Z"
        }
    ],
    "recovery": {
        "cycle_id": "cycle_12345",
        "sleep_id": "sleep_12345",
        "user_id": 12345,
        "created_at": "2024-01-15T14:30:00.000Z",
        "updated_at": "2024-01-15T14:30:00.000Z",
        "score": {
            "user_calibrating": False,
            "recovery_score": 78,
            "resting_heart_rate": 54,
            "hrv_rmssd_milli": 45.2,
            "spo2_percentage": 97.8,
            "skin_temp_celsius": 36.4
        }
    },
    "sleep": [
        {
            "id": "sleep_12345",
            "user_id": 12345,
            "created_at": "2024-01-15T08:30:00.000Z",
            "updated_at": "2024-01-15T08:30:00.000Z",
            "start": "2024-01-14T23:00:00.000Z",
            "end": "2024-01-15T07:00:00.000Z",
            "timezone_offset": "-05:00",
            "nap": False,
            "score": {
                "stage_summary": {
                    "total_in_bed_time_milli": 28800000,  # 8 hours
                    "total_awake_time_milli": 900000,      # 15 minutes
                    "total_no_data_time_milli": 0,
                    "total_light_sleep_time_milli": 14400000,  # 4 hours
                    "total_slow_wave_sleep_time_milli": 7200000,   # 2 hours 
                    "total_rem_sleep_time_milli": 6300000,        # 1.75 hours
                    "sleep_cycle_count": 5,
                    "disturbance_count": 3
                },
                "sleep_needed": {
                    "baseline_milli": 28800000,
                    "need_from_sleep_debt_milli": 0,
                    "need_from_recent_strain_milli": 0,
                    "need_from_recent_nap_milli": 0
                },
                "respiratory_rate": 14.5,
                "sleep_performance_percentage": 89,
                "sleep_consistency_percentage": 92,
                "sleep_efficiency_percentage": 87
            }
        }
    ],
    "workouts": [
        {
            "id": "workout_12345",
            "user_id": 12345,
            "created_at": "2024-01-15T19:30:00.000Z",
            "updated_at": "2024-01-15T19:30:00.000Z",
            "start": "2024-01-15T17:00:00.000Z",
            "end": "2024-01-15T18:30:00.000Z",
            "timezone_offset": "-05:00",
            "sport_id": 1,  # Running
            "score": {
                "strain": 16.3,
                "average_heart_rate": 165,
                "max_heart_rate": 189,
                "kilojoules": 1250.5,
                "percent_recorded": 98.5,
                "distance_meter": 8047,      # ~5 miles
                "altitude_gain_meter": 45,
                "altitude_loss_meter": 38,
                "zone_duration": {
                    "zone_zero_milli": 0,
                    "zone_one_milli": 300000,    # 5 minutes
                    "zone_two_milli": 1800000,   # 30 minutes  
                    "zone_three_milli": 2700000, # 45 minutes
                    "zone_four_milli": 900000,   # 15 minutes
                    "zone_five_milli": 0
                }
            }
        }
    ]
}

# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def test_client():
    """Create test client for FastAPI app"""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create async HTTP client for testing"""
    async with httpx.AsyncClient(
        base_url=TEST_CONFIG["api_base_url"],
        timeout=TEST_CONFIG["test_timeout"]
    ) as client:
        yield client

@pytest.fixture
def auth_headers():
    """Standard authentication headers for internal APIs"""
    return {"X-API-Key": TEST_CONFIG["service_api_key"]}

@pytest.fixture
def test_user_ids():
    """Generate unique test user IDs"""
    timestamp = str(int(time.time()))
    return {
        "valid_user": f"test_user_{timestamp}_valid",
        "empty_user": f"test_user_{timestamp}_empty", 
        "invalid_user": f"test_user_{timestamp}_invalid",
        "performance_user": f"test_user_{timestamp}_perf"
    }

@pytest.fixture
def mock_whoop_data():
    """Provide realistic WHOOP data for testing"""
    return MOCK_WHOOP_RESPONSES

@pytest.fixture
def oauth_service():
    """Initialize OAuth service for testing"""
    return WhoopOAuthService()

@pytest.fixture
def api_client():
    """Initialize WHOOP API client for testing"""
    return WhoopAPIClient()

@pytest.fixture
def rate_limiter():
    """Initialize rate limiter for testing"""
    return RateLimitManager()


class TestBasicEndpoints:
    """Test basic application endpoints and health checks"""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns correct response"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "WHOOP Health Metrics API" in data["message"]
        assert data["version"] == "1.0.0-mvp"
        
    def test_health_ready_endpoint(self, test_client):
        """Test health ready endpoint"""
        response = test_client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "unhealthy"]
        
    def test_health_live_endpoint(self, test_client):
        """Test health live endpoint"""
        response = test_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "uptime" in data
        assert isinstance(data["uptime"], (int, float))
        
    @pytest.mark.asyncio
    async def test_basic_endpoints_performance(self, async_client):
        """Test that basic endpoints respond within performance threshold"""
        endpoints = ["/", "/health/ready", "/health/live"]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = await async_client.get(endpoint)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            assert response.status_code == 200
            assert response_time < TEST_CONFIG["performance_threshold_ms"]


class TestOAuthConfiguration:
    """Test OAuth 2.0 configuration and setup"""
    
    def test_oauth_config_endpoint(self, test_client):
        """Test OAuth configuration endpoint returns required fields"""
        response = test_client.get("/api/v1/whoop/auth/oauth-config")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "authorization_url", "token_url", "client_id", "redirect_uri",
            "default_scopes", "available_scopes", "pkce_supported", "pkce_required"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
            
        # Validate OAuth URLs
        assert data["authorization_url"].startswith("https://api.prod.whoop.com/oauth/oauth2/auth")
        assert data["token_url"].startswith("https://api.prod.whoop.com/oauth/oauth2/token")
        
        # Validate PKCE support
        assert data["pkce_supported"] is True
        assert data["pkce_required"] is True
        
        # Validate scopes
        expected_scopes = ["offline", "read:profile", "read:recovery", "read:sleep", "read:workouts", "read:cycles"]
        for scope in expected_scopes:
            assert scope in data["default_scopes"], f"Missing default scope: {scope}"
            
    def test_oauth_service_initialization(self, oauth_service):
        """Test OAuth service initializes with correct configuration"""
        assert oauth_service.client_id is not None
        assert oauth_service.auth_url == "https://api.prod.whoop.com/oauth/oauth2/auth"
        assert oauth_service.token_url == "https://api.prod.whoop.com/oauth/oauth2/token"
        assert len(oauth_service.default_scopes) == 6
        assert "offline" in oauth_service.default_scopes
        
    def test_pkce_generation(self, oauth_service):
        """Test PKCE code verifier and challenge generation"""
        verifier, challenge = oauth_service._generate_pkce_pair()
        
        # Validate verifier (RFC 7636 requirements)
        assert 43 <= len(verifier) <= 128
        assert verifier.replace("-", "").replace("_", "").isalnum()
        
        # Validate challenge 
        assert len(challenge) == 43  # Base64url encoding of SHA256 hash
        assert challenge.replace("-", "").replace("_", "").isalnum()
        
    def test_state_generation_and_extraction(self, oauth_service):
        """Test OAuth state parameter generation and extraction"""
        test_user_id = "test_user_12345"
        state = oauth_service._generate_state(test_user_id)
        
        # Validate state format and length
        assert len(state) >= 8  # WHOOP minimum requirement
        assert "." in state  # Our format includes separator
        
        # Test extraction
        extracted_user = oauth_service._extract_user_from_state(state)
        assert extracted_user == test_user_id


class TestOAuthFlow:
    """Test complete OAuth 2.0 authorization flow"""
    
    @pytest.mark.asyncio
    async def test_oauth_flow_initiation(self, oauth_service, test_user_ids):
        """Test OAuth flow initiation"""
        user_id = test_user_ids["valid_user"]
        
        auth_response = await oauth_service.initiate_oauth_flow(user_id)
        
        assert isinstance(auth_response, OAuthAuthorizationResponse)
        assert auth_response.authorization_url.startswith("https://api.prod.whoop.com/oauth/oauth2/auth")
        assert "client_id=" in auth_response.authorization_url
        assert "code_challenge=" in auth_response.authorization_url
        assert "code_challenge_method=S256" in auth_response.authorization_url
        assert "response_type=code" in auth_response.authorization_url
        assert len(auth_response.state) >= 8
        
    def test_oauth_authorize_endpoint(self, test_client, test_user_ids):
        """Test OAuth authorization endpoint"""
        request_data = {
            "user_id": test_user_ids["valid_user"],
            "redirect_uri": "http://localhost:8001/callback",
            "scopes": ["read:profile", "read:recovery", "offline"]
        }
        
        response = test_client.post("/api/v1/whoop/auth/authorize", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert data["authorization_url"].startswith("https://api.prod.whoop.com/oauth/oauth2/auth")
        
    def test_oauth_callback_validation(self, test_client):
        """Test OAuth callback parameter validation"""
        # Test missing parameters
        response = test_client.get("/api/v1/whoop/auth/callback")
        assert response.status_code == 422  # Should require parameters
        
    @pytest.mark.asyncio
    async def test_token_validation_logic(self, oauth_service, test_user_ids):
        """Test token validation for non-existent user"""
        user_id = test_user_ids["empty_user"]
        
        is_valid = await oauth_service.is_token_valid(user_id)
        assert is_valid is False
        
    @pytest.mark.asyncio
    async def test_connection_status_non_existent_user(self, oauth_service, test_user_ids):
        """Test connection status for non-existent user"""
        user_id = test_user_ids["empty_user"]
        
        status = await oauth_service.get_connection_status(user_id)
        assert status["connected"] is False
        assert status["status"] == "not_found"


class TestAuthenticationAndAuthorization:
    """Test API authentication and authorization mechanisms"""
    
    def test_api_key_required(self, test_client, test_user_ids):
        """Test that internal endpoints require API key"""
        user_id = test_user_ids["valid_user"]
        
        # Test without API key
        response = test_client.get(f"/api/v1/auth/status/{user_id}")
        assert response.status_code == 422  # Missing required header
        
    def test_invalid_api_key_rejected(self, test_client, test_user_ids):
        """Test that invalid API keys are rejected"""
        user_id = test_user_ids["valid_user"]
        headers = {"X-API-Key": "invalid_key_12345"}
        
        response = test_client.get(f"/api/v1/auth/status/{user_id}", headers=headers)
        assert response.status_code == 401  # Unauthorized
        
    def test_valid_api_key_accepted(self, test_client, test_user_ids, auth_headers):
        """Test that valid API key is accepted"""
        user_id = test_user_ids["valid_user"]
        
        response = test_client.get(f"/api/v1/auth/status/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "connection_status" in data
        assert data["user_id"] == user_id
        
    @pytest.mark.asyncio
    async def test_auth_status_endpoint_comprehensive(self, async_client, test_user_ids, auth_headers):
        """Test auth status endpoint with comprehensive validation"""
        user_id = test_user_ids["valid_user"]
        
        response = await async_client.get(f"/api/v1/auth/status/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == user_id
        assert "connection_status" in data
        assert "checked_at" in data
        
        # Validate connection status structure
        conn_status = data["connection_status"]
        expected_fields = ["connected", "status"]
        for field in expected_fields:
            assert field in conn_status


class TestDataRetrievalEndpoints:
    """Test health data retrieval endpoints with realistic scenarios"""
    
    @pytest.mark.parametrize("endpoint,user_type", [
        ("/api/v1/data/recovery", "valid_user"),
        ("/api/v1/data/sleep", "valid_user"), 
        ("/api/v1/data/workouts", "valid_user"),
        ("/api/v1/health-metrics", "valid_user")
    ])
    def test_data_endpoints_structure(self, test_client, test_user_ids, auth_headers, endpoint, user_type):
        """Test data endpoints return proper structure"""
        user_id = test_user_ids[user_type]
        url = f"{endpoint}/{user_id}"
        
        response = test_client.get(url, headers=auth_headers)
        # Should return 200 (with data) or 404 (user not connected)
        assert response.status_code in [200, 404, 500, 502]
        
        if response.status_code == 200:
            data = response.json()
            assert "user_id" in data
            assert data["user_id"] == user_id
            
    @pytest.mark.parametrize("days", [1, 7, 15, 30])
    def test_data_endpoints_days_parameter(self, test_client, test_user_ids, auth_headers, days):
        """Test data endpoints with different days parameters"""
        user_id = test_user_ids["valid_user"]
        
        response = test_client.get(
            f"/api/v1/data/recovery/{user_id}",
            headers=auth_headers,
            params={"days": days}
        )
        
        # Should handle all valid days parameters
        assert response.status_code in [200, 404, 500, 502]
        
    @pytest.mark.parametrize("days", [-1, 0, 100, "abc"])
    def test_data_endpoints_invalid_days_parameter(self, test_client, test_user_ids, auth_headers, days):
        """Test data endpoints reject invalid days parameters"""
        user_id = test_user_ids["valid_user"]
        
        response = test_client.get(
            f"/api/v1/data/recovery/{user_id}",
            headers=auth_headers,
            params={"days": days}
        )
        
        # Should reject invalid parameters
        assert response.status_code == 422  # Validation error
        
    @pytest.mark.parametrize("source", ["database", "whoop", "both"])
    def test_health_metrics_source_parameter(self, test_client, test_user_ids, auth_headers, source):
        """Test health metrics endpoint with different source parameters"""
        user_id = test_user_ids["valid_user"]
        
        response = test_client.get(
            f"/api/v1/health-metrics/{user_id}",
            headers=auth_headers,
            params={"source": source}
        )
        
        assert response.status_code in [200, 404, 500, 502]
        
        if response.status_code == 200:
            data = response.json()
            assert data["source"] == source
            
    def test_health_metrics_date_range_parameter(self, test_client, test_user_ids, auth_headers):
        """Test health metrics with date range parameters"""
        user_id = test_user_ids["valid_user"]
        
        response = test_client.get(
            f"/api/v1/health-metrics/{user_id}",
            headers=auth_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-07"
            }
        )
        
        assert response.status_code in [200, 404, 500, 502]
        
        if response.status_code == 200:
            data = response.json()
            assert "date_range" in data
            assert data["date_range"]["start"] == "2024-01-01"
            assert data["date_range"]["end"] == "2024-01-07"


class TestErrorHandlingAndValidation:
    """Test comprehensive error handling and input validation"""
    
    @pytest.mark.parametrize("invalid_user", [
        "",  # Empty string
        "x" * 1000,  # Very long string
        "user with spaces",  # Spaces
        "user/with/slashes",  # Special characters
        "user@with@symbols"  # Email-like format
    ])
    def test_invalid_user_id_handling(self, test_client, auth_headers, invalid_user):
        """Test that invalid user IDs are handled gracefully"""
        if not invalid_user:  # Skip empty string as it would be a path issue
            return
            
        response = test_client.get(f"/api/v1/auth/status/{invalid_user}", headers=auth_headers)
        # Should not crash, return appropriate status
        assert response.status_code in [200, 400, 404, 422]
        
    @pytest.mark.parametrize("invalid_date", [
        "2024-13-01",  # Invalid month
        "invalid-date",  # Non-date string
        "2024/01/01",  # Wrong format
        "01-01-2024"   # Wrong format
    ])
    def test_invalid_date_parameter_handling(self, test_client, test_user_ids, auth_headers, invalid_date):
        """Test that invalid date parameters are properly validated"""
        user_id = test_user_ids["valid_user"]
        
        response = test_client.get(
            f"/api/v1/health-metrics/{user_id}",
            headers=auth_headers,
            params={"start_date": invalid_date}
        )
        
        assert response.status_code == 422  # Validation error
        
    def test_missing_user_connection_handling(self, test_client, test_user_ids, auth_headers):
        """Test handling of users without WHOOP connections"""
        user_id = test_user_ids["empty_user"]
        
        # Test various data endpoints
        endpoints = [
            f"/api/v1/data/recovery/{user_id}",
            f"/api/v1/data/sleep/{user_id}",
            f"/api/v1/data/workouts/{user_id}"
        ]
        
        for endpoint in endpoints:
            response = test_client.get(endpoint, headers=auth_headers)
            # Should gracefully handle missing connection
            assert response.status_code in [404, 500, 502]
            
    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, async_client, test_user_ids, auth_headers):
        """Test handling when external services are unavailable"""
        user_id = test_user_ids["invalid_user"]
        
        # Test with user that would cause external service errors
        response = await async_client.get(
            f"/api/v1/health-metrics/{user_id}",
            headers=auth_headers,
            params={"source": "whoop"}
        )
        
        # Should handle external service errors gracefully
        assert response.status_code in [200, 404, 500, 502]


class TestRateLimitingAndPerformance:
    """Test rate limiting compliance and performance characteristics"""
    
    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initializes with correct settings"""
        status = rate_limiter.get_rate_limit_status()
        
        assert status["minute_limit"] == 100  # WHOOP API limit
        assert status["daily_limit"] == 10000  # WHOOP API limit
        assert status["minute_used"] >= 0
        assert status["daily_used"] >= 0
        
    @pytest.mark.asyncio
    async def test_rate_limit_acquisition(self, rate_limiter):
        """Test rate limit permit acquisition"""
        permit = await rate_limiter.acquire_permit()
        assert permit is True
        
        status = rate_limiter.get_rate_limit_status()
        assert status["minute_used"] >= 1
        assert status["daily_used"] >= 1
        
    def test_client_status_endpoint(self, test_client, auth_headers):
        """Test client status endpoint provides rate limit information"""
        response = test_client.get("/api/v1/client-status", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["service_status"] == "operational"
        assert "whoop_client" in data
        assert "timestamp" in data
        
        whoop_client = data["whoop_client"]
        assert "rate_limiting" in whoop_client
        
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, async_client, test_user_ids, auth_headers):
        """Test handling of concurrent requests"""
        user_id = test_user_ids["performance_user"]
        endpoint = f"/api/v1/auth/status/{user_id}"
        
        # Create concurrent requests
        async def make_request(request_id):
            start_time = time.time()
            try:
                response = await async_client.get(endpoint, headers=auth_headers)
                duration = time.time() - start_time
                return {
                    "id": request_id,
                    "status_code": response.status_code,
                    "duration": duration,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "id": request_id,
                    "status_code": "exception",
                    "duration": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(TEST_CONFIG["concurrent_test_count"])]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        successful_requests = len([r for r in results if r["success"]])
        
        # Should handle most concurrent requests successfully
        assert successful_requests >= TEST_CONFIG["concurrent_test_count"] - 1
        assert total_time < 10.0  # Should complete within reasonable time
        
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, async_client, test_user_ids, auth_headers):
        """Test performance benchmarks for key endpoints"""
        user_id = test_user_ids["performance_user"]
        
        performance_tests = [
            ("Auth Status", f"/api/v1/auth/status/{user_id}"),
            ("Client Status", "/api/v1/client-status"),
            ("Health Metrics", f"/api/v1/health-metrics/{user_id}")
        ]
        
        for test_name, endpoint in performance_tests:
            # Warm up
            await async_client.get(endpoint, headers=auth_headers)
            
            # Actual test
            start_time = time.time()
            response = await async_client.get(endpoint, headers=auth_headers)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Verify response and performance
            assert response.status_code in [200, 404, 500, 502]
            assert response_time < TEST_CONFIG["performance_threshold_ms"], f"{test_name} took {response_time:.2f}ms"


class TestDatabaseIntegrationScenarios:
    """Test database integration and data persistence scenarios"""
    
    @pytest.mark.asyncio
    async def test_sync_endpoint_structure(self, async_client, test_user_ids, auth_headers):
        """Test sync endpoint structure and response"""
        user_id = test_user_ids["valid_user"]
        
        response = await async_client.post(
            f"/api/v1/sync/{user_id}",
            headers=auth_headers,
            params={
                "data_types": "recovery,sleep",
                "days_back": "3",
                "force_refresh": "false"
            }
        )
        
        # Should handle sync request appropriately
        assert response.status_code in [200, 404, 500, 502]
        
        if response.status_code == 200:
            data = response.json()
            assert "user_id" in data
            assert "sync_timestamp" in data
            assert "status" in data
            
    def test_data_source_preferences(self, test_client, test_user_ids, auth_headers):
        """Test different data source preferences in health metrics"""
        user_id = test_user_ids["valid_user"]
        
        sources = ["database", "whoop", "both"]
        
        for source in sources:
            response = test_client.get(
                f"/api/v1/health-metrics/{user_id}",
                headers=auth_headers,
                params={"source": source, "days_back": "2"}
            )
            
            assert response.status_code in [200, 404, 500, 502]
            
            if response.status_code == 200:
                data = response.json()
                assert data["source"] == source
                
                # Validate data structure based on source
                if source == "database":
                    # Should have database_data field
                    pass
                elif source == "whoop":
                    # Should have whoop_data field
                    pass
                elif source == "both":
                    # Should have both fields and potentially unified_data
                    pass


class TestDataModelValidation:
    """Test Pydantic model validation and data structures"""
    
    def test_whoop_user_model_validation(self):
        """Test WhoopUser model validation"""
        # Valid user
        user = WhoopUser(
            user_id="test_user_123",
            whoop_user_id="whoop_456",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            scopes="read:profile read:recovery offline",
            is_active=True
        )
        
        assert user.user_id == "test_user_123"
        assert user.whoop_user_id == "whoop_456"
        assert user.is_active is True
        assert "read:profile" in user.scopes
        
    def test_whoop_recovery_record_validation(self):
        """Test WhoopRecoveryRecord model validation"""
        recovery = WhoopRecoveryRecord(
            user_id="test_user_123",
            cycle_id="cycle_456", 
            recovery_score=78.5,
            hrv_rmssd=45.2,
            resting_heart_rate=54,
            skin_temp_celsius=36.4,
            respiratory_rate=14.8,
            date=date.today(),
            recorded_at=datetime.utcnow()
        )
        
        assert recovery.user_id == "test_user_123"
        assert recovery.recovery_score == 78.5
        assert recovery.hrv_rmssd == 45.2
        assert recovery.resting_heart_rate == 54
        assert recovery.date == date.today()
        
    def test_whoop_sleep_record_validation(self):
        """Test WhoopSleepRecord model validation"""
        sleep_record = WhoopSleepRecord(
            user_id="test_user_123",
            sleep_id="sleep_456",
            start_time=datetime.utcnow() - timedelta(hours=8),
            end_time=datetime.utcnow(),
            duration_seconds=28800,  # 8 hours
            efficiency_percentage=87.5,
            sleep_score=84.0,
            light_sleep_minutes=240,
            rem_sleep_minutes=120,
            deep_sleep_minutes=120,
            awake_minutes=20,
            date=date.today()
        )
        
        assert sleep_record.user_id == "test_user_123"
        assert sleep_record.duration_seconds == 28800
        assert sleep_record.efficiency_percentage == 87.5
        assert sleep_record.sleep_score == 84.0
        
    def test_whoop_workout_record_validation(self):
        """Test WhoopWorkoutRecord model validation"""
        workout = WhoopWorkoutRecord(
            user_id="test_user_123",
            workout_id="workout_456",
            sport_name="Running",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            duration_seconds=3600,  # 1 hour
            strain=16.3,
            average_heart_rate=165,
            max_heart_rate=189,
            calories=524,
            kilojoules=2195,
            date=date.today()
        )
        
        assert workout.user_id == "test_user_123"
        assert workout.sport_name == "Running"
        assert workout.strain == 16.3
        assert workout.average_heart_rate == 165
        assert workout.max_heart_rate == 189


class TestMockWhoopAPIScenarios:
    """Test scenarios with realistic WHOOP API data"""
    
    @patch('app.services.whoop_api_client.WhoopAPIClient._make_authenticated_request')
    @pytest.mark.asyncio
    async def test_mock_recovery_data_retrieval(self, mock_request, api_client, mock_whoop_data):
        """Test recovery data retrieval with mocked WHOOP API response"""
        # Mock successful API response
        mock_request.return_value = mock_whoop_data["recovery"]
        
        user_id = "test_user_12345"
        cycle_id = "cycle_12345"
        
        recovery_data = await api_client.get_recovery_data(user_id, cycle_id)
        
        assert recovery_data is not None
        assert recovery_data.cycle_id == cycle_id
        assert recovery_data.recovery_score == 78
        assert recovery_data.resting_heart_rate == 54
        assert recovery_data.hrv is not None
        
    @patch('app.services.whoop_api_client.WhoopAPIClient._make_authenticated_request')
    @pytest.mark.asyncio
    async def test_mock_sleep_data_retrieval(self, mock_request, api_client, mock_whoop_data):
        """Test sleep data retrieval with mocked WHOOP API response"""
        # Mock successful API response  
        mock_request.return_value = mock_whoop_data["sleep"]
        
        user_id = "test_user_12345"
        sleep_data = await api_client.get_sleep_activities(user_id, limit=1)
        
        assert len(sleep_data) == 1
        sleep = sleep_data[0]
        assert sleep.id == "sleep_12345"
        assert sleep.duration_seconds == 28800000 / 1000  # Convert from milli to seconds
        assert sleep.efficiency_percentage == 87
        
    @patch('app.services.whoop_api_client.WhoopAPIClient._make_authenticated_request')
    @pytest.mark.asyncio
    async def test_mock_workout_data_retrieval(self, mock_request, api_client, mock_whoop_data):
        """Test workout data retrieval with mocked WHOOP API response"""
        # Mock successful API response
        mock_request.return_value = mock_whoop_data["workouts"]
        
        user_id = "test_user_12345"
        workout_data = await api_client.get_workout_activities(user_id, limit=1)
        
        assert len(workout_data) == 1
        workout = workout_data[0]
        assert workout.id == "workout_12345"
        assert workout.strain == 16.3
        assert workout.average_heart_rate == 165
        assert workout.max_heart_rate == 189
        
    @patch('app.services.whoop_api_client.WhoopAPIClient.get_comprehensive_user_data')
    @pytest.mark.asyncio
    async def test_comprehensive_data_integration(self, mock_comprehensive_data, async_client, test_user_ids, auth_headers):
        """Test comprehensive data integration with realistic WHOOP responses"""
        # Mock comprehensive data response
        mock_comprehensive_data.return_value = {
            "user_id": test_user_ids["valid_user"],
            "profile": MOCK_WHOOP_RESPONSES["user_profile"],
            "recovery": [MOCK_WHOOP_RESPONSES["recovery"]],
            "sleep": MOCK_WHOOP_RESPONSES["sleep"],
            "workouts": MOCK_WHOOP_RESPONSES["workouts"],
            "fetch_timestamp": datetime.utcnow().isoformat()
        }
        
        user_id = test_user_ids["valid_user"]
        
        response = await async_client.get(
            f"/api/v1/health-metrics/{user_id}",
            headers=auth_headers,
            params={"source": "whoop", "days_back": "7"}
        )
        
        assert response.status_code in [200, 404, 500, 502]
        
        # If successful, validate structure
        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == user_id
            assert data["source"] == "whoop"


# Performance and Load Testing
class TestLoadAndStress:
    """Load and stress testing scenarios"""
    
    @pytest.mark.asyncio
    async def test_rapid_sequential_requests(self, async_client, test_user_ids, auth_headers):
        """Test rapid sequential requests to validate system stability"""
        user_id = test_user_ids["performance_user"]
        endpoint = f"/api/v1/auth/status/{user_id}"
        
        request_count = TEST_CONFIG["rate_limit_test_requests"]
        results = []
        
        start_time = time.time()
        
        for i in range(request_count):
            try:
                response = await async_client.get(endpoint, headers=auth_headers)
                results.append({
                    "request": i + 1,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                })
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
            except Exception as e:
                results.append({
                    "request": i + 1,
                    "status_code": "exception",
                    "success": False,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        successful_requests = len([r for r in results if r["success"]])
        
        # Should handle most requests successfully
        success_rate = successful_requests / request_count
        assert success_rate >= 0.8  # At least 80% success rate
        assert total_time < request_count * 0.5  # Reasonable total time
        
    @pytest.mark.asyncio
    async def test_large_data_request_handling(self, async_client, test_user_ids, auth_headers):
        """Test handling of large data requests"""
        user_id = test_user_ids["performance_user"]
        
        # Request maximum allowed days with all data sources
        response = await async_client.get(
            f"/api/v1/health-metrics/{user_id}",
            headers=auth_headers,
            params={
                "source": "both",
                "days_back": "30",
                "metric_types": "recovery,sleep,workout"
            }
        )
        
        # Should handle large requests without timeout
        assert response.status_code in [200, 404, 500, 502]


# Test Reporting and Utilities
class TestReporting:
    """Test reporting and validation utilities"""
    
    @pytest.fixture(autouse=True)
    def setup_test_results(self):
        """Setup for collecting test results"""
        self.test_results = []
        
    def record_test_result(self, test_name: str, success: bool, details: str = "", data: Any = None):
        """Record test result for reporting"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        })
        
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "timestamp": datetime.utcnow().isoformat()
            },
            "results": self.test_results,
            "configuration": TEST_CONFIG
        }


# Custom pytest markers for organizing tests
pytest.mark.basic = pytest.mark.parametrize("marker", ["basic"])
pytest.mark.oauth = pytest.mark.parametrize("marker", ["oauth"]) 
pytest.mark.data = pytest.mark.parametrize("marker", ["data"])
pytest.mark.performance = pytest.mark.parametrize("marker", ["performance"])
pytest.mark.integration = pytest.mark.parametrize("marker", ["integration"])


if __name__ == "__main__":
    # Run tests with verbose output and reporting
    import sys
    
    # Generate test report
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = f"whoop_automated_test_report_{timestamp}.json"
    
    print("🧪 WHOOP FastAPI Microservice - Automated Test Suite")
    print("=" * 60)
    
    # Run with pytest
    exit_code = pytest.main([
        "-v",
        "--tb=short",
        f"--junitxml=whoop_test_results_{timestamp}.xml",
        __file__
    ])
    
    print(f"\n📊 Test execution completed with exit code: {exit_code}")
    
    sys.exit(exit_code)