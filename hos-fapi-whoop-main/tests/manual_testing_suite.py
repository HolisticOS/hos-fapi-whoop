#!/usr/bin/env python3
"""
WHOOP FastAPI Microservice - Manual Testing Suite
=================================================

This comprehensive manual testing suite provides interactive testing capabilities
for all WHOOP API endpoints with realistic test scenarios and data.

Usage:
    python manual_testing_suite.py
    
Features:
- Interactive menu-driven testing
- Real WHOOP API integration scenarios
- OAuth flow testing with PKCE
- Rate limiting compliance testing
- Database integration testing
- Error handling validation
- Performance testing capabilities
"""

import asyncio
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import httpx
from urllib.parse import urlparse, parse_qs
import secrets
import base64
import hashlib

# Configuration
API_BASE_URL = "http://localhost:8001"
SERVICE_API_KEY = "dev-api-key-change-in-production"  # Change for production

# Test Data
TEST_USERS = {
    "user_with_data": "test_user_12345",
    "user_empty": "empty_user_67890", 
    "user_invalid_token": "invalid_token_user",
    "user_performance": "perf_test_user",
    "user_new": "new_user_" + str(int(time.time()))
}

REALISTIC_WHOOP_DATA = {
    "recovery": {
        "recovery_score": 78.5,
        "hrv_rmssd": 45.2,
        "resting_heart_rate": 54,
        "skin_temp_celsius": 36.4,
        "respiratory_rate": 14.8
    },
    "sleep": {
        "sleep_score": 84.0,
        "duration_seconds": 28800,  # 8 hours
        "efficiency_percentage": 89.2,
        "light_sleep_minutes": 240,
        "rem_sleep_minutes": 120,
        "deep_sleep_minutes": 120,
        "awake_minutes": 20
    },
    "workout": {
        "strain": 16.3,
        "duration_seconds": 3600,  # 1 hour
        "average_heart_rate": 165,
        "max_heart_rate": 189,
        "calories": 524,
        "sport_name": "Running"
    }
}


class WhoopTestingClient:
    """Enhanced testing client for WHOOP API with comprehensive testing capabilities"""
    
    def __init__(self, base_url: str = API_BASE_URL, api_key: str = SERVICE_API_KEY):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        self.oauth_states = {}  # Store OAuth states for testing
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    def print_section(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print('='*60)
    
    def print_test_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Print formatted test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_data and isinstance(response_data, dict):
            print(f"   Response: {json.dumps(response_data, indent=2, default=str)[:200]}...")
        
        # Store result for summary
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def test_basic_endpoints(self):
        """Test basic application endpoints"""
        self.print_section("Basic Endpoints Testing")
        
        # Test root endpoint
        try:
            response = await self.session.get(f"{self.base_url}/")
            success = response.status_code == 200 and "WHOOP" in response.text
            self.print_test_result(
                "Root Endpoint", 
                success, 
                f"Status: {response.status_code}", 
                response.json() if success else None
            )
        except Exception as e:
            self.print_test_result("Root Endpoint", False, f"Exception: {str(e)}")
        
        # Test health endpoints
        for health_endpoint in ["/health/ready", "/health/live"]:
            try:
                response = await self.session.get(f"{self.base_url}{health_endpoint}")
                success = response.status_code == 200
                data = response.json() if success else None
                self.print_test_result(
                    f"Health Check {health_endpoint}", 
                    success, 
                    f"Status: {response.status_code}, Health: {data.get('status') if data else 'unknown'}"
                )
            except Exception as e:
                self.print_test_result(f"Health Check {health_endpoint}", False, f"Exception: {str(e)}")
    
    async def test_oauth_configuration(self):
        """Test OAuth configuration endpoint"""
        self.print_section("OAuth Configuration Testing")
        
        try:
            response = await self.session.get(f"{self.base_url}/api/v1/whoop/auth/oauth-config")
            success = response.status_code == 200
            data = response.json() if success else None
            
            if success:
                required_fields = ["authorization_url", "client_id", "redirect_uri", "default_scopes", "pkce_supported"]
                all_fields_present = all(field in data for field in required_fields)
                success = success and all_fields_present
                
                self.print_test_result(
                    "OAuth Configuration",
                    success,
                    f"PKCE: {data.get('pkce_supported')}, Scopes: {len(data.get('default_scopes', []))}",
                    data
                )
            else:
                self.print_test_result("OAuth Configuration", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.print_test_result("OAuth Configuration", False, f"Exception: {str(e)}")
    
    async def test_oauth_flow_simulation(self):
        """Test complete OAuth flow simulation with PKCE"""
        self.print_section("OAuth Flow Simulation (PKCE)")
        
        user_id = TEST_USERS["user_new"]
        
        # Step 1: Test OAuth authorization initiation
        try:
            auth_request = {
                "user_id": user_id,
                "redirect_uri": "http://localhost:8001/api/v1/whoop/auth/callback",
                "scopes": ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"]
            }
            
            response = await self.session.post(
                f"{self.base_url}/api/v1/whoop/auth/authorize",
                json=auth_request
            )
            
            success = response.status_code == 200
            data = response.json() if success else None
            
            if success:
                # Validate OAuth URL structure
                auth_url = data.get("authorization_url", "")
                state = data.get("state", "")
                
                # Store state for callback testing
                self.oauth_states[user_id] = state
                
                # Validate URL contains required OAuth parameters
                url_valid = all(param in auth_url for param in [
                    "client_id=", "code_challenge=", "code_challenge_method=S256", 
                    "response_type=code", "state="
                ])
                
                self.print_test_result(
                    "OAuth Authorization Initiation",
                    success and url_valid,
                    f"URL valid: {url_valid}, State length: {len(state)}",
                    {"authorization_url": auth_url[:100] + "...", "state": state}
                )
                
                # Step 2: Simulate callback (without actual WHOOP authorization)
                await self._test_oauth_callback_structure(user_id, state)
            else:
                self.print_test_result("OAuth Authorization Initiation", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.print_test_result("OAuth Authorization Initiation", False, f"Exception: {str(e)}")
    
    async def _test_oauth_callback_structure(self, user_id: str, state: str):
        """Test OAuth callback endpoint structure (without real authorization code)"""
        try:
            # Test callback with missing parameters
            response = await self.session.get(f"{self.base_url}/api/v1/whoop/auth/callback")
            missing_params_handled = response.status_code == 422  # Should require parameters
            
            self.print_test_result(
                "OAuth Callback Parameter Validation",
                missing_params_handled,
                f"Missing params status: {response.status_code}"
            )
            
            # Test callback with invalid code (simulated)
            response = await self.session.get(
                f"{self.base_url}/api/v1/whoop/auth/callback?code=invalid_test_code&state={state}&user_id={user_id}"
            )
            
            # Should handle invalid code gracefully
            invalid_code_handled = response.status_code in [400, 500]  # Expected error responses
            
            self.print_test_result(
                "OAuth Callback Invalid Code Handling",
                invalid_code_handled,
                f"Invalid code status: {response.status_code}"
            )
            
        except Exception as e:
            self.print_test_result("OAuth Callback Structure Test", False, f"Exception: {str(e)}")
    
    async def test_authentication_endpoints(self):
        """Test authentication and connection status endpoints"""
        self.print_section("Authentication Endpoints Testing")
        
        headers = {"X-API-Key": self.api_key}
        
        # Test connection status for various user types
        for user_type, user_id in TEST_USERS.items():
            try:
                response = await self.session.get(
                    f"{self.base_url}/api/v1/auth/status/{user_id}",
                    headers=headers
                )
                
                success = response.status_code == 200
                data = response.json() if success else None
                
                if success and data:
                    connection_status = data.get("connection_status", {})
                    connected = connection_status.get("connected", False)
                    status = connection_status.get("status", "unknown")
                    
                    self.print_test_result(
                        f"Connection Status - {user_type}",
                        success,
                        f"Connected: {connected}, Status: {status}",
                        connection_status
                    )
                else:
                    self.print_test_result(f"Connection Status - {user_type}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.print_test_result(f"Connection Status - {user_type}", False, f"Exception: {str(e)}")
        
        # Test API key authentication
        await self._test_api_key_authentication()
    
    async def _test_api_key_authentication(self):
        """Test API key authentication requirements"""
        try:
            # Test without API key
            response = await self.session.get(
                f"{self.base_url}/api/v1/auth/status/{TEST_USERS['user_new']}"
            )
            no_key_rejected = response.status_code == 422  # Missing required header
            
            self.print_test_result(
                "API Key Required - No Key",
                no_key_rejected,
                f"No key status: {response.status_code}"
            )
            
            # Test with invalid API key
            response = await self.session.get(
                f"{self.base_url}/api/v1/auth/status/{TEST_USERS['user_new']}",
                headers={"X-API-Key": "invalid_key_12345"}
            )
            invalid_key_rejected = response.status_code == 401
            
            self.print_test_result(
                "API Key Required - Invalid Key",
                invalid_key_rejected,
                f"Invalid key status: {response.status_code}"
            )
            
        except Exception as e:
            self.print_test_result("API Key Authentication", False, f"Exception: {str(e)}")
    
    async def test_data_retrieval_endpoints(self):
        """Test health data retrieval endpoints"""
        self.print_section("Data Retrieval Endpoints Testing")
        
        headers = {"X-API-Key": self.api_key}
        test_user = TEST_USERS["user_with_data"]
        
        # Test each data type endpoint
        data_endpoints = [
            ("Recovery Data", f"/api/v1/data/recovery/{test_user}"),
            ("Sleep Data", f"/api/v1/data/sleep/{test_user}"),  
            ("Workout Data", f"/api/v1/data/workouts/{test_user}"),
            ("Comprehensive Health Metrics", f"/api/v1/health-metrics/{test_user}")
        ]
        
        for endpoint_name, endpoint_url in data_endpoints:
            await self._test_data_endpoint(endpoint_name, endpoint_url, headers)
    
    async def _test_data_endpoint(self, endpoint_name: str, endpoint_url: str, headers: Dict[str, str]):
        """Test individual data endpoint with various parameters"""
        try:
            # Test basic endpoint
            response = await self.session.get(f"{self.base_url}{endpoint_url}", headers=headers)
            basic_success = response.status_code in [200, 404]  # 404 if user not connected
            data = response.json() if response.status_code == 200 else None
            
            self.print_test_result(
                f"{endpoint_name} - Basic Request",
                basic_success,
                f"Status: {response.status_code}",
                data
            )
            
            # Test with parameters
            if "health-metrics" in endpoint_url:
                await self._test_health_metrics_parameters(endpoint_url, headers)
            else:
                await self._test_data_endpoint_parameters(endpoint_url, headers)
                
        except Exception as e:
            self.print_test_result(f"{endpoint_name} - Basic Request", False, f"Exception: {str(e)}")
    
    async def _test_health_metrics_parameters(self, base_url: str, headers: Dict[str, str]):
        """Test health metrics endpoint with various parameters"""
        test_params = [
            ("source=database", {"source": "database"}),
            ("source=whoop", {"source": "whoop"}), 
            ("source=both", {"source": "both"}),
            ("days_back=3", {"days_back": "3"}),
            ("date range", {"start_date": "2024-01-01", "end_date": "2024-01-07"}),
            ("metric_types", {"metric_types": "recovery,sleep"})
        ]
        
        for param_name, params in test_params:
            try:
                response = await self.session.get(
                    f"{self.base_url}{base_url}",
                    headers=headers,
                    params=params
                )
                success = response.status_code in [200, 404]
                self.print_test_result(
                    f"Health Metrics - {param_name}",
                    success,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                self.print_test_result(f"Health Metrics - {param_name}", False, f"Exception: {str(e)}")
    
    async def _test_data_endpoint_parameters(self, base_url: str, headers: Dict[str, str]):
        """Test data endpoint with days parameter"""
        for days in [1, 7, 15, 30]:
            try:
                response = await self.session.get(
                    f"{self.base_url}{base_url}",
                    headers=headers,
                    params={"days": str(days)}
                )
                success = response.status_code in [200, 404]
                self.print_test_result(
                    f"Data Endpoint - {days} days",
                    success,
                    f"Status: {response.status_code}, Days: {days}"
                )
            except Exception as e:
                self.print_test_result(f"Data Endpoint - {days} days", False, f"Exception: {str(e)}")
    
    async def test_error_handling_scenarios(self):
        """Test comprehensive error handling scenarios"""
        self.print_section("Error Handling Scenarios")
        
        headers = {"X-API-Key": self.api_key}
        
        # Test invalid user IDs
        invalid_users = ["", "x"*1000, "user with spaces", "user/with/slashes", None]
        
        for invalid_user in invalid_users:
            if invalid_user is None:
                continue
                
            try:
                response = await self.session.get(
                    f"{self.base_url}/api/v1/auth/status/{invalid_user}",
                    headers=headers
                )
                # Should handle gracefully without crashing
                handled = response.status_code in [200, 400, 404, 422]
                self.print_test_result(
                    f"Invalid User ID: '{invalid_user[:20]}{'...' if len(str(invalid_user)) > 20 else ''}'",
                    handled,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                # Should not crash with unhandled exceptions
                self.print_test_result(f"Invalid User ID Exception", False, f"Unhandled: {str(e)}")
        
        # Test parameter validation
        await self._test_parameter_validation(headers)
    
    async def _test_parameter_validation(self, headers: Dict[str, str]):
        """Test parameter validation edge cases"""
        test_user = TEST_USERS["user_with_data"]
        
        # Invalid date formats
        invalid_dates = ["2024-13-01", "invalid-date", "2024/01/01", "01-01-2024"]
        
        for invalid_date in invalid_dates:
            try:
                response = await self.session.get(
                    f"{self.base_url}/api/v1/health-metrics/{test_user}",
                    headers=headers,
                    params={"start_date": invalid_date}
                )
                # Should return validation error
                validation_error = response.status_code == 422
                self.print_test_result(
                    f"Invalid Date Format: {invalid_date}",
                    validation_error,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                self.print_test_result(f"Date Validation Exception", False, f"Exception: {str(e)}")
        
        # Invalid numeric parameters
        invalid_days = [-1, 0, 100, "abc", 999999]
        
        for invalid_day in invalid_days:
            try:
                response = await self.session.get(
                    f"{self.base_url}/api/v1/data/recovery/{test_user}",
                    headers=headers,
                    params={"days": str(invalid_day)}
                )
                # Should handle invalid numeric parameters
                handled = response.status_code in [200, 422, 404]
                self.print_test_result(
                    f"Invalid Days Parameter: {invalid_day}",
                    handled,
                    f"Status: {response.status_code}"
                )
            except Exception as e:
                self.print_test_result(f"Days Validation Exception", False, f"Exception: {str(e)}")
    
    async def test_rate_limiting_compliance(self):
        """Test rate limiting compliance and behavior"""
        self.print_section("Rate Limiting Compliance Testing")
        
        headers = {"X-API-Key": self.api_key}
        
        # Test client status endpoint for rate limit info
        try:
            response = await self.session.get(f"{self.base_url}/api/v1/client-status", headers=headers)
            success = response.status_code == 200
            data = response.json() if success else None
            
            if success and data:
                whoop_client = data.get("whoop_client", {})
                rate_limiting = whoop_client.get("rate_limiting", {})
                
                self.print_test_result(
                    "Client Status & Rate Limiting",
                    success,
                    f"Service: {data.get('service_status')}, Rate limits configured: {bool(rate_limiting)}",
                    rate_limiting
                )
            else:
                self.print_test_result("Client Status", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.print_test_result("Client Status", False, f"Exception: {str(e)}")
        
        # Test rapid successive requests (within limits)
        await self._test_rapid_requests(headers)
    
    async def _test_rapid_requests(self, headers: Dict[str, str]):
        """Test rapid successive requests to validate rate limiting"""
        test_user = TEST_USERS["user_performance"]
        endpoint = f"{self.base_url}/api/v1/auth/status/{test_user}"
        
        # Make 5 rapid requests
        start_time = time.time()
        responses = []
        
        for i in range(5):
            try:
                response = await self.session.get(endpoint, headers=headers)
                responses.append({
                    "request": i + 1,
                    "status": response.status_code,
                    "time": time.time() - start_time
                })
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.1)
            except Exception as e:
                responses.append({
                    "request": i + 1,
                    "status": "exception",
                    "error": str(e),
                    "time": time.time() - start_time
                })
        
        total_time = time.time() - start_time
        successful_requests = len([r for r in responses if isinstance(r.get("status"), int) and r["status"] == 200])
        
        # Rate limiting should allow reasonable number of requests
        rate_limiting_working = successful_requests >= 3  # Should allow at least 3 out of 5
        
        self.print_test_result(
            "Rapid Requests Test",
            rate_limiting_working,
            f"Successful: {successful_requests}/5 in {total_time:.2f}s",
            {"responses": responses}
        )
    
    async def test_performance_characteristics(self):
        """Test performance characteristics and response times"""
        self.print_section("Performance Characteristics Testing")
        
        headers = {"X-API-Key": self.api_key}
        test_user = TEST_USERS["user_performance"]
        
        # Test response times for different endpoints
        performance_tests = [
            ("Auth Status", f"/api/v1/auth/status/{test_user}"),
            ("Client Status", "/api/v1/client-status"),
            ("Health Metrics", f"/api/v1/health-metrics/{test_user}"),
            ("Recovery Data", f"/api/v1/data/recovery/{test_user}")
        ]
        
        for test_name, endpoint in performance_tests:
            await self._test_endpoint_performance(test_name, endpoint, headers)
    
    async def _test_endpoint_performance(self, test_name: str, endpoint: str, headers: Dict[str, str]):
        """Test individual endpoint performance"""
        response_times = []
        
        # Make 3 requests to get average response time
        for i in range(3):
            try:
                start_time = time.time()
                response = await self.session.get(f"{self.base_url}{endpoint}", headers=headers)
                response_time = time.time() - start_time
                
                if response.status_code in [200, 404]:  # Valid responses
                    response_times.append(response_time)
                
                await asyncio.sleep(0.5)  # Respectful delay between requests
                
            except Exception as e:
                self.print_test_result(f"{test_name} Performance", False, f"Exception: {str(e)}")
                return
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # Performance criteria: under 2 seconds is reasonable for health APIs
            performance_good = avg_time < 2.0 and max_time < 5.0
            
            self.print_test_result(
                f"{test_name} Performance",
                performance_good,
                f"Avg: {avg_time:.3f}s, Max: {max_time:.3f}s, Min: {min_time:.3f}s",
                {"response_times": response_times}
            )
    
    async def test_database_integration_scenarios(self):
        """Test database integration scenarios"""
        self.print_section("Database Integration Testing")
        
        headers = {"X-API-Key": self.api_key}
        
        # Test sync endpoint (if implemented)
        test_user = TEST_USERS["user_with_data"] 
        
        try:
            response = await self.session.post(
                f"{self.base_url}/api/v1/sync/{test_user}",
                headers=headers,
                params={"data_types": "recovery,sleep", "days_back": "3"}
            )
            
            sync_success = response.status_code in [200, 404, 502]  # Various valid responses
            data = response.json() if response.status_code == 200 else None
            
            self.print_test_result(
                "Data Sync Endpoint",
                sync_success,
                f"Status: {response.status_code}",
                data
            )
            
        except Exception as e:
            self.print_test_result("Data Sync Endpoint", False, f"Exception: {str(e)}")
        
        # Test data source preferences
        await self._test_data_source_preferences(test_user, headers)
    
    async def _test_data_source_preferences(self, user_id: str, headers: Dict[str, str]):
        """Test different data source preferences"""
        sources = ["database", "whoop", "both"]
        
        for source in sources:
            try:
                response = await self.session.get(
                    f"{self.base_url}/api/v1/health-metrics/{user_id}",
                    headers=headers,
                    params={"source": source, "days_back": "2"}
                )
                
                success = response.status_code in [200, 404, 502]
                data = response.json() if response.status_code == 200 else None
                
                source_info = ""
                if data and response.status_code == 200:
                    if "database_data" in data:
                        source_info += "DB "
                    if "whoop_data" in data:
                        source_info += "API "
                    if "unified_data" in data:
                        source_info += "Unified "
                
                self.print_test_result(
                    f"Data Source - {source}",
                    success,
                    f"Status: {response.status_code}, Sources: {source_info.strip()}"
                )
                
            except Exception as e:
                self.print_test_result(f"Data Source - {source}", False, f"Exception: {str(e)}")
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        self.print_section("Test Summary Report")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['details']}")
        
        print(f"\n🕐 Test completed at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        # Generate JSON report
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate,
                "timestamp": datetime.utcnow().isoformat()
            },
            "results": self.test_results
        }


class InteractiveTestRunner:
    """Interactive menu-driven test runner"""
    
    def __init__(self):
        self.client = None
        
    async def run(self):
        """Run interactive testing menu"""
        print("🧪 WHOOP FastAPI Microservice - Manual Testing Suite")
        print("=" * 60)
        
        async with WhoopTestingClient() as client:
            self.client = client
            await self.show_main_menu()
    
    async def show_main_menu(self):
        """Show main testing menu"""
        while True:
            print("\n📋 Testing Menu:")
            print("1.  🏃‍♂️ Run Complete Test Suite")
            print("2.  🔧 Test Basic Endpoints")
            print("3.  🔐 Test OAuth Configuration & Flow")
            print("4.  🔑 Test Authentication Endpoints")
            print("5.  📊 Test Data Retrieval Endpoints")
            print("6.  ⚠️  Test Error Handling")
            print("7.  ⚡ Test Rate Limiting & Performance")
            print("8.  💾 Test Database Integration")
            print("9.  📝 Generate Test Report")
            print("10. ⚙️  Configuration & Setup")
            print("11. 🚪 Exit")
            
            choice = input("\nSelect option (1-11): ").strip()
            
            try:
                if choice == "1":
                    await self.run_complete_suite()
                elif choice == "2":
                    await self.client.test_basic_endpoints()
                elif choice == "3":
                    await self.test_oauth_menu()
                elif choice == "4":
                    await self.client.test_authentication_endpoints()
                elif choice == "5":
                    await self.client.test_data_retrieval_endpoints()
                elif choice == "6":
                    await self.client.test_error_handling_scenarios()
                elif choice == "7":
                    await self.test_performance_menu()
                elif choice == "8":
                    await self.client.test_database_integration_scenarios()
                elif choice == "9":
                    self.generate_test_report()
                elif choice == "10":
                    await self.configuration_menu()
                elif choice == "11":
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n\n⏹️  Test interrupted by user.")
                continue
            except Exception as e:
                print(f"\n❌ Error during testing: {str(e)}")
                continue
    
    async def run_complete_suite(self):
        """Run complete test suite"""
        print("\n🚀 Running Complete Test Suite...")
        print("This may take several minutes. Press Ctrl+C to interrupt.")
        
        start_time = time.time()
        
        await self.client.test_basic_endpoints()
        await self.client.test_oauth_configuration()
        await self.client.test_oauth_flow_simulation()
        await self.client.test_authentication_endpoints()
        await self.client.test_data_retrieval_endpoints()
        await self.client.test_error_handling_scenarios()
        await self.client.test_rate_limiting_compliance()
        await self.client.test_performance_characteristics()
        await self.client.test_database_integration_scenarios()
        
        total_time = time.time() - start_time
        
        print(f"\n⏱️  Complete test suite finished in {total_time:.1f} seconds")
        summary = self.client.print_test_summary()
        
        return summary
    
    async def test_oauth_menu(self):
        """OAuth-specific testing menu"""
        while True:
            print("\n🔐 OAuth Testing Menu:")
            print("1. Test OAuth Configuration")
            print("2. Test OAuth Flow Simulation")
            print("3. Test OAuth State Management")
            print("4. Test OAuth Error Scenarios")
            print("5. Back to Main Menu")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                await self.client.test_oauth_configuration()
            elif choice == "2":
                await self.client.test_oauth_flow_simulation()
            elif choice == "3":
                await self.test_oauth_state_management()
            elif choice == "4":
                await self.test_oauth_error_scenarios()
            elif choice == "5":
                break
            else:
                print("❌ Invalid option. Please try again.")
    
    async def test_oauth_state_management(self):
        """Test OAuth state parameter management"""
        print("\n🔒 Testing OAuth State Management...")
        
        # Test multiple simultaneous OAuth flows
        users = [TEST_USERS["user_new"] + f"_{i}" for i in range(3)]
        states = {}
        
        for user in users:
            auth_request = {
                "user_id": user,
                "redirect_uri": "http://localhost:8001/api/v1/whoop/auth/callback",
                "scopes": ["read:profile", "offline"]
            }
            
            try:
                response = await self.client.session.post(
                    f"{self.client.base_url}/api/v1/whoop/auth/authorize",
                    json=auth_request
                )
                
                if response.status_code == 200:
                    data = response.json()
                    state = data.get("state")
                    states[user] = state
                    
                    self.client.print_test_result(
                        f"OAuth State Generation - {user}",
                        True,
                        f"State: {state[:20]}..."
                    )
                    
            except Exception as e:
                self.client.print_test_result(f"OAuth State Generation - {user}", False, f"Exception: {str(e)}")
        
        # Verify all states are unique
        unique_states = len(set(states.values())) == len(states)
        self.client.print_test_result(
            "OAuth State Uniqueness",
            unique_states,
            f"Generated {len(states)} unique states: {unique_states}"
        )
    
    async def test_oauth_error_scenarios(self):
        """Test OAuth error scenarios"""
        print("\n⚠️  Testing OAuth Error Scenarios...")
        
        # Test invalid redirect URI
        invalid_request = {
            "user_id": "test_user",
            "redirect_uri": "invalid-uri",
            "scopes": ["read:profile"]
        }
        
        try:
            response = await self.client.session.post(
                f"{self.client.base_url}/api/v1/whoop/auth/authorize",
                json=invalid_request
            )
            
            # Should handle invalid URI gracefully
            handled = response.status_code in [400, 422, 500]
            self.client.print_test_result(
                "Invalid Redirect URI",
                handled,
                f"Status: {response.status_code}"
            )
            
        except Exception as e:
            self.client.print_test_result("Invalid Redirect URI", False, f"Exception: {str(e)}")
    
    async def test_performance_menu(self):
        """Performance testing menu"""
        while True:
            print("\n⚡ Performance Testing Menu:")
            print("1. Test Response Times")
            print("2. Test Rate Limiting")
            print("3. Test Concurrent Requests")
            print("4. Test Large Data Requests")
            print("5. Back to Main Menu")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                await self.client.test_performance_characteristics()
            elif choice == "2":
                await self.client.test_rate_limiting_compliance()
            elif choice == "3":
                await self.test_concurrent_requests()
            elif choice == "4":
                await self.test_large_data_requests()
            elif choice == "5":
                break
            else:
                print("❌ Invalid option. Please try again.")
    
    async def test_concurrent_requests(self):
        """Test concurrent request handling"""
        print("\n🔄 Testing Concurrent Request Handling...")
        
        headers = {"X-API-Key": self.client.api_key}
        endpoint = f"{self.client.base_url}/api/v1/client-status"
        
        # Create 5 concurrent requests
        async def make_request(request_id):
            try:
                start = time.time()
                response = await self.client.session.get(endpoint, headers=headers)
                duration = time.time() - start
                return {
                    "id": request_id,
                    "status": response.status_code,
                    "duration": duration,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "id": request_id,
                    "status": "exception",
                    "duration": 0,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        successful_requests = len([r for r in results if r["success"]])
        avg_duration = sum(r["duration"] for r in results if r["duration"] > 0) / len(results)
        
        concurrent_handling_good = successful_requests >= 4  # At least 4 out of 5 should succeed
        
        self.client.print_test_result(
            "Concurrent Request Handling",
            concurrent_handling_good,
            f"Successful: {successful_requests}/5, Avg time: {avg_duration:.3f}s, Total: {total_time:.3f}s",
            results
        )
    
    async def test_large_data_requests(self):
        """Test large data request handling"""
        print("\n📊 Testing Large Data Request Handling...")
        
        headers = {"X-API-Key": self.client.api_key}
        test_user = TEST_USERS["user_performance"]
        
        # Test with maximum allowed days
        try:
            start_time = time.time()
            response = await self.client.session.get(
                f"{self.client.base_url}/api/v1/health-metrics/{test_user}",
                headers=headers,
                params={"days_back": "30", "source": "both"}
            )
            duration = time.time() - start_time
            
            # Should handle large requests gracefully
            large_request_handled = response.status_code in [200, 404, 502]  # Various valid responses
            reasonable_time = duration < 10.0  # Should complete within 10 seconds
            
            self.client.print_test_result(
                "Large Data Request (30 days, both sources)",
                large_request_handled and reasonable_time,
                f"Status: {response.status_code}, Duration: {duration:.3f}s"
            )
            
        except Exception as e:
            self.client.print_test_result("Large Data Request", False, f"Exception: {str(e)}")
    
    async def configuration_menu(self):
        """Configuration and setup menu"""
        while True:
            print("\n⚙️  Configuration Menu:")
            print("1. Test API Connection")
            print("2. Display Current Configuration")
            print("3. Test Environment Variables")
            print("4. Validate Test Data")
            print("5. Back to Main Menu")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                await self.test_api_connection()
            elif choice == "2":
                self.display_configuration()
            elif choice == "3":
                await self.test_environment_variables()
            elif choice == "4":
                self.validate_test_data()
            elif choice == "5":
                break
            else:
                print("❌ Invalid option. Please try again.")
    
    async def test_api_connection(self):
        """Test basic API connection"""
        print("\n🔗 Testing API Connection...")
        
        try:
            response = await self.client.session.get(f"{self.client.base_url}/")
            success = response.status_code == 200
            
            self.client.print_test_result(
                "API Connection",
                success,
                f"URL: {self.client.base_url}, Status: {response.status_code}"
            )
            
            if success:
                data = response.json()
                print(f"   API Version: {data.get('version', 'unknown')}")
                print(f"   Message: {data.get('message', 'none')}")
                
        except Exception as e:
            self.client.print_test_result("API Connection", False, f"Exception: {str(e)}")
    
    def display_configuration(self):
        """Display current configuration"""
        print("\n📋 Current Configuration:")
        print(f"   API Base URL: {self.client.base_url}")
        print(f"   Service API Key: {'*' * (len(self.client.api_key) - 4) + self.client.api_key[-4:] if self.client.api_key else 'Not set'}")
        print(f"   Test Users: {len(TEST_USERS)} configured")
        print(f"   Timeout: {self.client.session.timeout}")
    
    async def test_environment_variables(self):
        """Test environment variable configuration"""
        print("\n🌍 Testing Environment Variables...")
        
        try:
            response = await self.client.session.get(f"{self.client.base_url}/api/v1/whoop/auth/oauth-config")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if important config is present
                client_id_set = bool(data.get("client_id"))
                redirect_uri_set = bool(data.get("redirect_uri"))
                
                self.client.print_test_result(
                    "Environment Variables Check",
                    client_id_set and redirect_uri_set,
                    f"Client ID: {'✅' if client_id_set else '❌'}, Redirect URI: {'✅' if redirect_uri_set else '❌'}"
                )
            else:
                self.client.print_test_result(
                    "Environment Variables Check",
                    False,
                    f"Could not retrieve config, status: {response.status_code}"
                )
                
        except Exception as e:
            self.client.print_test_result("Environment Variables Check", False, f"Exception: {str(e)}")
    
    def validate_test_data(self):
        """Validate test data configuration"""
        print("\n✅ Validating Test Data...")
        
        # Check test users
        users_valid = len(TEST_USERS) > 0 and all(isinstance(user_id, str) and len(user_id) > 0 for user_id in TEST_USERS.values())
        
        print(f"   Test Users: {'✅' if users_valid else '❌'} ({len(TEST_USERS)} configured)")
        
        # Check realistic data
        data_valid = all(
            isinstance(REALISTIC_WHOOP_DATA[key], dict) and len(REALISTIC_WHOOP_DATA[key]) > 0 
            for key in ["recovery", "sleep", "workout"]
        )
        
        print(f"   Realistic Data: {'✅' if data_valid else '❌'} (3 categories configured)")
        
        if users_valid and data_valid:
            print("   🎉 All test data validation passed!")
        else:
            print("   ⚠️  Some test data validation failed!")
    
    def generate_test_report(self):
        """Generate and display test report"""
        if not self.client.test_results:
            print("\n📝 No test results available. Run some tests first!")
            return
        
        print("\n📊 Generating Test Report...")
        
        summary = self.client.print_test_summary()
        
        # Save to file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"whoop_test_report_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            print(f"\n💾 Test report saved to: {filename}")
            
        except Exception as e:
            print(f"\n❌ Failed to save report: {str(e)}")


async def main():
    """Main entry point"""
    runner = InteractiveTestRunner()
    await runner.run()


if __name__ == "__main__":
    print("🧪 WHOOP FastAPI Microservice - Manual Testing Suite")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")