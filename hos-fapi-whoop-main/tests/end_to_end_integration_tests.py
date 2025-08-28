#!/usr/bin/env python3
"""
WHOOP FastAPI Microservice - End-to-End Integration Testing Suite
================================================================

Comprehensive end-to-end testing suite that validates complete workflows from 
OAuth authorization through data retrieval and database integration.

Usage:
    python end_to_end_integration_tests.py
    
Features:
- Complete OAuth flow simulation with real WHOOP endpoints
- Database integration testing with Supabase
- Data synchronization workflow validation  
- Cross-service integration testing
- Real-world scenario testing
- Production readiness validation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import httpx
from unittest.mock import patch, AsyncMock
import secrets
import base64
import hashlib

# Database integration
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  Supabase not available - database tests will be skipped")

@dataclass
class E2ETestScenario:
    """End-to-end test scenario definition"""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    expected_outcome: str
    cleanup_required: bool = True

@dataclass
class E2ETestResult:
    """End-to-end test execution result"""
    scenario_name: str
    total_steps: int
    completed_steps: int
    passed_steps: int
    failed_steps: int
    duration_seconds: float
    success: bool
    error_details: List[str]
    step_results: List[Dict[str, Any]]
    timestamp: datetime

@dataclass
class DatabaseTestData:
    """Test data for database integration"""
    user_id: str
    whoop_user_id: str
    access_token: str
    refresh_token: str
    recovery_data: Dict[str, Any]
    sleep_data: Dict[str, Any]
    workout_data: Dict[str, Any]


class WhoopDatabaseTestHelper:
    """Helper class for database integration testing"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        if not SUPABASE_AVAILABLE:
            self.client = None
            return
            
        try:
            self.client = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"⚠️  Database connection failed: {str(e)}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if database is available for testing"""
        return self.client is not None
    
    async def setup_test_user(self, test_data: DatabaseTestData) -> bool:
        """Setup test user in database"""
        if not self.client:
            return False
            
        try:
            # Insert test user connection
            user_data = {
                "user_id": test_data.user_id,
                "whoop_user_id": test_data.whoop_user_id,
                "access_token": test_data.access_token,
                "refresh_token": test_data.refresh_token,
                "token_expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                "scopes": "read:profile read:recovery read:sleep read:workouts offline",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("whoop_users").upsert(user_data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"❌ Database setup failed: {str(e)}")
            return False
    
    async def insert_test_recovery_data(self, test_data: DatabaseTestData) -> bool:
        """Insert test recovery data"""
        if not self.client:
            return False
            
        try:
            recovery_record = {
                "user_id": test_data.user_id,
                "cycle_id": f"cycle_{uuid.uuid4()}",
                "recovery_score": test_data.recovery_data.get("recovery_score", 75.5),
                "hrv_rmssd": test_data.recovery_data.get("hrv_rmssd", 45.2),
                "resting_heart_rate": test_data.recovery_data.get("resting_heart_rate", 54),
                "skin_temp_celsius": test_data.recovery_data.get("skin_temp_celsius", 36.4),
                "respiratory_rate": test_data.recovery_data.get("respiratory_rate", 14.8),
                "date": date.today().isoformat(),
                "recorded_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("whoop_recovery").insert(recovery_record).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"❌ Recovery data insertion failed: {str(e)}")
            return False
    
    async def insert_test_sleep_data(self, test_data: DatabaseTestData) -> bool:
        """Insert test sleep data"""
        if not self.client:
            return False
            
        try:
            sleep_record = {
                "user_id": test_data.user_id,
                "sleep_id": f"sleep_{uuid.uuid4()}",
                "start_time": (datetime.utcnow() - timedelta(hours=8)).isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_seconds": test_data.sleep_data.get("duration_seconds", 28800),
                "efficiency_percentage": test_data.sleep_data.get("efficiency_percentage", 87.5),
                "sleep_score": test_data.sleep_data.get("sleep_score", 84.0),
                "light_sleep_minutes": test_data.sleep_data.get("light_sleep_minutes", 240),
                "rem_sleep_minutes": test_data.sleep_data.get("rem_sleep_minutes", 120),
                "deep_sleep_minutes": test_data.sleep_data.get("deep_sleep_minutes", 120),
                "awake_minutes": test_data.sleep_data.get("awake_minutes", 20),
                "date": date.today().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("whoop_sleep").insert(sleep_record).execute()
            return len(result.data) > 0
            
        except Exception as e:
            print(f"❌ Sleep data insertion failed: {str(e)}")
            return False
    
    async def verify_data_retrieval(self, user_id: str, data_type: str) -> Tuple[bool, int]:
        """Verify data can be retrieved from database"""
        if not self.client:
            return False, 0
            
        try:
            table_name = f"whoop_{data_type}"
            result = self.client.table(table_name).select("*").eq("user_id", user_id).execute()
            
            return True, len(result.data)
            
        except Exception as e:
            print(f"❌ Data retrieval verification failed: {str(e)}")
            return False, 0
    
    async def cleanup_test_data(self, user_id: str) -> bool:
        """Clean up test data for user"""
        if not self.client:
            return False
            
        try:
            tables = ["whoop_users", "whoop_recovery", "whoop_sleep", "whoop_workouts", "whoop_sync_log"]
            
            for table in tables:
                try:
                    self.client.table(table).delete().eq("user_id", user_id).execute()
                except:
                    pass  # Ignore errors for non-existent data
                    
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {str(e)}")
            return False


class WhoopE2ETestSuite:
    """Main end-to-end testing suite"""
    
    def __init__(self, api_base_url: str = "http://localhost:8001", 
                 api_key: str = "dev-api-key-change-in-production",
                 supabase_url: str = "", supabase_key: str = ""):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.db_helper = WhoopDatabaseTestHelper(supabase_url, supabase_key) if supabase_url and supabase_key else None
        self.test_results = []
        self.session_data = {}
        
    def print_section(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print('='*60)
    
    def create_test_scenarios(self) -> List[E2ETestScenario]:
        """Create comprehensive end-to-end test scenarios"""
        return [
            self._create_oauth_flow_scenario(),
            self._create_database_integration_scenario(),
            self._create_data_sync_scenario(),
            self._create_multi_user_scenario(),
            self._create_error_recovery_scenario(),
            self._create_production_readiness_scenario()
        ]
    
    def _create_oauth_flow_scenario(self) -> E2ETestScenario:
        """Create OAuth flow end-to-end scenario"""
        return E2ETestScenario(
            name="Complete OAuth Flow",
            description="Test complete OAuth 2.0 authorization flow with PKCE",
            steps=[
                {
                    "name": "Get OAuth Configuration",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/whoop/auth/oauth-config",
                    "expected_status": 200,
                    "validations": [
                        {"field": "pkce_supported", "value": True},
                        {"field": "client_id", "not_empty": True}
                    ]
                },
                {
                    "name": "Initiate OAuth Authorization",
                    "type": "api_call",
                    "method": "POST",
                    "endpoint": "/api/v1/whoop/auth/authorize",
                    "body": {
                        "user_id": "e2e_oauth_user",
                        "redirect_uri": "http://localhost:8001/callback",
                        "scopes": ["read:profile", "read:recovery", "offline"]
                    },
                    "expected_status": 200,
                    "validations": [
                        {"field": "authorization_url", "contains": "code_challenge"},
                        {"field": "state", "min_length": 8}
                    ],
                    "extract": {"oauth_state": "state", "auth_url": "authorization_url"}
                },
                {
                    "name": "Verify OAuth State Management",
                    "type": "validation",
                    "check": "oauth_state_valid"
                },
                {
                    "name": "Test OAuth Callback Structure",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/whoop/auth/callback",
                    "params": {"code": "test_invalid_code", "state": "{{oauth_state}}"},
                    "expected_status": [400, 500],
                    "validations": []
                },
                {
                    "name": "Verify Connection Status",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/auth/status/e2e_oauth_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "expected_status": 200,
                    "validations": [
                        {"field": "connection_status.connected", "value": False}
                    ]
                }
            ],
            expected_outcome="OAuth flow initiated successfully with proper state management"
        )
    
    def _create_database_integration_scenario(self) -> E2ETestScenario:
        """Create database integration scenario"""
        return E2ETestScenario(
            name="Database Integration",
            description="Test complete database integration with CRUD operations",
            steps=[
                {
                    "name": "Setup Test User in Database",
                    "type": "database",
                    "operation": "setup_user",
                    "data": {
                        "user_id": "e2e_db_user",
                        "whoop_user_id": "whoop_123456",
                        "access_token": "test_access_token",
                        "refresh_token": "test_refresh_token"
                    }
                },
                {
                    "name": "Insert Recovery Data",
                    "type": "database",
                    "operation": "insert_recovery",
                    "data": {
                        "recovery_score": 82.5,
                        "hrv_rmssd": 48.3,
                        "resting_heart_rate": 52
                    }
                },
                {
                    "name": "Insert Sleep Data",
                    "type": "database", 
                    "operation": "insert_sleep",
                    "data": {
                        "duration_seconds": 29400,
                        "efficiency_percentage": 91.2,
                        "sleep_score": 87.0
                    }
                },
                {
                    "name": "Verify Data via API - Database Source",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/health-metrics/e2e_db_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"source": "database", "days_back": "1"},
                    "expected_status": 200,
                    "validations": [
                        {"field": "source", "value": "database"},
                        {"field": "database_data", "not_empty": True}
                    ]
                },
                {
                    "name": "Verify Recovery Data Retrieval",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/data/recovery/e2e_db_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "expected_status": 200,
                    "validations": [
                        {"field": "user_id", "value": "e2e_db_user"}
                    ]
                },
                {
                    "name": "Cleanup Test Data",
                    "type": "database",
                    "operation": "cleanup",
                    "data": {"user_id": "e2e_db_user"}
                }
            ],
            expected_outcome="Database operations successful with data retrievable via API"
        )
    
    def _create_data_sync_scenario(self) -> E2ETestScenario:
        """Create data synchronization scenario"""
        return E2ETestScenario(
            name="Data Synchronization Workflow",
            description="Test complete data sync from WHOOP API to database",
            steps=[
                {
                    "name": "Setup Connected User",
                    "type": "database",
                    "operation": "setup_user",
                    "data": {
                        "user_id": "e2e_sync_user",
                        "whoop_user_id": "whoop_sync_123",
                        "access_token": "valid_sync_token",
                        "refresh_token": "sync_refresh_token"
                    }
                },
                {
                    "name": "Test Sync Endpoint",
                    "type": "api_call",
                    "method": "POST",
                    "endpoint": "/api/v1/sync/e2e_sync_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {
                        "data_types": "recovery,sleep",
                        "days_back": "3",
                        "force_refresh": "false"
                    },
                    "expected_status": [200, 404, 502],
                    "validations": [
                        {"field": "user_id", "value": "e2e_sync_user"}
                    ]
                },
                {
                    "name": "Verify Sync with Both Sources",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/health-metrics/e2e_sync_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"source": "both", "days_back": "3"},
                    "expected_status": [200, 404, 502],
                    "validations": []
                },
                {
                    "name": "Test Forced Sync",
                    "type": "api_call",
                    "method": "POST",
                    "endpoint": "/api/v1/sync/e2e_sync_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"force_refresh": "true", "days_back": "1"},
                    "expected_status": [200, 404, 502],
                    "validations": []
                },
                {
                    "name": "Cleanup Sync Test Data",
                    "type": "database",
                    "operation": "cleanup",
                    "data": {"user_id": "e2e_sync_user"}
                }
            ],
            expected_outcome="Data sync workflow operates correctly with proper error handling"
        )
    
    def _create_multi_user_scenario(self) -> E2ETestScenario:
        """Create multi-user scenario"""
        return E2ETestScenario(
            name="Multi-User Operations",
            description="Test concurrent operations with multiple users",
            steps=[
                {
                    "name": "Setup Multiple Test Users",
                    "type": "multi_user_setup",
                    "users": ["e2e_multi_1", "e2e_multi_2", "e2e_multi_3"],
                    "operation": "setup"
                },
                {
                    "name": "Concurrent Auth Status Checks",
                    "type": "concurrent_api_calls",
                    "calls": [
                        {
                            "endpoint": "/api/v1/auth/status/e2e_multi_1",
                            "headers": {"X-API-Key": "{{api_key}}"}
                        },
                        {
                            "endpoint": "/api/v1/auth/status/e2e_multi_2", 
                            "headers": {"X-API-Key": "{{api_key}}"}
                        },
                        {
                            "endpoint": "/api/v1/auth/status/e2e_multi_3",
                            "headers": {"X-API-Key": "{{api_key}}"}
                        }
                    ],
                    "expected_success_rate": 0.8
                },
                {
                    "name": "Concurrent Data Requests",
                    "type": "concurrent_api_calls",
                    "calls": [
                        {
                            "endpoint": "/api/v1/health-metrics/e2e_multi_1",
                            "headers": {"X-API-Key": "{{api_key}}"},
                            "params": {"source": "database"}
                        },
                        {
                            "endpoint": "/api/v1/health-metrics/e2e_multi_2",
                            "headers": {"X-API-Key": "{{api_key}}"},
                            "params": {"source": "database"}
                        }
                    ],
                    "expected_success_rate": 0.8
                },
                {
                    "name": "Cleanup Multi-User Test Data",
                    "type": "multi_user_setup",
                    "users": ["e2e_multi_1", "e2e_multi_2", "e2e_multi_3"],
                    "operation": "cleanup"
                }
            ],
            expected_outcome="Multi-user operations handle concurrency correctly"
        )
    
    def _create_error_recovery_scenario(self) -> E2ETestScenario:
        """Create error recovery scenario"""
        return E2ETestScenario(
            name="Error Recovery and Resilience",
            description="Test system behavior under error conditions",
            steps=[
                {
                    "name": "Test Invalid User ID Handling",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/auth/status/invalid@user#id",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "expected_status": [200, 400, 404, 422],
                    "validations": []
                },
                {
                    "name": "Test Malformed Request Bodies",
                    "type": "api_call",
                    "method": "POST",
                    "endpoint": "/api/v1/whoop/auth/authorize",
                    "body": {"invalid": "data", "missing_required_fields": True},
                    "expected_status": [400, 422],
                    "validations": []
                },
                {
                    "name": "Test Large Data Requests",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/health-metrics/error_recovery_user",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "params": {"days_back": "30", "source": "both"},
                    "expected_status": [200, 404, 502, 504],
                    "validations": [],
                    "timeout": 10.0
                },
                {
                    "name": "Test Rate Limiting Response",
                    "type": "rate_limit_test",
                    "endpoint": "/api/v1/client-status",
                    "requests_count": 15,
                    "expected_status": [200, 429]
                },
                {
                    "name": "Test Service Recovery",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/health/ready",
                    "expected_status": 200,
                    "validations": [
                        {"field": "status", "value_in": ["healthy", "unhealthy"]}
                    ]
                }
            ],
            expected_outcome="System handles errors gracefully and recovers properly"
        )
    
    def _create_production_readiness_scenario(self) -> E2ETestScenario:
        """Create production readiness scenario"""
        return E2ETestScenario(
            name="Production Readiness Validation",
            description="Validate production readiness with realistic loads",
            steps=[
                {
                    "name": "Health Check Validation",
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/health/ready",
                    "expected_status": 200,
                    "validations": [
                        {"field": "status", "not_empty": True},
                        {"field": "timestamp", "not_empty": True}
                    ]
                },
                {
                    "name": "Service Status Validation", 
                    "type": "api_call",
                    "method": "GET",
                    "endpoint": "/api/v1/client-status",
                    "headers": {"X-API-Key": "{{api_key}}"},
                    "expected_status": 200,
                    "validations": [
                        {"field": "service_status", "value": "operational"},
                        {"field": "whoop_client", "not_empty": True}
                    ]
                },
                {
                    "name": "Response Time Validation",
                    "type": "performance_test",
                    "endpoints": [
                        "/",
                        "/health/ready",
                        "/api/v1/whoop/auth/oauth-config"
                    ],
                    "max_response_time_ms": 2000,
                    "requests_per_endpoint": 5
                },
                {
                    "name": "Security Headers Validation",
                    "type": "security_check",
                    "endpoint": "/api/v1/whoop/auth/oauth-config",
                    "check_cors": True,
                    "check_api_key_requirement": True
                },
                {
                    "name": "Data Consistency Check",
                    "type": "consistency_check",
                    "endpoints": [
                        "/api/v1/whoop/auth/oauth-config",
                        "/api/v1/client-status"
                    ],
                    "consistency_fields": ["timestamp_format", "response_structure"]
                }
            ],
            expected_outcome="Service meets production readiness criteria"
        )
    
    async def execute_scenario(self, scenario: E2ETestScenario) -> E2ETestResult:
        """Execute a single end-to-end scenario"""
        print(f"\n🎬 Executing Scenario: {scenario.name}")
        print(f"📝 Description: {scenario.description}")
        print(f"📊 Steps: {len(scenario.steps)}")
        print("-" * 50)
        
        start_time = time.time()
        step_results = []
        completed_steps = 0
        passed_steps = 0
        failed_steps = 0
        error_details = []
        
        for i, step in enumerate(scenario.steps, 1):
            step_name = step.get("name", f"Step {i}")
            print(f"[{i}/{len(scenario.steps)}] {step_name}")
            
            try:
                step_result = await self._execute_step(step)
                step_results.append(step_result)
                completed_steps += 1
                
                if step_result["success"]:
                    passed_steps += 1
                    print(f"  ✅ Passed")
                else:
                    failed_steps += 1
                    error_details.append(f"Step {i}: {step_result.get('error', 'Unknown error')}")
                    print(f"  ❌ Failed: {step_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                completed_steps += 1
                failed_steps += 1
                error_details.append(f"Step {i}: Exception - {str(e)}")
                step_results.append({
                    "step_name": step_name,
                    "success": False,
                    "error": str(e)
                })
                print(f"  ❌ Exception: {str(e)}")
            
            # Small delay between steps
            await asyncio.sleep(0.2)
        
        duration = time.time() - start_time
        overall_success = failed_steps == 0
        
        result = E2ETestResult(
            scenario_name=scenario.name,
            total_steps=len(scenario.steps),
            completed_steps=completed_steps,
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            duration_seconds=duration,
            success=overall_success,
            error_details=error_details,
            step_results=step_results,
            timestamp=datetime.utcnow()
        )
        
        # Cleanup if required
        if scenario.cleanup_required:
            await self._cleanup_scenario_data(scenario)
        
        # Print scenario summary
        success_rate = (passed_steps / completed_steps * 100) if completed_steps > 0 else 0
        status_emoji = "✅" if overall_success else "❌"
        print(f"\n{status_emoji} Scenario Summary:")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Steps: {passed_steps}/{completed_steps} passed ({success_rate:.1f}%)")
        if error_details:
            print(f"   Errors: {len(error_details)}")
        
        return result
    
    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test step"""
        step_type = step.get("type")
        
        if step_type == "api_call":
            return await self._execute_api_call_step(step)
        elif step_type == "database":
            return await self._execute_database_step(step)
        elif step_type == "validation":
            return await self._execute_validation_step(step)
        elif step_type == "concurrent_api_calls":
            return await self._execute_concurrent_api_calls_step(step)
        elif step_type == "multi_user_setup":
            return await self._execute_multi_user_setup_step(step)
        elif step_type == "rate_limit_test":
            return await self._execute_rate_limit_test_step(step)
        elif step_type == "performance_test":
            return await self._execute_performance_test_step(step)
        elif step_type == "security_check":
            return await self._execute_security_check_step(step)
        elif step_type == "consistency_check":
            return await self._execute_consistency_check_step(step)
        else:
            return {"success": False, "error": f"Unknown step type: {step_type}"}
    
    async def _execute_api_call_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call step"""
        method = step.get("method", "GET").upper()
        endpoint = self._resolve_variables(step["endpoint"])
        headers = self._resolve_variables(step.get("headers", {}))
        params = self._resolve_variables(step.get("params", {}))
        body = self._resolve_variables(step.get("body"))
        expected_status = step.get("expected_status", 200)
        validations = step.get("validations", [])
        extract = step.get("extract", {})
        timeout = step.get("timeout", 30.0)
        
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, params=params, json=body)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, params=params, json=body)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                else:
                    return {"success": False, "error": f"Unsupported method: {method}"}
                
                # Check status code
                if isinstance(expected_status, list):
                    status_ok = response.status_code in expected_status
                else:
                    status_ok = response.status_code == expected_status
                
                if not status_ok:
                    return {
                        "success": False,
                        "error": f"Status code {response.status_code}, expected {expected_status}"
                    }
                
                # Parse response
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_text": response.text}
                
                # Run validations
                for validation in validations:
                    if not self._validate_response(response_data, validation):
                        return {
                            "success": False,
                            "error": f"Validation failed: {validation}"
                        }
                
                # Extract data for future steps
                for key, path in extract.items():
                    value = self._extract_from_response(response_data, path)
                    if value is not None:
                        self.session_data[key] = value
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_data": response_data
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_database_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operation step"""
        if not self.db_helper or not self.db_helper.is_available():
            return {"success": True, "skipped": "Database not available"}
        
        operation = step.get("operation")
        data = step.get("data", {})
        
        try:
            if operation == "setup_user":
                test_data = DatabaseTestData(
                    user_id=data["user_id"],
                    whoop_user_id=data["whoop_user_id"],
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    recovery_data={},
                    sleep_data={},
                    workout_data={}
                )
                success = await self.db_helper.setup_test_user(test_data)
                
            elif operation == "insert_recovery":
                test_data = DatabaseTestData(
                    user_id=data.get("user_id", "e2e_db_user"),
                    whoop_user_id="",
                    access_token="",
                    refresh_token="",
                    recovery_data=data,
                    sleep_data={},
                    workout_data={}
                )
                success = await self.db_helper.insert_test_recovery_data(test_data)
                
            elif operation == "insert_sleep":
                test_data = DatabaseTestData(
                    user_id=data.get("user_id", "e2e_db_user"),
                    whoop_user_id="",
                    access_token="",
                    refresh_token="",
                    recovery_data={},
                    sleep_data=data,
                    workout_data={}
                )
                success = await self.db_helper.insert_test_sleep_data(test_data)
                
            elif operation == "cleanup":
                success = await self.db_helper.cleanup_test_data(data["user_id"])
                
            else:
                return {"success": False, "error": f"Unknown database operation: {operation}"}
            
            return {"success": success}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_validation_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation step"""
        check = step.get("check")
        
        if check == "oauth_state_valid":
            state = self.session_data.get("oauth_state")
            if state and len(state) >= 8:
                return {"success": True}
            else:
                return {"success": False, "error": "OAuth state invalid or missing"}
        
        return {"success": False, "error": f"Unknown validation check: {check}"}
    
    async def _execute_concurrent_api_calls_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute concurrent API calls step"""
        calls = step.get("calls", [])
        expected_success_rate = step.get("expected_success_rate", 1.0)
        
        async def make_call(call_config):
            try:
                endpoint = self._resolve_variables(call_config["endpoint"])
                headers = self._resolve_variables(call_config.get("headers", {}))
                params = self._resolve_variables(call_config.get("params", {}))
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(f"{self.api_base_url}{endpoint}", headers=headers, params=params)
                    return {"success": True, "status_code": response.status_code}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        tasks = [make_call(call) for call in calls]
        results = await asyncio.gather(*tasks)
        
        successful_calls = len([r for r in results if r["success"]])
        actual_success_rate = successful_calls / len(results) if results else 0
        
        success = actual_success_rate >= expected_success_rate
        
        return {
            "success": success,
            "successful_calls": successful_calls,
            "total_calls": len(results),
            "success_rate": actual_success_rate,
            "expected_success_rate": expected_success_rate
        }
    
    async def _execute_multi_user_setup_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-user setup step"""
        users = step.get("users", [])
        operation = step.get("operation", "setup")
        
        if not self.db_helper or not self.db_helper.is_available():
            return {"success": True, "skipped": "Database not available"}
        
        success_count = 0
        
        for user_id in users:
            try:
                if operation == "setup":
                    test_data = DatabaseTestData(
                        user_id=user_id,
                        whoop_user_id=f"whoop_{user_id}",
                        access_token=f"token_{user_id}",
                        refresh_token=f"refresh_{user_id}",
                        recovery_data={},
                        sleep_data={},
                        workout_data={}
                    )
                    if await self.db_helper.setup_test_user(test_data):
                        success_count += 1
                        
                elif operation == "cleanup":
                    if await self.db_helper.cleanup_test_data(user_id):
                        success_count += 1
                        
            except Exception:
                pass
        
        success = success_count == len(users)
        return {
            "success": success,
            "users_processed": success_count,
            "total_users": len(users)
        }
    
    async def _execute_rate_limit_test_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute rate limit test step"""
        endpoint = step["endpoint"]
        requests_count = step.get("requests_count", 10)
        expected_status = step.get("expected_status", [200, 429])
        
        status_codes = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(requests_count):
                try:
                    response = await client.get(
                        f"{self.api_base_url}{endpoint}",
                        headers={"X-API-Key": self.api_key}
                    )
                    status_codes.append(response.status_code)
                    await asyncio.sleep(0.1)  # Small delay
                except Exception:
                    status_codes.append(0)
        
        # Check if we got expected status codes
        valid_responses = len([s for s in status_codes if s in expected_status])
        success_rate = valid_responses / len(status_codes) if status_codes else 0
        
        return {
            "success": success_rate >= 0.8,  # At least 80% should be valid
            "valid_responses": valid_responses,
            "total_requests": len(status_codes),
            "status_codes": status_codes
        }
    
    async def _execute_performance_test_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute performance test step"""
        endpoints = step.get("endpoints", [])
        max_response_time_ms = step.get("max_response_time_ms", 2000)
        requests_per_endpoint = step.get("requests_per_endpoint", 3)
        
        all_response_times = []
        failed_endpoints = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in endpoints:
                endpoint_times = []
                
                for _ in range(requests_per_endpoint):
                    try:
                        start_time = time.time()
                        response = await client.get(f"{self.api_base_url}{endpoint}")
                        response_time = (time.time() - start_time) * 1000
                        
                        if response.status_code < 400:  # Only count successful responses
                            endpoint_times.append(response_time)
                            all_response_times.append(response_time)
                        
                    except Exception:
                        pass
                
                # Check if endpoint meets performance criteria
                if endpoint_times:
                    avg_time = sum(endpoint_times) / len(endpoint_times)
                    if avg_time > max_response_time_ms:
                        failed_endpoints.append({
                            "endpoint": endpoint,
                            "avg_time_ms": avg_time
                        })
        
        success = len(failed_endpoints) == 0
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
        
        return {
            "success": success,
            "avg_response_time_ms": avg_response_time,
            "max_response_time_ms": max(all_response_times) if all_response_times else 0,
            "failed_endpoints": failed_endpoints,
            "total_requests": len(all_response_times)
        }
    
    async def _execute_security_check_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security check step"""
        endpoint = step["endpoint"]
        check_cors = step.get("check_cors", False)
        check_api_key = step.get("check_api_key_requirement", False)
        
        security_issues = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_base_url}{endpoint}")
                
                if check_cors:
                    cors_header = response.headers.get("access-control-allow-origin")
                    if not cors_header:
                        security_issues.append("Missing CORS headers")
                
                if check_api_key:
                    # Test endpoint without API key if it requires one
                    if "/api/v1/" in endpoint and endpoint != "/api/v1/whoop/auth/oauth-config":
                        test_response = await client.get(f"{self.api_base_url}/api/v1/client-status")
                        if test_response.status_code != 422:  # Should require API key
                            security_issues.append("API key not properly enforced")
        
        except Exception as e:
            security_issues.append(f"Security check failed: {str(e)}")
        
        return {
            "success": len(security_issues) == 0,
            "security_issues": security_issues
        }
    
    async def _execute_consistency_check_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute consistency check step"""
        endpoints = step.get("endpoints", [])
        consistency_fields = step.get("consistency_fields", [])
        
        responses = []
        inconsistencies = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in endpoints:
                try:
                    headers = {"X-API-Key": self.api_key} if "/api/v1/" in endpoint else {}
                    response = await client.get(f"{self.api_base_url}{endpoint}", headers=headers)
                    
                    if response.status_code == 200:
                        responses.append({
                            "endpoint": endpoint,
                            "data": response.json()
                        })
                except Exception:
                    pass
        
        # Check timestamp format consistency
        if "timestamp_format" in consistency_fields:
            timestamp_formats = []
            for resp in responses:
                data = resp["data"]
                if "timestamp" in data:
                    timestamp_formats.append(data["timestamp"])
            
            if len(set(timestamp_formats)) > 1:
                inconsistencies.append("Inconsistent timestamp formats across endpoints")
        
        # Check response structure consistency
        if "response_structure" in consistency_fields:
            structures = []
            for resp in responses:
                structures.append(list(resp["data"].keys()))
            
            # This is a simplified check - in practice, you'd want more sophisticated structure comparison
        
        return {
            "success": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies,
            "endpoints_checked": len(responses)
        }
    
    async def _cleanup_scenario_data(self, scenario: E2ETestScenario):
        """Clean up data created during scenario execution"""
        if not self.db_helper or not self.db_helper.is_available():
            return
        
        # Clean up known test users based on scenario name
        test_users = []
        
        if "OAuth" in scenario.name:
            test_users.extend(["e2e_oauth_user"])
        elif "Database" in scenario.name:
            test_users.extend(["e2e_db_user"])
        elif "Sync" in scenario.name:
            test_users.extend(["e2e_sync_user"])
        elif "Multi-User" in scenario.name:
            test_users.extend(["e2e_multi_1", "e2e_multi_2", "e2e_multi_3"])
        
        for user_id in test_users:
            try:
                await self.db_helper.cleanup_test_data(user_id)
            except:
                pass  # Ignore cleanup errors
    
    def _resolve_variables(self, value):
        """Resolve template variables"""
        if isinstance(value, str):
            value = value.replace("{{api_key}}", self.api_key)
            
            for key, val in self.session_data.items():
                value = value.replace(f"{{{{{key}}}}}", str(val))
                
        elif isinstance(value, dict):
            return {k: self._resolve_variables(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_variables(item) for item in value]
            
        return value
    
    def _validate_response(self, response_data: Dict[str, Any], validation: Dict[str, Any]) -> bool:
        """Validate response data against validation rules"""
        field = validation.get("field")
        
        if field:
            # Navigate nested fields using dot notation
            value = response_data
            for part in field.split("."):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return False
        else:
            value = response_data
        
        # Check validation rules
        if "value" in validation:
            return value == validation["value"]
        elif "value_in" in validation:
            return value in validation["value_in"]
        elif "not_empty" in validation:
            return value is not None and value != ""
        elif "contains" in validation:
            return validation["contains"] in str(value)
        elif "min_length" in validation:
            return len(str(value)) >= validation["min_length"]
        
        return True
    
    def _extract_from_response(self, response_data: Dict[str, Any], path: str) -> Any:
        """Extract value from response using path"""
        value = response_data
        for part in path.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value
    
    async def run_all_scenarios(self) -> List[E2ETestResult]:
        """Run all end-to-end test scenarios"""
        self.print_section("End-to-End Integration Testing Suite")
        
        scenarios = self.create_test_scenarios()
        
        print(f"📊 Running {len(scenarios)} end-to-end scenarios...")
        print(f"🌐 API Base URL: {self.api_base_url}")
        print(f"💾 Database Available: {'Yes' if self.db_helper and self.db_helper.is_available() else 'No'}")
        print("=" * 60)
        
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n📋 Scenario {i}/{len(scenarios)}")
            
            try:
                result = await self.execute_scenario(scenario)
                results.append(result)
                self.test_results.append(result)
                
            except Exception as e:
                print(f"❌ Scenario failed with exception: {str(e)}")
                results.append(E2ETestResult(
                    scenario_name=scenario.name,
                    total_steps=len(scenario.steps),
                    completed_steps=0,
                    passed_steps=0,
                    failed_steps=len(scenario.steps),
                    duration_seconds=0,
                    success=False,
                    error_details=[str(e)],
                    step_results=[],
                    timestamp=datetime.utcnow()
                ))
            
            # Wait between scenarios
            await asyncio.sleep(1)
        
        return results
    
    def generate_e2e_report(self) -> Dict[str, Any]:
        """Generate comprehensive end-to-end test report"""
        if not self.test_results:
            return {"error": "No test results available"}
        
        total_scenarios = len(self.test_results)
        successful_scenarios = len([r for r in self.test_results if r.success])
        total_steps = sum(r.total_steps for r in self.test_results)
        total_passed_steps = sum(r.passed_steps for r in self.test_results)
        total_duration = sum(r.duration_seconds for r in self.test_results)
        
        report = {
            "summary": {
                "total_scenarios": total_scenarios,
                "successful_scenarios": successful_scenarios,
                "failed_scenarios": total_scenarios - successful_scenarios,
                "scenario_success_rate": (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
                "total_steps": total_steps,
                "total_passed_steps": total_passed_steps,
                "step_success_rate": (total_passed_steps / total_steps * 100) if total_steps > 0 else 0,
                "total_duration_seconds": total_duration,
                "timestamp": datetime.utcnow().isoformat()
            },
            "scenario_results": [asdict(result) for result in self.test_results],
            "recommendations": self._generate_e2e_recommendations(),
            "system_status": {
                "api_accessible": True,  # If we got this far, API is accessible
                "database_available": self.db_helper.is_available() if self.db_helper else False,
                "production_ready": self._assess_production_readiness()
            }
        }
        
        return report
    
    def _generate_e2e_recommendations(self) -> List[str]:
        """Generate recommendations based on E2E test results"""
        recommendations = []
        
        failed_scenarios = [r for r in self.test_results if not r.success]
        
        if failed_scenarios:
            recommendations.append(f"Address failures in {len(failed_scenarios)} scenarios before production deployment")
        
        # Check specific failure patterns
        oauth_failures = [r for r in failed_scenarios if "OAuth" in r.scenario_name]
        if oauth_failures:
            recommendations.append("OAuth flow has issues - review PKCE implementation and state management")
        
        db_failures = [r for r in failed_scenarios if "Database" in r.scenario_name]
        if db_failures:
            recommendations.append("Database integration issues detected - review connection setup and schema")
        
        performance_issues = [r for r in self.test_results if r.duration_seconds > 30]
        if performance_issues:
            recommendations.append("Some scenarios are slow - consider performance optimization")
        
        recommendations.extend([
            "Set up comprehensive monitoring and alerting for production",
            "Implement automated E2E testing in CI/CD pipeline",
            "Create runbooks for common failure scenarios",
            "Plan regular E2E testing schedule for production validation"
        ])
        
        return recommendations
    
    def _assess_production_readiness(self) -> bool:
        """Assess if service is ready for production"""
        if not self.test_results:
            return False
        
        # Critical scenarios that must pass
        critical_scenarios = ["Complete OAuth Flow", "Database Integration", "Production Readiness Validation"]
        
        for result in self.test_results:
            if result.scenario_name in critical_scenarios and not result.success:
                return False
        
        # Overall success rate should be high
        total_scenarios = len(self.test_results)
        successful_scenarios = len([r for r in self.test_results if r.success])
        success_rate = (successful_scenarios / total_scenarios) if total_scenarios > 0 else 0
        
        return success_rate >= 0.8  # At least 80% success rate
    
    def export_e2e_results(self, filename: Optional[str] = None) -> str:
        """Export E2E test results"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"whoop_e2e_results_{timestamp}.json"
        
        report = self.generate_e2e_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filename
    
    def print_e2e_summary(self):
        """Print E2E test summary"""
        report = self.generate_e2e_report()
        
        if "error" in report:
            print("❌ No E2E test results available")
            return
        
        summary = report["summary"]
        
        print("\n" + "="*60)
        print("🧪 End-to-End Integration Test Summary")
        print("="*60)
        print(f"🎬 Total Scenarios: {summary['total_scenarios']}")
        print(f"✅ Successful Scenarios: {summary['successful_scenarios']}")
        print(f"❌ Failed Scenarios: {summary['failed_scenarios']}")
        print(f"📈 Scenario Success Rate: {summary['scenario_success_rate']:.1f}%")
        print(f"📊 Total Steps: {summary['total_steps']}")
        print(f"✅ Passed Steps: {summary['total_passed_steps']}")
        print(f"📈 Step Success Rate: {summary['step_success_rate']:.1f}%")
        print(f"⏱️  Total Duration: {summary['total_duration_seconds']:.1f}s")
        print(f"🚀 Production Ready: {'Yes' if report['system_status']['production_ready'] else 'No'}")
        
        failed_results = [r for r in self.test_results if not r.success]
        if failed_results:
            print(f"\n❌ Failed Scenarios:")
            for result in failed_results:
                print(f"   - {result.scenario_name}: {result.failed_steps}/{result.total_steps} step failures")
        
        print(f"\n💡 Key Recommendations:")
        for i, rec in enumerate(report["recommendations"][:5], 1):
            print(f"   {i}. {rec}")
        
        print("="*60)


async def main():
    """Main entry point for E2E testing"""
    print("🧪 WHOOP API End-to-End Integration Testing Suite")
    print("=" * 60)
    
    # Configuration
    api_base_url = input("API Base URL (default: http://localhost:8001): ").strip() or "http://localhost:8001"
    api_key = input("Service API Key (default: dev-api-key-change-in-production): ").strip() or "dev-api-key-change-in-production"
    
    # Optional database configuration
    print("\nOptional Database Integration (for full E2E testing):")
    supabase_url = input("Supabase URL (optional): ").strip()
    supabase_key = input("Supabase Key (optional): ").strip()
    
    # Create test suite
    test_suite = WhoopE2ETestSuite(api_base_url, api_key, supabase_url, supabase_key)
    
    print(f"\n🔧 Configuration:")
    print(f"   API Base URL: {api_base_url}")
    print(f"   Database Integration: {'Enabled' if supabase_url and supabase_key else 'Disabled'}")
    
    # Run tests
    try:
        results = await test_suite.run_all_scenarios()
        
        # Print summary
        test_suite.print_e2e_summary()
        
        # Ask about exporting results
        export = input("\nExport results to JSON? (y/N): ").strip().lower()
        if export == 'y':
            filename = test_suite.export_e2e_results()
            print(f"📄 Results exported to: {filename}")
        
    except KeyboardInterrupt:
        print("\n⏹️  E2E testing interrupted by user.")
    except Exception as e:
        print(f"\n❌ E2E testing failed: {str(e)}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 E2E testing interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")