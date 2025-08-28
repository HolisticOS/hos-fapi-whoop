#!/usr/bin/env python3
"""
WHOOP FastAPI Microservice - Error Handling and Edge Case Testing Suite
======================================================================

Comprehensive testing suite focused on error handling, edge cases, and system resilience.
Validates proper error responses, input validation, and graceful failure handling.

Usage:
    python error_edge_case_tests.py
    
Features:
- Input validation edge case testing
- Error response format validation
- System resilience under adverse conditions
- Boundary value testing
- Security vulnerability testing
- Malformed request handling
- Resource exhaustion testing
"""

import asyncio
import json
import time
import uuid
import random
import string
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import httpx
import tempfile
import os

@dataclass
class ErrorTestCase:
    """Individual error test case definition"""
    name: str
    description: str
    endpoint: str
    method: str
    headers: Dict[str, str]
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    expected_status_codes: List[int] = None
    should_fail: bool = True
    timeout: float = 30.0
    category: str = "general"

@dataclass
class ErrorTestResult:
    """Error test execution result"""
    test_case_name: str
    success: bool
    status_code: int
    response_time_ms: float
    error_message: Optional[str]
    response_data: Optional[Dict[str, Any]]
    expected_failure: bool
    actual_failure: bool
    category: str
    timestamp: datetime


class WhoopErrorTestSuite:
    """Comprehensive error handling and edge case testing suite"""
    
    def __init__(self, api_base_url: str = "http://localhost:8001", 
                 api_key: str = "dev-api-key-change-in-production"):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.test_results = []
        
    def print_section(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"⚠️  {title}")
        print('='*60)
    
    def create_input_validation_tests(self) -> List[ErrorTestCase]:
        """Create input validation edge case tests"""
        return [
            # User ID validation tests
            ErrorTestCase(
                name="Empty User ID",
                description="Test endpoint with empty user ID",
                endpoint="/api/v1/auth/status/",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[404, 422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Extremely Long User ID",
                description="Test with user ID longer than reasonable limit",
                endpoint=f"/api/v1/auth/status/{'x' * 10000}",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 414, 422],  # 414 = URI Too Long
                category="input_validation"
            ),
            ErrorTestCase(
                name="User ID with Special Characters",
                description="Test user ID with various special characters",
                endpoint="/api/v1/auth/status/user@#$%^&*()+={}[]|\\:;\"'<>?/",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="User ID with Unicode Characters",
                description="Test user ID with Unicode/emoji characters",
                endpoint="/api/v1/auth/status/用户🎉测试👍",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="User ID with SQL Injection Attempt",
                description="Test user ID with SQL injection patterns",
                endpoint="/api/v1/auth/status/'; DROP TABLE users; --",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                category="security"
            ),
            ErrorTestCase(
                name="User ID with XSS Attempt",
                description="Test user ID with XSS injection patterns",
                endpoint="/api/v1/auth/status/<script>alert('xss')</script>",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                category="security"
            ),
            
            # Parameter validation tests
            ErrorTestCase(
                name="Invalid Days Parameter - Negative",
                description="Test days parameter with negative value",
                endpoint="/api/v1/data/recovery/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": -5},
                expected_status_codes=[422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Invalid Days Parameter - Zero",
                description="Test days parameter with zero value",
                endpoint="/api/v1/data/recovery/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": 0},
                expected_status_codes=[422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Invalid Days Parameter - Too Large",
                description="Test days parameter exceeding maximum",
                endpoint="/api/v1/data/recovery/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": 999999},
                expected_status_codes=[422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Invalid Days Parameter - Non-numeric",
                description="Test days parameter with non-numeric value",
                endpoint="/api/v1/data/recovery/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": "not_a_number"},
                expected_status_codes=[422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Invalid Date Format",
                description="Test date parameter with invalid format",
                endpoint="/api/v1/health-metrics/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": "2024-13-45"},  # Invalid date
                expected_status_codes=[422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Invalid Date Format - Wrong Pattern",
                description="Test date parameter with wrong pattern",
                endpoint="/api/v1/health-metrics/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": "01/15/2024"},  # Wrong format
                expected_status_codes=[422],
                category="input_validation"
            ),
            ErrorTestCase(
                name="Date Range - End Before Start",
                description="Test date range where end date is before start date",
                endpoint="/api/v1/health-metrics/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": "2024-12-01", "end_date": "2024-01-01"},
                expected_status_codes=[200, 400, 422],  # Some APIs might handle this gracefully
                category="input_validation"
            ),
            ErrorTestCase(
                name="Future Date Range",
                description="Test date range in the future",
                endpoint="/api/v1/health-metrics/test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": "2030-01-01", "end_date": "2030-12-31"},
                expected_status_codes=[200, 400, 422],  # Future dates might be allowed
                category="input_validation"
            )
        ]
    
    def create_authentication_security_tests(self) -> List[ErrorTestCase]:
        """Create authentication and security related tests"""
        return [
            # API Key tests
            ErrorTestCase(
                name="Missing API Key",
                description="Test endpoint that requires API key without providing one",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={},
                expected_status_codes=[422],
                category="authentication"
            ),
            ErrorTestCase(
                name="Invalid API Key Format",
                description="Test with malformed API key",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={"X-API-Key": ""},
                expected_status_codes=[401, 422],
                category="authentication"
            ),
            ErrorTestCase(
                name="Wrong API Key",
                description="Test with incorrect API key",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={"X-API-Key": "wrong_api_key_123"},
                expected_status_codes=[401],
                category="authentication"
            ),
            ErrorTestCase(
                name="API Key in Wrong Header",
                description="Test providing API key in wrong header name",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={"Authorization": f"Bearer {self.api_key}"},
                expected_status_codes=[401, 422],
                category="authentication"
            ),
            ErrorTestCase(
                name="Multiple API Keys",
                description="Test providing multiple API key headers",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={
                    "X-API-Key": self.api_key,
                    "X-Api-Key": "duplicate_key"
                },
                expected_status_codes=[200, 400],  # Should handle gracefully
                category="authentication"
            ),
            
            # Header injection tests
            ErrorTestCase(
                name="Header Injection Attempt",
                description="Test header injection vulnerability",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={
                    "X-API-Key": self.api_key,
                    "X-Injected-Header\r\nMalicious": "value"
                },
                expected_status_codes=[200, 400],
                category="security"
            ),
            ErrorTestCase(
                name="Extremely Long Header",
                description="Test with extremely long header value",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={
                    "X-API-Key": self.api_key,
                    "X-Long-Header": "x" * 100000
                },
                expected_status_codes=[200, 400, 431],  # 431 = Request Header Fields Too Large
                category="security"
            )
        ]
    
    def create_request_body_tests(self) -> List[ErrorTestCase]:
        """Create request body validation tests"""
        return [
            # OAuth authorization endpoint tests
            ErrorTestCase(
                name="Empty Request Body",
                description="Test POST endpoint with empty body",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body={},
                expected_status_codes=[422],
                category="request_body"
            ),
            ErrorTestCase(
                name="Missing Required Fields",
                description="Test with missing required fields",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body={"user_id": "test_user"},  # Missing redirect_uri and scopes
                expected_status_codes=[422],
                category="request_body"
            ),
            ErrorTestCase(
                name="Invalid JSON Format",
                description="Test with malformed JSON",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body='{"invalid": json, missing_quotes}',  # Will be handled specially
                expected_status_codes=[400, 422],
                category="request_body"
            ),
            ErrorTestCase(
                name="Extremely Large Request Body",
                description="Test with very large request body",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body={
                    "user_id": "test_user",
                    "redirect_uri": "http://example.com",
                    "scopes": ["read:profile"],
                    "large_data": "x" * 1000000  # 1MB of data
                },
                expected_status_codes=[400, 413, 422],  # 413 = Payload Too Large
                category="request_body"
            ),
            ErrorTestCase(
                name="Invalid Field Types",
                description="Test with incorrect field data types",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body={
                    "user_id": 12345,  # Should be string
                    "redirect_uri": ["http://example.com"],  # Should be string
                    "scopes": "read:profile"  # Should be array
                },
                expected_status_codes=[422],
                category="request_body"
            ),
            ErrorTestCase(
                name="Invalid Redirect URI",
                description="Test with invalid redirect URI format",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body={
                    "user_id": "test_user",
                    "redirect_uri": "not_a_valid_uri",
                    "scopes": ["read:profile"]
                },
                expected_status_codes=[400, 422],
                category="request_body"
            ),
            ErrorTestCase(
                name="Invalid Scopes",
                description="Test with invalid OAuth scopes",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "application/json"},
                body={
                    "user_id": "test_user",
                    "redirect_uri": "http://example.com",
                    "scopes": ["invalid:scope", "nonexistent:permission"]
                },
                expected_status_codes=[200, 400, 422],  # Might be handled gracefully
                category="request_body"
            ),
            
            # Content-Type tests
            ErrorTestCase(
                name="Wrong Content-Type",
                description="Test POST with wrong content type",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={"Content-Type": "text/plain"},
                body={"user_id": "test_user", "redirect_uri": "http://example.com"},
                expected_status_codes=[400, 415, 422],  # 415 = Unsupported Media Type
                category="request_body"
            ),
            ErrorTestCase(
                name="Missing Content-Type",
                description="Test POST without content type header",
                endpoint="/api/v1/whoop/auth/authorize",
                method="POST",
                headers={},
                body={"user_id": "test_user", "redirect_uri": "http://example.com"},
                expected_status_codes=[400, 422],
                category="request_body"
            )
        ]
    
    def create_http_method_tests(self) -> List[ErrorTestCase]:
        """Create HTTP method validation tests"""
        return [
            # Method not allowed tests
            ErrorTestCase(
                name="POST on GET Endpoint",
                description="Test POST method on GET-only endpoint",
                endpoint="/api/v1/client-status",
                method="POST",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[405],  # Method Not Allowed
                category="http_methods"
            ),
            ErrorTestCase(
                name="GET on POST Endpoint",
                description="Test GET method on POST-only endpoint",
                endpoint="/api/v1/whoop/auth/authorize",
                method="GET",
                headers={},
                expected_status_codes=[405],
                category="http_methods"
            ),
            ErrorTestCase(
                name="PUT on Endpoint",
                description="Test PUT method on endpoint that doesn't support it",
                endpoint="/api/v1/client-status",
                method="PUT",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[405],
                category="http_methods"
            ),
            ErrorTestCase(
                name="DELETE on Endpoint",
                description="Test DELETE method on endpoint that doesn't support it",
                endpoint="/api/v1/client-status",
                method="DELETE",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[405],
                category="http_methods"
            ),
            ErrorTestCase(
                name="PATCH on Endpoint",
                description="Test PATCH method on endpoint that doesn't support it",
                endpoint="/api/v1/client-status",
                method="PATCH",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[405],
                category="http_methods"
            ),
            ErrorTestCase(
                name="HEAD Request",
                description="Test HEAD method (should return headers only)",
                endpoint="/",
                method="HEAD",
                headers={},
                expected_status_codes=[200, 405],
                should_fail=False,  # HEAD might be supported
                category="http_methods"
            ),
            ErrorTestCase(
                name="OPTIONS Request",
                description="Test OPTIONS method for CORS preflight",
                endpoint="/api/v1/client-status",
                method="OPTIONS",
                headers={},
                expected_status_codes=[200, 204, 405],
                should_fail=False,  # OPTIONS might be supported for CORS
                category="http_methods"
            )
        ]
    
    def create_endpoint_existence_tests(self) -> List[ErrorTestCase]:
        """Create endpoint existence and routing tests"""
        return [
            # Non-existent endpoints
            ErrorTestCase(
                name="Non-existent Endpoint",
                description="Test completely non-existent endpoint",
                endpoint="/api/v1/nonexistent/endpoint",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[404],
                category="routing"
            ),
            ErrorTestCase(
                name="Non-existent API Version",
                description="Test non-existent API version",
                endpoint="/api/v99/client-status",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[404],
                category="routing"
            ),
            ErrorTestCase(
                name="Malformed Endpoint Path",
                description="Test malformed endpoint path",
                endpoint="/api//v1//client-status",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 404],  # Might normalize the path
                category="routing"
            ),
            ErrorTestCase(
                name="Endpoint with Trailing Slash",
                description="Test endpoint path with trailing slash",
                endpoint="/api/v1/client-status/",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 404, 307, 308],  # Might redirect
                should_fail=False,
                category="routing"
            ),
            ErrorTestCase(
                name="Case Sensitive Endpoint",
                description="Test endpoint path case sensitivity",
                endpoint="/API/V1/CLIENT-STATUS",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[404],
                category="routing"
            ),
            ErrorTestCase(
                name="Partial Endpoint Path",
                description="Test incomplete endpoint path",
                endpoint="/api/v1/data/",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[404, 422],
                category="routing"
            )
        ]
    
    def create_resource_exhaustion_tests(self) -> List[ErrorTestCase]:
        """Create resource exhaustion and stress tests"""
        return [
            # Timeout tests
            ErrorTestCase(
                name="Request Timeout Test",
                description="Test request that might timeout",
                endpoint="/api/v1/health-metrics/timeout_test_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days_back": "30", "source": "both"},
                expected_status_codes=[200, 404, 502, 504, 408],  # Various timeout statuses
                timeout=5.0,  # Short timeout
                should_fail=False,  # Timeout is expected behavior
                category="resource_exhaustion"
            ),
            ErrorTestCase(
                name="Large Parameter Values",
                description="Test with extremely large parameter values",
                endpoint="/api/v1/health-metrics/large_param_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={
                    "metric_types": "recovery,sleep,workout," * 1000,  # Very long string
                    "days_back": "30"
                },
                expected_status_codes=[200, 400, 414, 422],
                category="resource_exhaustion"
            ),
            ErrorTestCase(
                name="Many Query Parameters",
                description="Test with excessive number of query parameters",
                endpoint="/api/v1/health-metrics/many_params_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={f"param_{i}": f"value_{i}" for i in range(1000)},  # 1000 params
                expected_status_codes=[200, 400, 414, 422],
                category="resource_exhaustion"
            )
        ]
    
    def create_encoding_tests(self) -> List[ErrorTestCase]:
        """Create character encoding and format tests"""
        return [
            # Character encoding tests
            ErrorTestCase(
                name="UTF-8 Encoding Test",
                description="Test with UTF-8 encoded characters",
                endpoint="/api/v1/auth/status/测试用户名",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                should_fail=False,
                category="encoding"
            ),
            ErrorTestCase(
                name="Percent Encoded Characters",
                description="Test with percent-encoded special characters",
                endpoint="/api/v1/auth/status/test%20user%40example.com",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                should_fail=False,
                category="encoding"
            ),
            ErrorTestCase(
                name="Double Percent Encoding",
                description="Test with double percent encoding",
                endpoint="/api/v1/auth/status/test%2520user",  # %20 encoded again
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                should_fail=False,
                category="encoding"
            ),
            ErrorTestCase(
                name="Null Bytes in URL",
                description="Test with null byte injection in URL",
                endpoint="/api/v1/auth/status/test\x00user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 400, 422],
                category="security"
            )
        ]
    
    async def execute_test_case(self, test_case: ErrorTestCase) -> ErrorTestResult:
        """Execute a single error test case"""
        start_time = time.time()
        
        try:
            url = f"{self.api_base_url}{test_case.endpoint}"
            
            async with httpx.AsyncClient(timeout=test_case.timeout) as client:
                # Handle special body cases
                if test_case.body == '{"invalid": json, missing_quotes}':
                    # Test malformed JSON by sending raw string
                    response = await client.request(
                        test_case.method,
                        url,
                        headers=test_case.headers,
                        params=test_case.params,
                        content='{"invalid": json, missing_quotes}'
                    )
                else:
                    # Normal request
                    response = await client.request(
                        test_case.method,
                        url,
                        headers=test_case.headers,
                        params=test_case.params,
                        json=test_case.body
                    )
                
                response_time = (time.time() - start_time) * 1000
                
                # Parse response
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_text": response.text[:500]}  # First 500 chars
                
                # Determine if test passed
                expected_codes = test_case.expected_status_codes or ([200] if not test_case.should_fail else [400, 422, 500])
                status_ok = response.status_code in expected_codes
                
                # Check if failure expectation matches reality
                actual_failure = response.status_code >= 400
                expectation_match = (actual_failure == test_case.should_fail) or not test_case.should_fail
                
                success = status_ok and expectation_match
                
                return ErrorTestResult(
                    test_case_name=test_case.name,
                    success=success,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    error_message=None,
                    response_data=response_data,
                    expected_failure=test_case.should_fail,
                    actual_failure=actual_failure,
                    category=test_case.category,
                    timestamp=datetime.utcnow()
                )
                
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return ErrorTestResult(
                test_case_name=test_case.name,
                success=test_case.category == "resource_exhaustion",  # Timeout might be expected
                status_code=408,  # Request Timeout
                response_time_ms=response_time,
                error_message="Request timeout",
                response_data=None,
                expected_failure=test_case.should_fail,
                actual_failure=True,
                category=test_case.category,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ErrorTestResult(
                test_case_name=test_case.name,
                success=False,
                status_code=0,
                response_time_ms=response_time,
                error_message=str(e),
                response_data=None,
                expected_failure=test_case.should_fail,
                actual_failure=True,
                category=test_case.category,
                timestamp=datetime.utcnow()
            )
    
    async def run_error_test_category(self, category_name: str, test_cases: List[ErrorTestCase]) -> List[ErrorTestResult]:
        """Run all tests in a category"""
        self.print_section(f"{category_name} Testing")
        
        print(f"📊 Running {len(test_cases)} {category_name.lower()} tests...")
        print("-" * 50)
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {test_case.name}")
            
            result = await self.execute_test_case(test_case)
            results.append(result)
            
            # Print result
            if result.success:
                print(f"  ✅ Passed - {result.status_code} ({result.response_time_ms:.0f}ms)")
            else:
                print(f"  ❌ Failed - {result.status_code} ({result.response_time_ms:.0f}ms)")
                if result.error_message:
                    print(f"     Error: {result.error_message}")
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        # Category summary
        passed_tests = len([r for r in results if r.success])
        print(f"\n📊 {category_name} Summary: {passed_tests}/{len(results)} tests passed")
        
        return results
    
    async def run_all_error_tests(self) -> Dict[str, List[ErrorTestResult]]:
        """Run all error handling tests"""
        self.print_section("Error Handling and Edge Case Testing Suite")
        
        print(f"🌐 API Base URL: {self.api_base_url}")
        print("=" * 60)
        
        # Define test categories
        test_categories = [
            ("Input Validation", self.create_input_validation_tests()),
            ("Authentication & Security", self.create_authentication_security_tests()),
            ("Request Body Validation", self.create_request_body_tests()),
            ("HTTP Methods", self.create_http_method_tests()),
            ("Endpoint Routing", self.create_endpoint_existence_tests()),
            ("Resource Exhaustion", self.create_resource_exhaustion_tests()),
            ("Character Encoding", self.create_encoding_tests())
        ]
        
        all_results = {}
        
        for category_name, test_cases in test_categories:
            try:
                results = await self.run_error_test_category(category_name, test_cases)
                all_results[category_name] = results
                self.test_results.extend(results)
                
                # Wait between categories
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Category {category_name} failed: {str(e)}")
                all_results[category_name] = []
        
        return all_results
    
    async def run_boundary_value_tests(self) -> List[ErrorTestResult]:
        """Run boundary value analysis tests"""
        self.print_section("Boundary Value Analysis")
        
        boundary_tests = [
            # Days parameter boundaries
            ErrorTestCase(
                name="Days = 1 (Minimum Valid)",
                description="Test minimum valid days parameter",
                endpoint="/api/v1/data/recovery/boundary_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": 1},
                expected_status_codes=[200, 404],
                should_fail=False,
                category="boundary"
            ),
            ErrorTestCase(
                name="Days = 30 (Maximum Valid)",
                description="Test maximum valid days parameter",
                endpoint="/api/v1/data/recovery/boundary_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": 30},
                expected_status_codes=[200, 404],
                should_fail=False,
                category="boundary"
            ),
            ErrorTestCase(
                name="Days = 31 (Just Over Maximum)",
                description="Test days parameter just over maximum",
                endpoint="/api/v1/data/recovery/boundary_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"days": 31},
                expected_status_codes=[422],
                category="boundary"
            ),
            
            # Date boundaries
            ErrorTestCase(
                name="Start Date = Today",
                description="Test with start date as today",
                endpoint="/api/v1/health-metrics/boundary_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": date.today().isoformat()},
                expected_status_codes=[200, 404],
                should_fail=False,
                category="boundary"
            ),
            ErrorTestCase(
                name="Start Date = Far Past",
                description="Test with very old start date",
                endpoint="/api/v1/health-metrics/boundary_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": "1900-01-01"},
                expected_status_codes=[200, 400, 404, 422],
                should_fail=False,
                category="boundary"
            ),
            ErrorTestCase(
                name="Start Date = Future",
                description="Test with future start date",
                endpoint="/api/v1/health-metrics/boundary_user",
                method="GET",
                headers={"X-API-Key": self.api_key},
                params={"start_date": (date.today() + timedelta(days=365)).isoformat()},
                expected_status_codes=[200, 400, 404, 422],
                should_fail=False,
                category="boundary"
            ),
            
            # String length boundaries
            ErrorTestCase(
                name="User ID = Single Character",
                description="Test with single character user ID",
                endpoint="/api/v1/auth/status/a",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200],
                should_fail=False,
                category="boundary"
            ),
            ErrorTestCase(
                name="User ID = Very Long",
                description="Test with very long user ID (just under limit)",
                endpoint=f"/api/v1/auth/status/{'u' * 255}",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 414, 422],
                should_fail=False,
                category="boundary"
            )
        ]
        
        results = []
        print(f"📊 Running {len(boundary_tests)} boundary value tests...")
        print("-" * 50)
        
        for i, test_case in enumerate(boundary_tests, 1):
            print(f"[{i}/{len(boundary_tests)}] {test_case.name}")
            
            result = await self.execute_test_case(test_case)
            results.append(result)
            
            if result.success:
                print(f"  ✅ Passed - {result.status_code}")
            else:
                print(f"  ❌ Failed - {result.status_code}")
            
            await asyncio.sleep(0.1)
        
        passed_tests = len([r for r in results if r.success])
        print(f"\n📊 Boundary Value Analysis: {passed_tests}/{len(results)} tests passed")
        
        self.test_results.extend(results)
        return results
    
    async def run_stress_error_tests(self) -> List[ErrorTestResult]:
        """Run stress tests to identify breaking points"""
        self.print_section("Stress Error Testing")
        
        stress_tests = []
        
        # Generate rapid fire requests to same endpoint
        for i in range(20):
            stress_tests.append(ErrorTestCase(
                name=f"Rapid Request {i+1}",
                description=f"Rapid fire request #{i+1}",
                endpoint="/api/v1/client-status",
                method="GET",
                headers={"X-API-Key": self.api_key},
                expected_status_codes=[200, 429, 502, 503],  # Various overload responses
                should_fail=False,
                timeout=5.0,
                category="stress"
            ))
        
        print(f"🔥 Running {len(stress_tests)} stress tests...")
        print("⚠️  This may trigger rate limiting or stress responses")
        print("-" * 50)
        
        results = []
        
        # Execute stress tests with minimal delay
        tasks = []
        for test_case in stress_tests:
            tasks.append(self.execute_test_case(test_case))
        
        # Execute all stress tests concurrently
        start_time = time.time()
        stress_results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Analyze results
        status_codes = [r.status_code for r in stress_results]
        success_count = len([r for r in stress_results if r.success])
        rate_limited_count = len([r for r in stress_results if r.status_code == 429])
        error_count = len([r for r in stress_results if r.status_code >= 500])
        
        print(f"\n🔥 Stress Test Results:")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Successful: {success_count}/{len(stress_results)}")
        print(f"   Rate Limited (429): {rate_limited_count}")
        print(f"   Server Errors (5xx): {error_count}")
        print(f"   Requests/Second: {len(stress_results) / duration:.1f}")
        
        self.test_results.extend(stress_results)
        return stress_results
    
    def generate_error_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive error test report"""
        if not self.test_results:
            return {"error": "No test results available"}
        
        # Organize results by category
        results_by_category = {}
        for result in self.test_results:
            category = result.category
            if category not in results_by_category:
                results_by_category[category] = []
            results_by_category[category].append(result)
        
        # Calculate overall statistics
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.success])
        failed_tests = total_tests - passed_tests
        
        # Calculate category statistics
        category_stats = {}
        for category, results in results_by_category.items():
            category_passed = len([r for r in results if r.success])
            category_stats[category] = {
                "total": len(results),
                "passed": category_passed,
                "failed": len(results) - category_passed,
                "success_rate": (category_passed / len(results) * 100) if results else 0
            }
        
        # Identify critical failures
        critical_failures = []
        for result in self.test_results:
            if not result.success and result.category in ["authentication", "security"]:
                critical_failures.append({
                    "test_name": result.test_case_name,
                    "category": result.category,
                    "status_code": result.status_code,
                    "error": result.error_message
                })
        
        # Response time analysis
        response_times = [r.response_time_ms for r in self.test_results if r.response_time_ms > 0]
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "overall_success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "timestamp": datetime.utcnow().isoformat()
            },
            "category_breakdown": category_stats,
            "critical_failures": critical_failures,
            "failed_tests": [
                {
                    "name": r.test_case_name,
                    "category": r.category,
                    "status_code": r.status_code,
                    "expected_failure": r.expected_failure,
                    "actual_failure": r.actual_failure,
                    "error": r.error_message
                }
                for r in self.test_results if not r.success
            ],
            "recommendations": self._generate_error_test_recommendations(),
            "detailed_results": [asdict(result) for result in self.test_results]
        }
        
        return report
    
    def _generate_error_test_recommendations(self) -> List[str]:
        """Generate recommendations based on error test results"""
        recommendations = []
        
        # Check for authentication issues
        auth_failures = [r for r in self.test_results if not r.success and r.category == "authentication"]
        if auth_failures:
            recommendations.append("Review API key validation and authentication mechanisms")
        
        # Check for security issues
        security_failures = [r for r in self.test_results if not r.success and r.category == "security"]
        if security_failures:
            recommendations.append("Address security vulnerabilities - implement input sanitization")
        
        # Check for input validation issues
        validation_failures = [r for r in self.test_results if not r.success and r.category == "input_validation"]
        if len(validation_failures) > 5:  # More than 5 validation failures
            recommendations.append("Strengthen input validation across all endpoints")
        
        # Check for unhandled errors (500 responses)
        server_errors = [r for r in self.test_results if r.status_code >= 500]
        if server_errors:
            recommendations.append("Fix server errors - review error handling and logging")
        
        # Check for missing error handling
        unexpected_successes = [r for r in self.test_results if not r.success and r.expected_failure and not r.actual_failure]
        if unexpected_successes:
            recommendations.append("Some invalid inputs are being accepted - review validation logic")
        
        # Performance recommendations
        slow_responses = [r for r in self.test_results if r.response_time_ms > 5000]
        if slow_responses:
            recommendations.append("Some error responses are very slow - optimize error handling performance")
        
        recommendations.extend([
            "Implement consistent error response format across all endpoints",
            "Add comprehensive request logging for debugging",
            "Set up monitoring and alerting for error rates",
            "Create error handling documentation for developers",
            "Implement rate limiting to prevent abuse",
            "Regular security testing should be part of CI/CD pipeline"
        ])
        
        return recommendations
    
    def print_error_test_summary(self):
        """Print error test summary"""
        report = self.generate_error_test_report()
        
        if "error" in report:
            print("❌ No error test results available")
            return
        
        summary = report["summary"]
        
        print("\n" + "="*60)
        print("⚠️  Error Handling and Edge Case Test Summary")
        print("="*60)
        print(f"🧪 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed_tests']}")
        print(f"❌ Failed: {summary['failed_tests']}")
        print(f"📈 Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"⏱️  Avg Response Time: {summary['avg_response_time_ms']:.1f}ms")
        print(f"⚡ Max Response Time: {summary['max_response_time_ms']:.1f}ms")
        
        print(f"\n📊 Results by Category:")
        for category, stats in report["category_breakdown"].items():
            print(f"   {category}: {stats['passed']}/{stats['total']} passed ({stats['success_rate']:.1f}%)")
        
        critical_failures = report["critical_failures"]
        if critical_failures:
            print(f"\n🚨 Critical Failures ({len(critical_failures)}):")
            for failure in critical_failures[:5]:  # Show first 5
                print(f"   - {failure['test_name']} ({failure['category']})")
        
        print(f"\n💡 Key Recommendations:")
        for i, rec in enumerate(report["recommendations"][:5], 1):
            print(f"   {i}. {rec}")
        
        print("="*60)
    
    def export_error_results(self, filename: Optional[str] = None) -> str:
        """Export error test results"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"whoop_error_test_results_{timestamp}.json"
        
        report = self.generate_error_test_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filename


class InteractiveErrorTester:
    """Interactive runner for error testing"""
    
    def __init__(self):
        api_base_url = input("API Base URL (default: http://localhost:8001): ").strip() or "http://localhost:8001"
        api_key = input("Service API Key (default: dev-api-key-change-in-production): ").strip() or "dev-api-key-change-in-production"
        self.tester = WhoopErrorTestSuite(api_base_url, api_key)
    
    async def run(self):
        """Run interactive error testing menu"""
        print("⚠️  WHOOP API Error Handling and Edge Case Testing Suite")
        print("=" * 60)
        
        await self.show_main_menu()
    
    async def show_main_menu(self):
        """Show main testing menu"""
        while True:
            print(f"\n📋 Error Testing Menu:")
            print("1.  🧪 Run All Error Tests")
            print("2.  📝 Input Validation Tests")
            print("3.  🔐 Authentication & Security Tests")
            print("4.  📊 Request Body Tests")
            print("5.  🌐 HTTP Method Tests")
            print("6.  🔍 Endpoint Routing Tests")
            print("7.  💥 Resource Exhaustion Tests")
            print("8.  📖 Character Encoding Tests")
            print("9.  📏 Boundary Value Tests")
            print("10. 🔥 Stress Error Tests")
            print("11. 📈 View Test Summary")
            print("12. 💾 Export Results")
            print("13. 🔄 Clear Results")
            print("14. 🚪 Exit")
            
            choice = input("\nSelect option (1-14): ").strip()
            
            try:
                if choice == "1":
                    await self.run_all_tests()
                elif choice == "2":
                    await self.tester.run_error_test_category("Input Validation", self.tester.create_input_validation_tests())
                elif choice == "3":
                    await self.tester.run_error_test_category("Authentication & Security", self.tester.create_authentication_security_tests())
                elif choice == "4":
                    await self.tester.run_error_test_category("Request Body Validation", self.tester.create_request_body_tests())
                elif choice == "5":
                    await self.tester.run_error_test_category("HTTP Methods", self.tester.create_http_method_tests())
                elif choice == "6":
                    await self.tester.run_error_test_category("Endpoint Routing", self.tester.create_endpoint_existence_tests())
                elif choice == "7":
                    await self.tester.run_error_test_category("Resource Exhaustion", self.tester.create_resource_exhaustion_tests())
                elif choice == "8":
                    await self.tester.run_error_test_category("Character Encoding", self.tester.create_encoding_tests())
                elif choice == "9":
                    await self.tester.run_boundary_value_tests()
                elif choice == "10":
                    await self.tester.run_stress_error_tests()
                elif choice == "11":
                    self.tester.print_error_test_summary()
                elif choice == "12":
                    self.export_results()
                elif choice == "13":
                    self.clear_results()
                elif choice == "14":
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
    
    async def run_all_tests(self):
        """Run all error tests"""
        print("\n🧪 Running Complete Error Testing Suite...")
        print("This may take several minutes. Press Ctrl+C to interrupt.")
        
        start_time = time.time()
        
        try:
            # Run all test categories
            await self.tester.run_all_error_tests()
            
            # Run additional specialized tests
            await self.tester.run_boundary_value_tests()
            await self.tester.run_stress_error_tests()
            
            total_time = time.time() - start_time
            print(f"\n⏱️  All error tests completed in {total_time:.1f} seconds")
            
            # Show summary
            self.tester.print_error_test_summary()
            
        except KeyboardInterrupt:
            print("\n⏹️  Error testing interrupted by user.")
    
    def export_results(self):
        """Export error test results"""
        if not self.tester.test_results:
            print("❌ No results to export. Run some tests first.")
            return
        
        filename = input("Export filename (optional): ").strip()
        
        try:
            exported_file = self.tester.export_error_results(filename if filename else None)
            print(f"📄 Results exported to: {exported_file}")
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
    
    def clear_results(self):
        """Clear all test results"""
        if self.tester.test_results:
            confirm = input(f"Clear {len(self.tester.test_results)} test results? (y/N): ").strip().lower()
            if confirm == 'y':
                self.tester.test_results.clear()
                print("🧹 Results cleared.")
            else:
                print("❌ Results not cleared.")
        else:
            print("ℹ️  No results to clear.")


async def main():
    """Main entry point"""
    runner = InteractiveErrorTester()
    await runner.run()


if __name__ == "__main__":
    print("⚠️  WHOOP API Error Handling and Edge Case Testing Suite")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Error testing interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")