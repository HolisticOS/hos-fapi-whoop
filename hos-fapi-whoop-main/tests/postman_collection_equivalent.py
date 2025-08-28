#!/usr/bin/env python3
"""
WHOOP FastAPI Microservice - Postman Collection Equivalent
=========================================================

Python-based equivalent of a Postman collection for WHOOP API testing.
Provides organized request collections with environment management,
pre-request scripts equivalent, and comprehensive response validation.

Usage:
    python postman_collection_equivalent.py
    
Features:
- Environment variable management
- Request collections organized by functionality  
- Response validation and assertions
- Request chaining and data extraction
- Export results to various formats
- CI/CD integration support
"""

import asyncio
import json
import time
import csv
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import httpx
from urllib.parse import urljoin, urlencode
import base64
import hashlib
import secrets

@dataclass
class Environment:
    """Environment configuration similar to Postman environments"""
    name: str
    base_url: str
    api_key: str
    variables: Dict[str, Any]

@dataclass
class RequestResult:
    """Request execution result"""
    name: str
    method: str
    url: str
    status_code: int
    response_time_ms: float
    response_data: Optional[Dict[str, Any]]
    headers: Dict[str, str]
    success: bool
    error: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass 
class Collection:
    """Request collection similar to Postman collections"""
    name: str
    description: str
    requests: List[Dict[str, Any]]


class WhoopPostmanEquivalent:
    """Main class providing Postman-like functionality for WHOOP API testing"""
    
    def __init__(self):
        self.environments = self._load_environments()
        self.current_environment = self.environments["development"]
        self.global_variables = {}
        self.session_data = {}  # For storing data between requests
        self.collections = self._load_collections()
        self.results = []
        
    def _load_environments(self) -> Dict[str, Environment]:
        """Load environment configurations"""
        return {
            "development": Environment(
                name="Development",
                base_url="http://localhost:8001",
                api_key="dev-api-key-change-in-production",
                variables={
                    "timeout": 30,
                    "test_user_prefix": f"test_{int(time.time())}",
                    "default_days_back": 7,
                    "oauth_redirect_uri": "http://localhost:8001/api/v1/whoop/auth/callback"
                }
            ),
            "staging": Environment(
                name="Staging", 
                base_url="https://staging-whoop-api.example.com",
                api_key="staging-api-key",
                variables={
                    "timeout": 45,
                    "test_user_prefix": f"staging_test_{int(time.time())}",
                    "default_days_back": 7,
                    "oauth_redirect_uri": "https://staging-whoop-api.example.com/callback"
                }
            ),
            "production": Environment(
                name="Production",
                base_url="https://whoop-api.example.com",
                api_key="{{PROD_API_KEY}}",  # To be replaced with actual key
                variables={
                    "timeout": 60,
                    "test_user_prefix": f"prod_test_{int(time.time())}",
                    "default_days_back": 3,
                    "oauth_redirect_uri": "https://whoop-api.example.com/callback"
                }
            )
        }
    
    def _load_collections(self) -> Dict[str, Collection]:
        """Load request collections organized by functionality"""
        return {
            "health_checks": self._create_health_checks_collection(),
            "oauth_flow": self._create_oauth_flow_collection(),
            "authentication": self._create_authentication_collection(),
            "data_retrieval": self._create_data_retrieval_collection(),
            "error_scenarios": self._create_error_scenarios_collection(),
            "performance_tests": self._create_performance_tests_collection()
        }
    
    def _create_health_checks_collection(self) -> Collection:
        """Create health check requests collection"""
        return Collection(
            name="Health Checks",
            description="Basic health check and status endpoints",
            requests=[
                {
                    "name": "Root Endpoint",
                    "method": "GET",
                    "url": "/",
                    "headers": {},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_contains", "expected": "WHOOP Health Metrics API"},
                        {"check": "response_has_field", "expected": "version"}
                    ]
                },
                {
                    "name": "Health Ready",
                    "method": "GET", 
                    "url": "/health/ready",
                    "headers": {},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_has_field", "expected": "status"},
                        {"check": "response_has_field", "expected": "timestamp"}
                    ]
                },
                {
                    "name": "Health Live",
                    "method": "GET",
                    "url": "/health/live", 
                    "headers": {},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_has_field", "expected": "status"},
                        {"check": "response_has_field", "expected": "uptime"}
                    ]
                }
            ]
        )
    
    def _create_oauth_flow_collection(self) -> Collection:
        """Create OAuth flow requests collection"""
        return Collection(
            name="OAuth Flow",
            description="Complete OAuth 2.0 authorization flow with PKCE",
            requests=[
                {
                    "name": "OAuth Configuration", 
                    "method": "GET",
                    "url": "/api/v1/whoop/auth/oauth-config",
                    "headers": {},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_has_field", "expected": "authorization_url"},
                        {"check": "response_has_field", "expected": "client_id"},
                        {"check": "response_has_field", "expected": "pkce_supported"},
                        {"check": "response_field_equals", "field": "pkce_supported", "expected": True}
                    ],
                    "post_request_script": "extract_oauth_config"
                },
                {
                    "name": "OAuth Authorization Initiation",
                    "method": "POST",
                    "url": "/api/v1/whoop/auth/authorize",
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "user_id": "{{test_user_prefix}}_oauth_test", 
                        "redirect_uri": "{{oauth_redirect_uri}}",
                        "scopes": ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"]
                    },
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_has_field", "expected": "authorization_url"},
                        {"check": "response_has_field", "expected": "state"},
                        {"check": "response_contains", "expected": "code_challenge"}
                    ],
                    "post_request_script": "extract_oauth_state"
                },
                {
                    "name": "OAuth Callback Validation (Invalid Code)",
                    "method": "GET",
                    "url": "/api/v1/whoop/auth/callback",
                    "headers": {},
                    "params": {
                        "code": "invalid_test_code_12345",
                        "state": "{{oauth_state}}",
                        "user_id": "{{test_user_prefix}}_oauth_test"
                    },
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [400, 500]},
                        {"check": "response_time_under", "expected": 5000}
                    ]
                }
            ]
        )
    
    def _create_authentication_collection(self) -> Collection:
        """Create authentication requests collection"""
        return Collection(
            name="Authentication",
            description="API key authentication and user connection status",
            requests=[
                {
                    "name": "Connection Status - Valid User",
                    "method": "GET",
                    "url": "/api/v1/auth/status/{{test_user_prefix}}_valid",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_has_field", "expected": "user_id"},
                        {"check": "response_has_field", "expected": "connection_status"},
                        {"check": "response_time_under", "expected": 2000}
                    ]
                },
                {
                    "name": "Connection Status - No API Key",
                    "method": "GET", 
                    "url": "/api/v1/auth/status/{{test_user_prefix}}_no_key",
                    "headers": {},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 422}
                    ]
                },
                {
                    "name": "Connection Status - Invalid API Key",
                    "method": "GET",
                    "url": "/api/v1/auth/status/{{test_user_prefix}}_invalid_key",
                    "headers": {"X-API-Key": "invalid_key_12345"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 401}
                    ]
                },
                {
                    "name": "Client Status",
                    "method": "GET",
                    "url": "/api/v1/client-status",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_has_field", "expected": "service_status"},
                        {"check": "response_has_field", "expected": "whoop_client"},
                        {"check": "response_field_equals", "field": "service_status", "expected": "operational"}
                    ],
                    "post_request_script": "extract_rate_limit_info"
                }
            ]
        )
    
    def _create_data_retrieval_collection(self) -> Collection:
        """Create data retrieval requests collection"""
        return Collection(
            name="Data Retrieval",
            description="Health data retrieval endpoints with various parameters",
            requests=[
                {
                    "name": "Recovery Data - Basic",
                    "method": "GET",
                    "url": "/api/v1/data/recovery/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "{{default_days_back}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 3000}
                    ]
                },
                {
                    "name": "Recovery Data - Extended Period",
                    "method": "GET",
                    "url": "/api/v1/data/recovery/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "30"},
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 5000}
                    ]
                },
                {
                    "name": "Sleep Data - Basic",
                    "method": "GET",
                    "url": "/api/v1/data/sleep/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "{{default_days_back}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 3000}
                    ]
                },
                {
                    "name": "Workout Data - Basic",
                    "method": "GET", 
                    "url": "/api/v1/data/workouts/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "{{default_days_back}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 3000}
                    ]
                },
                {
                    "name": "Health Metrics - Database Source",
                    "method": "GET",
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {
                        "source": "database",
                        "days_back": "{{default_days_back}}",
                        "metric_types": "recovery,sleep,workout"
                    },
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 4000}
                    ]
                },
                {
                    "name": "Health Metrics - WHOOP API Source",
                    "method": "GET",
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {
                        "source": "whoop",
                        "days_back": "3",
                        "metric_types": "recovery,sleep"
                    },
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 5000}
                    ]
                },
                {
                    "name": "Health Metrics - Both Sources",
                    "method": "GET", 
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {
                        "source": "both",
                        "days_back": "5"
                    },
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 6000}
                    ]
                },
                {
                    "name": "Health Metrics - Date Range",
                    "method": "GET",
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_data",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-07",
                        "source": "database"
                    },
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 4000}
                    ]
                }
            ]
        )
    
    def _create_error_scenarios_collection(self) -> Collection:
        """Create error scenarios requests collection"""
        return Collection(
            name="Error Scenarios",
            description="Error handling and edge case validation",
            requests=[
                {
                    "name": "Invalid User ID - Special Characters",
                    "method": "GET",
                    "url": "/api/v1/auth/status/user@with@symbols",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 400, 404, 422]},
                        {"check": "response_time_under", "expected": 2000}
                    ]
                },
                {
                    "name": "Invalid Date Parameter",
                    "method": "GET",
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_error",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"start_date": "invalid-date-format"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 422}
                    ]
                },
                {
                    "name": "Invalid Days Parameter - Negative",
                    "method": "GET",
                    "url": "/api/v1/data/recovery/{{test_user_prefix}}_error",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "-1"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 422}
                    ]
                },
                {
                    "name": "Invalid Days Parameter - Too High",
                    "method": "GET", 
                    "url": "/api/v1/data/recovery/{{test_user_prefix}}_error",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "100"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 422}
                    ]
                },
                {
                    "name": "Invalid Days Parameter - Non-numeric",
                    "method": "GET",
                    "url": "/api/v1/data/recovery/{{test_user_prefix}}_error",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days": "abc"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 422}
                    ]
                },
                {
                    "name": "Missing Required Path Parameter",
                    "method": "GET",
                    "url": "/api/v1/auth/status/",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 404}
                    ]
                }
            ]
        )
    
    def _create_performance_tests_collection(self) -> Collection:
        """Create performance test requests collection"""
        return Collection(
            name="Performance Tests",
            description="Performance and load testing scenarios",
            requests=[
                {
                    "name": "Response Time - Auth Status",
                    "method": "GET",
                    "url": "/api/v1/auth/status/{{test_user_prefix}}_perf",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_time_under", "expected": 1000}
                    ]
                },
                {
                    "name": "Response Time - Client Status",
                    "method": "GET",
                    "url": "/api/v1/client-status",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "body": None,
                    "tests": [
                        {"check": "status_code", "expected": 200},
                        {"check": "response_time_under", "expected": 1500}
                    ]
                },
                {
                    "name": "Response Time - Health Metrics",
                    "method": "GET",
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_perf",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"source": "database", "days_back": "3"},
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 3000}
                    ]
                },
                {
                    "name": "Large Data Request", 
                    "method": "GET",
                    "url": "/api/v1/health-metrics/{{test_user_prefix}}_perf",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {
                        "source": "both",
                        "days_back": "30",
                        "metric_types": "recovery,sleep,workout"
                    },
                    "body": None,
                    "tests": [
                        {"check": "status_code_in", "expected": [200, 404, 502]},
                        {"check": "response_time_under", "expected": 10000}
                    ]
                }
            ]
        )
    
    async def execute_request(self, request: Dict[str, Any]) -> RequestResult:
        """Execute a single request with full validation"""
        start_time = time.time()
        
        try:
            # Prepare URL
            url = self._resolve_variables(request["url"])
            full_url = urljoin(self.current_environment.base_url, url)
            
            # Prepare headers
            headers = self._resolve_variables(request.get("headers", {}))
            
            # Prepare parameters
            params = self._resolve_variables(request.get("params", {}))
            
            # Prepare body
            body = self._resolve_variables(request.get("body"))
            
            # Execute request
            async with httpx.AsyncClient(timeout=self.current_environment.variables["timeout"]) as client:
                if request["method"].upper() == "GET":
                    response = await client.get(full_url, headers=headers, params=params)
                elif request["method"].upper() == "POST":
                    response = await client.post(full_url, headers=headers, params=params, json=body)
                elif request["method"].upper() == "PUT":
                    response = await client.put(full_url, headers=headers, params=params, json=body)
                elif request["method"].upper() == "DELETE":
                    response = await client.delete(full_url, headers=headers, params=params)
                else:
                    raise ValueError(f"Unsupported method: {request['method']}")
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_content": response.text}
            
            # Create result
            result = RequestResult(
                name=request["name"],
                method=request["method"].upper(),
                url=full_url,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                response_data=response_data,
                headers=dict(response.headers),
                success=True,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Run tests
            if "tests" in request:
                test_success = self._run_tests(request["tests"], result)
                result.success = test_success
            
            # Run post-request script
            if "post_request_script" in request:
                self._run_post_request_script(request["post_request_script"], result)
            
            return result
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return RequestResult(
                name=request["name"],
                method=request["method"].upper(),
                url=full_url if 'full_url' in locals() else request["url"],
                status_code=0,
                response_time_ms=response_time_ms,
                response_data=None,
                headers={},
                success=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat()
            )
    
    def _resolve_variables(self, value: Any) -> Any:
        """Resolve template variables in requests (similar to Postman variables)"""
        if isinstance(value, str):
            # Replace environment variables
            for key, val in self.current_environment.variables.items():
                value = value.replace(f"{{{{{key}}}}}", str(val))
            
            # Replace environment properties
            value = value.replace("{{api_key}}", self.current_environment.api_key)
            value = value.replace("{{base_url}}", self.current_environment.base_url)
            
            # Replace global variables
            for key, val in self.global_variables.items():
                value = value.replace(f"{{{{{key}}}}}", str(val))
            
            # Replace session data
            for key, val in self.session_data.items():
                value = value.replace(f"{{{{{key}}}}}", str(val))
                
        elif isinstance(value, dict):
            return {k: self._resolve_variables(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_variables(item) for item in value]
            
        return value
    
    def _run_tests(self, tests: List[Dict[str, Any]], result: RequestResult) -> bool:
        """Run test assertions on request result"""
        all_tests_passed = True
        
        for test in tests:
            check_type = test["check"]
            expected = test["expected"]
            
            try:
                if check_type == "status_code":
                    assert result.status_code == expected
                elif check_type == "status_code_in":
                    assert result.status_code in expected
                elif check_type == "response_contains":
                    response_text = json.dumps(result.response_data) if result.response_data else ""
                    assert expected in response_text
                elif check_type == "response_has_field":
                    assert result.response_data is not None
                    assert expected in result.response_data
                elif check_type == "response_field_equals":
                    field = test["field"] 
                    assert result.response_data is not None
                    assert result.response_data.get(field) == expected
                elif check_type == "response_time_under":
                    assert result.response_time_ms < expected
                else:
                    print(f"Unknown test type: {check_type}")
                    all_tests_passed = False
                    
            except AssertionError:
                all_tests_passed = False
                print(f"Test failed for {result.name}: {check_type} expected {expected}")
            except Exception as e:
                all_tests_passed = False
                print(f"Test error for {result.name}: {str(e)}")
        
        return all_tests_passed
    
    def _run_post_request_script(self, script_name: str, result: RequestResult):
        """Run post-request script to extract data (similar to Postman scripts)"""
        if script_name == "extract_oauth_config" and result.response_data:
            self.session_data["client_id"] = result.response_data.get("client_id")
            self.session_data["authorization_url"] = result.response_data.get("authorization_url")
            
        elif script_name == "extract_oauth_state" and result.response_data:
            self.session_data["oauth_state"] = result.response_data.get("state")
            self.session_data["authorization_url"] = result.response_data.get("authorization_url")
            
        elif script_name == "extract_rate_limit_info" and result.response_data:
            whoop_client = result.response_data.get("whoop_client", {})
            rate_limiting = whoop_client.get("rate_limiting", {})
            self.session_data["rate_limit_status"] = rate_limiting
    
    async def execute_collection(self, collection_name: str) -> List[RequestResult]:
        """Execute all requests in a collection"""
        if collection_name not in self.collections:
            raise ValueError(f"Collection '{collection_name}' not found")
        
        collection = self.collections[collection_name]
        results = []
        
        print(f"\n🚀 Executing Collection: {collection.name}")
        print(f"📝 Description: {collection.description}")
        print(f"📊 Requests: {len(collection.requests)}")
        print("-" * 60)
        
        for i, request in enumerate(collection.requests, 1):
            print(f"[{i}/{len(collection.requests)}] {request['name']}")
            
            result = await self.execute_request(request)
            results.append(result)
            
            # Print result summary
            status_emoji = "✅" if result.success else "❌"
            print(f"  {status_emoji} {result.status_code} - {result.response_time_ms:.0f}ms")
            
            if not result.success and result.error:
                print(f"  ❌ Error: {result.error}")
            
            # Small delay between requests to be respectful
            await asyncio.sleep(0.2)
        
        return results
    
    async def execute_all_collections(self) -> Dict[str, List[RequestResult]]:
        """Execute all collections"""
        all_results = {}
        
        print(f"🧪 Executing All Collections for Environment: {self.current_environment.name}")
        print(f"🌐 Base URL: {self.current_environment.base_url}")
        print("=" * 80)
        
        for collection_name in self.collections.keys():
            try:
                results = await self.execute_collection(collection_name)
                all_results[collection_name] = results
                self.results.extend(results)
                
                # Print collection summary
                total_requests = len(results)
                successful_requests = len([r for r in results if r.success])
                print(f"\n📊 Collection Summary: {total_requests} total, {successful_requests} successful")
                
            except Exception as e:
                print(f"❌ Collection execution failed: {str(e)}")
                all_results[collection_name] = []
        
        return all_results
    
    def switch_environment(self, environment_name: str):
        """Switch to a different environment"""
        if environment_name not in self.environments:
            raise ValueError(f"Environment '{environment_name}' not found")
        
        self.current_environment = self.environments[environment_name]
        print(f"🔄 Switched to environment: {environment_name}")
        print(f"🌐 Base URL: {self.current_environment.base_url}")
    
    def set_global_variable(self, key: str, value: Any):
        """Set a global variable"""
        self.global_variables[key] = value
        print(f"🔧 Set global variable: {key} = {value}")
    
    def get_results_summary(self) -> Dict[str, Any]:
        """Get summary of all test results"""
        total_requests = len(self.results)
        successful_requests = len([r for r in self.results if r.success])
        failed_requests = total_requests - successful_requests
        
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100
            avg_response_time = sum(r.response_time_ms for r in self.results) / total_requests
            max_response_time = max(r.response_time_ms for r in self.results)
            min_response_time = min(r.response_time_ms for r in self.results)
        else:
            success_rate = 0
            avg_response_time = 0
            max_response_time = 0
            min_response_time = 0
        
        return {
            "summary": {
                "environment": self.current_environment.name,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": success_rate,
                "average_response_time_ms": avg_response_time,
                "max_response_time_ms": max_response_time,
                "min_response_time_ms": min_response_time,
                "timestamp": datetime.utcnow().isoformat()
            },
            "failed_requests": [
                {
                    "name": r.name,
                    "method": r.method,
                    "url": r.url,
                    "status_code": r.status_code,
                    "error": r.error
                }
                for r in self.results if not r.success
            ]
        }
    
    def export_results(self, format_type: str = "json", filename: Optional[str] = None):
        """Export results in various formats"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"whoop_postman_results_{timestamp}"
        
        if format_type.lower() == "json":
            self._export_json(filename)
        elif format_type.lower() == "csv":
            self._export_csv(filename)
        elif format_type.lower() == "html":
            self._export_html(filename)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_json(self, filename: str):
        """Export results as JSON"""
        data = {
            "summary": self.get_results_summary(),
            "results": [asdict(result) for result in self.results]
        }
        
        json_filename = f"{filename}.json"
        with open(json_filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"📄 Results exported to: {json_filename}")
    
    def _export_csv(self, filename: str):
        """Export results as CSV"""
        csv_filename = f"{filename}.csv"
        with open(csv_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Name', 'Method', 'URL', 'Status Code', 'Response Time (ms)',
                'Success', 'Error', 'Timestamp'
            ])
            
            # Data rows
            for result in self.results:
                writer.writerow([
                    result.name,
                    result.method,
                    result.url,
                    result.status_code,
                    result.response_time_ms,
                    result.success,
                    result.error or '',
                    result.timestamp
                ])
        
        print(f"📊 Results exported to: {csv_filename}")
    
    def _export_html(self, filename: str):
        """Export results as HTML report"""
        summary = self.get_results_summary()
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>WHOOP API Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .results {{ margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .timestamp {{ font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 WHOOP API Test Results</h1>
        <p><strong>Environment:</strong> {summary['summary']['environment']}</p>
        <p><strong>Timestamp:</strong> {summary['summary']['timestamp']}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <p><strong>Total Requests:</strong> {summary['summary']['total_requests']}</p>
        <p><strong>Successful:</strong> <span class="success">{summary['summary']['successful_requests']}</span></p>
        <p><strong>Failed:</strong> <span class="failure">{summary['summary']['failed_requests']}</span></p>
        <p><strong>Success Rate:</strong> {summary['summary']['success_rate']:.1f}%</p>
        <p><strong>Average Response Time:</strong> {summary['summary']['average_response_time_ms']:.0f}ms</p>
    </div>
    
    <div class="results">
        <h2>📋 Detailed Results</h2>
        <table>
            <tr>
                <th>Name</th>
                <th>Method</th>
                <th>Status</th>
                <th>Response Time</th>
                <th>Success</th>
                <th>Error</th>
            </tr>
        """
        
        for result in self.results:
            success_class = "success" if result.success else "failure"
            success_text = "✅ Pass" if result.success else "❌ Fail"
            
            html_content += f"""
            <tr>
                <td>{result.name}</td>
                <td>{result.method}</td>
                <td>{result.status_code}</td>
                <td>{result.response_time_ms:.0f}ms</td>
                <td class="{success_class}">{success_text}</td>
                <td>{result.error or ''}</td>
            </tr>
            """
        
        html_content += """
        </table>
    </div>
</body>
</html>
        """
        
        html_filename = f"{filename}.html"
        with open(html_filename, 'w') as f:
            f.write(html_content)
        
        print(f"🌐 HTML report exported to: {html_filename}")
    
    def print_results_summary(self):
        """Print formatted results summary"""
        summary = self.get_results_summary()
        
        print("\n" + "="*60)
        print("📊 WHOOP API Test Results Summary")
        print("="*60)
        print(f"🌍 Environment: {summary['summary']['environment']}")
        print(f"🔢 Total Requests: {summary['summary']['total_requests']}")
        print(f"✅ Successful: {summary['summary']['successful_requests']}")
        print(f"❌ Failed: {summary['summary']['failed_requests']}")
        print(f"📈 Success Rate: {summary['summary']['success_rate']:.1f}%")
        print(f"⏱️  Average Response Time: {summary['summary']['average_response_time_ms']:.0f}ms")
        print(f"⚡ Max Response Time: {summary['summary']['max_response_time_ms']:.0f}ms")
        print(f"🕐 Timestamp: {summary['summary']['timestamp']}")
        
        if summary['failed_requests']:
            print(f"\n❌ Failed Requests:")
            for failed in summary['failed_requests']:
                print(f"   - {failed['name']}: {failed['status_code']} - {failed['error']}")
        
        print("="*60)


class InteractivePostmanRunner:
    """Interactive runner for Postman-equivalent functionality"""
    
    def __init__(self):
        self.client = WhoopPostmanEquivalent()
    
    async def run(self):
        """Run interactive menu"""
        print("🧪 WHOOP API Postman Collection Equivalent")
        print("=" * 60)
        
        await self.show_main_menu()
    
    async def show_main_menu(self):
        """Show main menu"""
        while True:
            print(f"\n📋 Main Menu (Environment: {self.client.current_environment.name}):")
            print("1.  🚀 Execute All Collections")
            print("2.  📁 Execute Specific Collection")
            print("3.  🔍 Execute Single Request")
            print("4.  🌍 Switch Environment")
            print("5.  🔧 Manage Variables")
            print("6.  📊 View Results Summary")
            print("7.  💾 Export Results")
            print("8.  🔄 Clear Results")
            print("9.  ℹ️  Show Configuration")
            print("10. 🚪 Exit")
            
            choice = input("\nSelect option (1-10): ").strip()
            
            try:
                if choice == "1":
                    await self.execute_all_collections()
                elif choice == "2":
                    await self.execute_specific_collection()
                elif choice == "3":
                    await self.execute_single_request()
                elif choice == "4":
                    await self.switch_environment()
                elif choice == "5":
                    await self.manage_variables()
                elif choice == "6":
                    self.client.print_results_summary()
                elif choice == "7":
                    await self.export_results()
                elif choice == "8":
                    self.clear_results()
                elif choice == "9":
                    self.show_configuration()
                elif choice == "10":
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n\n⏹️  Operation interrupted by user.")
                continue
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                continue
    
    async def execute_all_collections(self):
        """Execute all collections"""
        print("\n🚀 Executing all collections...")
        start_time = time.time()
        
        await self.client.execute_all_collections()
        
        total_time = time.time() - start_time
        print(f"\n⏱️  All collections completed in {total_time:.1f} seconds")
        
        self.client.print_results_summary()
    
    async def execute_specific_collection(self):
        """Execute a specific collection"""
        print("\n📁 Available Collections:")
        collections = list(self.client.collections.keys())
        
        for i, name in enumerate(collections, 1):
            collection = self.client.collections[name]
            print(f"{i}. {collection.name} ({len(collection.requests)} requests)")
            print(f"   {collection.description}")
        
        try:
            choice = int(input(f"\nSelect collection (1-{len(collections)}): "))
            if 1 <= choice <= len(collections):
                collection_name = collections[choice - 1]
                await self.client.execute_collection(collection_name)
            else:
                print("❌ Invalid collection number.")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
    
    async def execute_single_request(self):
        """Execute a single request"""
        print("\n🔍 Execute Single Request")
        
        # Show available collections and requests
        print("\nAvailable Requests:")
        all_requests = []
        
        for collection_name, collection in self.client.collections.items():
            for request in collection.requests:
                all_requests.append((collection_name, request))
                print(f"{len(all_requests)}. [{collection.name}] {request['name']}")
        
        try:
            choice = int(input(f"\nSelect request (1-{len(all_requests)}): "))
            if 1 <= choice <= len(all_requests):
                collection_name, request = all_requests[choice - 1]
                print(f"\n🚀 Executing: {request['name']}")
                
                result = await self.client.execute_request(request)
                self.client.results.append(result)
                
                # Print detailed result
                print(f"\n📊 Result:")
                print(f"   Status: {result.status_code}")
                print(f"   Response Time: {result.response_time_ms:.0f}ms")
                print(f"   Success: {'✅' if result.success else '❌'}")
                if result.error:
                    print(f"   Error: {result.error}")
                    
            else:
                print("❌ Invalid request number.")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
    
    async def switch_environment(self):
        """Switch environment"""
        print("\n🌍 Available Environments:")
        environments = list(self.client.environments.keys())
        
        for i, name in enumerate(environments, 1):
            env = self.client.environments[name]
            current = " (CURRENT)" if name == self.client.current_environment.name else ""
            print(f"{i}. {env.name}{current}")
            print(f"   Base URL: {env.base_url}")
        
        try:
            choice = int(input(f"\nSelect environment (1-{len(environments)}): "))
            if 1 <= choice <= len(environments):
                environment_name = environments[choice - 1]
                self.client.switch_environment(environment_name)
            else:
                print("❌ Invalid environment number.")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
    
    async def manage_variables(self):
        """Manage global variables"""
        while True:
            print(f"\n🔧 Variable Management:")
            print("1. View Current Variables")
            print("2. Set Global Variable")
            print("3. Set Session Variable") 
            print("4. Clear Variables")
            print("5. Back to Main Menu")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                self.show_variables()
            elif choice == "2":
                self.set_global_variable()
            elif choice == "3":
                self.set_session_variable()
            elif choice == "4":
                self.clear_variables()
            elif choice == "5":
                break
            else:
                print("❌ Invalid option.")
    
    def show_variables(self):
        """Show all current variables"""
        print("\n📋 Current Variables:")
        
        print(f"\n🌍 Environment Variables ({self.client.current_environment.name}):")
        for key, value in self.client.current_environment.variables.items():
            print(f"   {key}: {value}")
        
        print(f"\n🌐 Global Variables:")
        if self.client.global_variables:
            for key, value in self.client.global_variables.items():
                print(f"   {key}: {value}")
        else:
            print("   (none)")
        
        print(f"\n📝 Session Variables:")
        if self.client.session_data:
            for key, value in self.client.session_data.items():
                print(f"   {key}: {value}")
        else:
            print("   (none)")
    
    def set_global_variable(self):
        """Set a global variable"""
        key = input("Variable name: ").strip()
        value = input("Variable value: ").strip()
        
        if key and value:
            self.client.set_global_variable(key, value)
        else:
            print("❌ Both name and value are required.")
    
    def set_session_variable(self):
        """Set a session variable"""
        key = input("Session variable name: ").strip()
        value = input("Session variable value: ").strip()
        
        if key and value:
            self.client.session_data[key] = value
            print(f"🔧 Set session variable: {key} = {value}")
        else:
            print("❌ Both name and value are required.")
    
    def clear_variables(self):
        """Clear variables"""
        print("\nClear which variables?")
        print("1. Global Variables")
        print("2. Session Variables")
        print("3. Both")
        
        choice = input("Select option (1-3): ").strip()
        
        if choice == "1":
            self.client.global_variables.clear()
            print("🧹 Global variables cleared.")
        elif choice == "2":
            self.client.session_data.clear()
            print("🧹 Session variables cleared.")
        elif choice == "3":
            self.client.global_variables.clear()
            self.client.session_data.clear()
            print("🧹 All variables cleared.")
        else:
            print("❌ Invalid option.")
    
    async def export_results(self):
        """Export results"""
        if not self.client.results:
            print("❌ No results to export. Run some tests first.")
            return
        
        print("\n💾 Export Results:")
        print("1. JSON Format")
        print("2. CSV Format") 
        print("3. HTML Report")
        print("4. All Formats")
        
        choice = input("Select format (1-4): ").strip()
        filename = input("Filename (optional): ").strip()
        
        if not filename:
            filename = None
        
        try:
            if choice == "1":
                self.client.export_results("json", filename)
            elif choice == "2":
                self.client.export_results("csv", filename)
            elif choice == "3":
                self.client.export_results("html", filename)
            elif choice == "4":
                if filename:
                    base_name = filename
                else:
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    base_name = f"whoop_postman_results_{timestamp}"
                
                self.client.export_results("json", base_name)
                self.client.export_results("csv", base_name)
                self.client.export_results("html", base_name)
                print("📦 All formats exported!")
            else:
                print("❌ Invalid format option.")
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
    
    def clear_results(self):
        """Clear all results"""
        if self.client.results:
            confirm = input(f"Clear {len(self.client.results)} results? (y/N): ").strip().lower()
            if confirm == 'y':
                self.client.results.clear()
                print("🧹 Results cleared.")
            else:
                print("❌ Results not cleared.")
        else:
            print("ℹ️  No results to clear.")
    
    def show_configuration(self):
        """Show current configuration"""
        print("\n⚙️  Current Configuration:")
        print(f"Environment: {self.client.current_environment.name}")
        print(f"Base URL: {self.client.current_environment.base_url}")
        print(f"API Key: {self.client.current_environment.api_key[:10]}..." if self.client.current_environment.api_key else "API Key: Not set")
        print(f"Timeout: {self.client.current_environment.variables['timeout']}s")
        print(f"Collections: {len(self.client.collections)}")
        print(f"Total Requests: {sum(len(c.requests) for c in self.client.collections.values())}")
        print(f"Results Stored: {len(self.client.results)}")


async def main():
    """Main entry point"""
    runner = InteractivePostmanRunner()
    await runner.run()


if __name__ == "__main__":
    print("🧪 WHOOP API Postman Collection Equivalent")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")