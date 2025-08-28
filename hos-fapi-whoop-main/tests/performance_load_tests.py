#!/usr/bin/env python3
"""
WHOOP FastAPI Microservice - Performance and Load Testing Suite
==============================================================

Comprehensive performance and load testing suite for WHOOP API with focus on:
- Rate limiting compliance (100/min, 10K/day)
- Response time validation  
- Concurrent user simulation
- Stress testing and bottleneck identification
- Resource utilization monitoring

Usage:
    python performance_load_tests.py
    
Features:
- WHOOP API rate limit compliance testing
- Multi-user concurrent testing scenarios  
- Response time benchmarking
- Load testing with realistic traffic patterns
- Stress testing to identify breaking points
- Resource monitoring and reporting
"""

import asyncio
import time
import statistics
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import psutil
import threading
from collections import defaultdict, deque

@dataclass
class PerformanceMetric:
    """Individual performance measurement"""
    test_name: str
    request_name: str
    response_time_ms: float
    status_code: int
    success: bool
    timestamp: datetime
    user_id: str
    thread_id: int

@dataclass
class LoadTestConfig:
    """Load test configuration"""
    name: str
    concurrent_users: int
    requests_per_user: int
    ramp_up_seconds: int
    test_duration_seconds: int
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = None
    params: Dict[str, str] = None

@dataclass
class LoadTestResult:
    """Load test execution result"""
    config: LoadTestConfig
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    max_response_time_ms: float
    min_response_time_ms: float
    requests_per_second: float
    errors: List[str]
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    resource_usage: Dict[str, Any]


class RateLimitMonitor:
    """Monitor and enforce rate limiting compliance"""
    
    def __init__(self, requests_per_minute: int = 100, requests_per_day: int = 10000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day
        self.minute_requests = deque()
        self.daily_requests = deque()
        self.lock = threading.Lock()
        
    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limits"""
        now = datetime.utcnow()
        
        with self.lock:
            # Clean old requests
            self._clean_old_requests(now)
            
            # Check minute limit
            if len(self.minute_requests) >= self.requests_per_minute:
                return False
                
            # Check daily limit
            if len(self.daily_requests) >= self.requests_per_day:
                return False
                
            return True
    
    def record_request(self):
        """Record a request"""
        now = datetime.utcnow()
        
        with self.lock:
            self.minute_requests.append(now)
            self.daily_requests.append(now)
    
    def _clean_old_requests(self, now: datetime):
        """Remove old requests outside the time windows"""
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)
        
        # Clean minute window
        while self.minute_requests and self.minute_requests[0] < minute_ago:
            self.minute_requests.popleft()
            
        # Clean daily window
        while self.daily_requests and self.daily_requests[0] < day_ago:
            self.daily_requests.popleft()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        now = datetime.utcnow()
        
        with self.lock:
            self._clean_old_requests(now)
            
            return {
                "minute_used": len(self.minute_requests),
                "minute_limit": self.requests_per_minute,
                "minute_remaining": self.requests_per_minute - len(self.minute_requests),
                "daily_used": len(self.daily_requests),
                "daily_limit": self.requests_per_day,
                "daily_remaining": self.requests_per_day - len(self.daily_requests)
            }


class ResourceMonitor:
    """Monitor system resource usage during tests"""
    
    def __init__(self):
        self.cpu_samples = []
        self.memory_samples = []
        self.network_samples = []
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start resource monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def _monitor_resources(self):
        """Monitor resources in background thread"""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_samples.append({
                    "timestamp": datetime.utcnow(),
                    "value": cpu_percent
                })
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.memory_samples.append({
                    "timestamp": datetime.utcnow(),
                    "percent": memory.percent,
                    "available_mb": memory.available / (1024 * 1024)
                })
                
                # Network IO
                network = psutil.net_io_counters()
                self.network_samples.append({
                    "timestamp": datetime.utcnow(),
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv
                })
                
            except Exception:
                pass  # Ignore monitoring errors
                
            time.sleep(1)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get resource usage summary"""
        if not self.cpu_samples:
            return {}
            
        cpu_values = [s["value"] for s in self.cpu_samples]
        memory_values = [s["percent"] for s in self.memory_samples]
        
        return {
            "cpu": {
                "avg": statistics.mean(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "avg_percent": statistics.mean(memory_values),
                "max_percent": max(memory_values),
                "min_percent": min(memory_values),
                "avg_available_mb": statistics.mean([s["available_mb"] for s in self.memory_samples])
            },
            "samples": len(self.cpu_samples)
        }


class WhoopPerformanceTester:
    """Main performance testing class"""
    
    def __init__(self, base_url: str = "http://localhost:8001", api_key: str = "dev-api-key-change-in-production"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.rate_limiter = RateLimitMonitor()
        self.resource_monitor = ResourceMonitor()
        self.test_results = []
        self.performance_metrics = []
        
    def print_section(self, title: str):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"⚡ {title}")
        print('='*60)
    
    async def test_response_times(self) -> Dict[str, Any]:
        """Test response times for key endpoints"""
        self.print_section("Response Time Testing")
        
        endpoints = [
            {"name": "Root Endpoint", "url": "/", "headers": {}},
            {"name": "Health Ready", "url": "/health/ready", "headers": {}},
            {"name": "OAuth Config", "url": "/api/v1/whoop/auth/oauth-config", "headers": {}},
            {"name": "Client Status", "url": "/api/v1/client-status", "headers": {"X-API-Key": self.api_key}},
            {"name": "Auth Status", "url": "/api/v1/auth/status/perf_test_user", "headers": {"X-API-Key": self.api_key}},
            {"name": "Health Metrics", "url": "/api/v1/health-metrics/perf_test_user", "headers": {"X-API-Key": self.api_key}, "params": {"source": "database", "days_back": "3"}}
        ]
        
        results = {}
        
        for endpoint in endpoints:
            print(f"Testing {endpoint['name']}...")
            
            response_times = []
            status_codes = []
            
            # Make 10 requests to get statistical data
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i in range(10):
                    try:
                        start_time = time.time()
                        response = await client.get(
                            f"{self.base_url}{endpoint['url']}", 
                            headers=endpoint.get("headers", {}),
                            params=endpoint.get("params", {})
                        )
                        response_time = (time.time() - start_time) * 1000  # Convert to ms
                        
                        response_times.append(response_time)
                        status_codes.append(response.status_code)
                        
                        # Respectful delay between requests
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        print(f"   Error on request {i+1}: {str(e)}")
                        
            if response_times:
                results[endpoint["name"]] = {
                    "avg_ms": statistics.mean(response_times),
                    "median_ms": statistics.median(response_times),
                    "max_ms": max(response_times),
                    "min_ms": min(response_times),
                    "p95_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 2 else max(response_times),
                    "successful_requests": len([s for s in status_codes if 200 <= s < 400]),
                    "total_requests": len(response_times),
                    "status_codes": status_codes
                }
                
                print(f"   ✅ Avg: {results[endpoint['name']]['avg_ms']:.1f}ms, "
                      f"Max: {results[endpoint['name']]['max_ms']:.1f}ms, "
                      f"Success: {results[endpoint['name']]['successful_requests']}/{results[endpoint['name']]['total_requests']}")
            else:
                print(f"   ❌ No successful requests")
                
        return results
    
    async def test_rate_limiting_compliance(self) -> Dict[str, Any]:
        """Test rate limiting compliance"""
        self.print_section("Rate Limiting Compliance Testing")
        
        print("Testing WHOOP API rate limits (100/min, 10K/day)...")
        
        # Test endpoint that should be rate limited
        endpoint = "/api/v1/client-status"
        headers = {"X-API-Key": self.api_key}
        
        request_times = []
        response_times = []
        status_codes = []
        rate_limit_violations = 0
        
        # Make requests rapidly to test rate limiting
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(20):  # Test with 20 requests
                if not self.rate_limiter.can_make_request():
                    print(f"   Rate limit reached at request {i+1}")
                    rate_limit_violations += 1
                    await asyncio.sleep(1)  # Wait and retry
                    
                try:
                    start_time = time.time()
                    response = await client.get(f"{self.base_url}{endpoint}", headers=headers)
                    response_time = (time.time() - start_time) * 1000
                    
                    request_times.append(datetime.utcnow())
                    response_times.append(response_time)
                    status_codes.append(response.status_code)
                    
                    self.rate_limiter.record_request()
                    
                    print(f"   Request {i+1}: {response.status_code} - {response_time:.0f}ms")
                    
                    # Small delay to avoid overwhelming
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"   Request {i+1} failed: {str(e)}")
        
        rate_limit_status = self.rate_limiter.get_status()
        
        result = {
            "total_requests": len(response_times),
            "successful_requests": len([s for s in status_codes if 200 <= s < 400]),
            "rate_limit_violations": rate_limit_violations,
            "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
            "rate_limit_status": rate_limit_status,
            "status_codes": status_codes
        }
        
        print(f"\n📊 Rate Limiting Results:")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Successful: {result['successful_requests']}")
        print(f"   Rate Limit Violations: {result['rate_limit_violations']}")
        print(f"   Current Usage: {rate_limit_status['minute_used']}/{rate_limit_status['minute_limit']} per minute")
        
        return result
    
    async def test_concurrent_users(self, num_users: int = 5, requests_per_user: int = 10) -> Dict[str, Any]:
        """Test concurrent user scenarios"""
        self.print_section(f"Concurrent Users Testing ({num_users} users, {requests_per_user} requests each)")
        
        async def simulate_user(user_id: int) -> List[PerformanceMetric]:
            """Simulate a single user's requests"""
            user_metrics = []
            headers = {"X-API-Key": self.api_key}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for request_num in range(requests_per_user):
                    try:
                        start_time = time.time()
                        response = await client.get(
                            f"{self.base_url}/api/v1/auth/status/concurrent_user_{user_id}",
                            headers=headers
                        )
                        response_time = (time.time() - start_time) * 1000
                        
                        metric = PerformanceMetric(
                            test_name="concurrent_users",
                            request_name="auth_status",
                            response_time_ms=response_time,
                            status_code=response.status_code,
                            success=200 <= response.status_code < 400,
                            timestamp=datetime.utcnow(),
                            user_id=f"user_{user_id}",
                            thread_id=threading.get_ident()
                        )
                        user_metrics.append(metric)
                        
                        # Random delay between user requests
                        await asyncio.sleep(0.2 + (user_id * 0.1))
                        
                    except Exception as e:
                        metric = PerformanceMetric(
                            test_name="concurrent_users",
                            request_name="auth_status",
                            response_time_ms=0,
                            status_code=0,
                            success=False,
                            timestamp=datetime.utcnow(),
                            user_id=f"user_{user_id}",
                            thread_id=threading.get_ident()
                        )
                        user_metrics.append(metric)
                        
            return user_metrics
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        start_time = time.time()
        
        # Execute concurrent users
        tasks = [simulate_user(user_id) for user_id in range(num_users)]
        all_metrics = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Stop resource monitoring  
        self.resource_monitor.stop_monitoring()
        
        # Flatten metrics
        flat_metrics = []
        for user_metrics in all_metrics:
            flat_metrics.extend(user_metrics)
            
        # Calculate results
        total_requests = len(flat_metrics)
        successful_requests = len([m for m in flat_metrics if m.success])
        response_times = [m.response_time_ms for m in flat_metrics if m.success]
        
        result = {
            "concurrent_users": num_users,
            "requests_per_user": requests_per_user,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "duration_seconds": end_time - start_time,
            "requests_per_second": total_requests / (end_time - start_time) if (end_time - start_time) > 0 else 0,
            "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "min_response_time_ms": min(response_times) if response_times else 0,
            "resource_usage": self.resource_monitor.get_summary()
        }
        
        print(f"\n📊 Concurrent Users Results:")
        print(f"   Total Requests: {result['total_requests']}")
        print(f"   Successful: {result['successful_requests']}")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Duration: {result['duration_seconds']:.1f}s")
        print(f"   Requests/Second: {result['requests_per_second']:.1f}")
        print(f"   Avg Response Time: {result['avg_response_time_ms']:.1f}ms")
        
        if result['resource_usage']:
            print(f"   CPU Usage: {result['resource_usage']['cpu']['avg']:.1f}% avg, {result['resource_usage']['cpu']['max']:.1f}% max")
            print(f"   Memory Usage: {result['resource_usage']['memory']['avg_percent']:.1f}% avg")
        
        return result
    
    async def run_load_test(self, config: LoadTestConfig) -> LoadTestResult:
        """Run a specific load test configuration"""
        self.print_section(f"Load Test: {config.name}")
        
        print(f"Configuration:")
        print(f"   Concurrent Users: {config.concurrent_users}")
        print(f"   Requests per User: {config.requests_per_user}")  
        print(f"   Ramp-up Time: {config.ramp_up_seconds}s")
        print(f"   Test Duration: {config.test_duration_seconds}s")
        print(f"   Target Endpoint: {config.endpoint}")
        
        all_metrics = []
        errors = []
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        start_time = datetime.utcnow()
        
        async def load_test_user(user_id: int, start_delay: float) -> List[PerformanceMetric]:
            """Single user load test execution"""
            # Wait for ramp-up delay
            await asyncio.sleep(start_delay)
            
            user_metrics = []
            headers = config.headers or {"X-API-Key": self.api_key}
            
            end_time = start_time + timedelta(seconds=config.test_duration_seconds)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                request_count = 0
                
                while datetime.utcnow() < end_time and request_count < config.requests_per_user:
                    try:
                        req_start_time = time.time()
                        
                        if config.method.upper() == "GET":
                            response = await client.get(
                                f"{self.base_url}{config.endpoint}",
                                headers=headers,
                                params=config.params
                            )
                        elif config.method.upper() == "POST":
                            response = await client.post(
                                f"{self.base_url}{config.endpoint}",
                                headers=headers,
                                params=config.params,
                                json={}
                            )
                        
                        response_time = (time.time() - req_start_time) * 1000
                        
                        metric = PerformanceMetric(
                            test_name=config.name,
                            request_name=config.endpoint,
                            response_time_ms=response_time,
                            status_code=response.status_code,
                            success=200 <= response.status_code < 400,
                            timestamp=datetime.utcnow(),
                            user_id=f"load_user_{user_id}",
                            thread_id=threading.get_ident()
                        )
                        user_metrics.append(metric)
                        
                        request_count += 1
                        
                        # Small delay between requests
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        errors.append(f"User {user_id}: {str(e)}")
                        metric = PerformanceMetric(
                            test_name=config.name,
                            request_name=config.endpoint,
                            response_time_ms=0,
                            status_code=0,
                            success=False,
                            timestamp=datetime.utcnow(),
                            user_id=f"load_user_{user_id}",
                            thread_id=threading.get_ident()
                        )
                        user_metrics.append(metric)
                        
            return user_metrics
        
        # Calculate ramp-up delays
        ramp_up_delay = config.ramp_up_seconds / config.concurrent_users if config.concurrent_users > 0 else 0
        
        # Start all users
        tasks = []
        for user_id in range(config.concurrent_users):
            start_delay = user_id * ramp_up_delay
            tasks.append(load_test_user(user_id, start_delay))
        
        # Execute load test
        user_metrics_list = await asyncio.gather(*tasks)
        
        # Stop monitoring
        end_time = datetime.utcnow()
        self.resource_monitor.stop_monitoring()
        
        # Flatten all metrics
        for user_metrics in user_metrics_list:
            all_metrics.extend(user_metrics)
        
        # Calculate results
        total_requests = len(all_metrics)
        successful_requests = len([m for m in all_metrics if m.success])
        failed_requests = total_requests - successful_requests
        
        response_times = [m.response_time_ms for m in all_metrics if m.success and m.response_time_ms > 0]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 2 else max_response_time
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 2 else max_response_time
        else:
            avg_response_time = median_response_time = max_response_time = min_response_time = p95_response_time = p99_response_time = 0
        
        duration_seconds = (end_time - start_time).total_seconds()
        requests_per_second = total_requests / duration_seconds if duration_seconds > 0 else 0
        
        result = LoadTestResult(
            config=config,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response_time,
            median_response_time_ms=median_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            max_response_time_ms=max_response_time,
            min_response_time_ms=min_response_time,
            requests_per_second=requests_per_second,
            errors=errors[:10],  # Keep first 10 errors
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            resource_usage=self.resource_monitor.get_summary()
        )
        
        # Print results
        print(f"\n📊 Load Test Results:")
        print(f"   Total Requests: {result.total_requests}")
        print(f"   Successful: {result.successful_requests}")
        print(f"   Failed: {result.failed_requests}")
        print(f"   Success Rate: {(result.successful_requests / result.total_requests * 100):.1f}%")
        print(f"   Duration: {result.duration_seconds:.1f}s")
        print(f"   Requests/Second: {result.requests_per_second:.1f}")
        print(f"   Avg Response Time: {result.avg_response_time_ms:.1f}ms")
        print(f"   P95 Response Time: {result.p95_response_time_ms:.1f}ms")
        print(f"   Max Response Time: {result.max_response_time_ms:.1f}ms")
        
        if result.resource_usage:
            print(f"   CPU Usage: {result.resource_usage['cpu']['avg']:.1f}% avg, {result.resource_usage['cpu']['max']:.1f}% max")
            print(f"   Memory Usage: {result.resource_usage['memory']['avg_percent']:.1f}% avg")
        
        if result.errors:
            print(f"   Sample Errors: {len(result.errors)} shown")
            for error in result.errors[:3]:
                print(f"     - {error}")
        
        self.test_results.append(result)
        return result
    
    async def run_stress_test(self) -> Dict[str, Any]:
        """Run stress test to find breaking points"""
        self.print_section("Stress Testing - Finding Breaking Points")
        
        # Define stress test configurations with increasing load
        stress_configs = [
            LoadTestConfig("Stress Level 1", 5, 20, 5, 30, "/api/v1/auth/status/stress_user"),
            LoadTestConfig("Stress Level 2", 10, 30, 10, 45, "/api/v1/auth/status/stress_user"), 
            LoadTestConfig("Stress Level 3", 20, 40, 15, 60, "/api/v1/auth/status/stress_user"),
            LoadTestConfig("Stress Level 4", 35, 50, 20, 75, "/api/v1/auth/status/stress_user"),
            LoadTestConfig("Stress Level 5", 50, 60, 25, 90, "/api/v1/auth/status/stress_user")
        ]
        
        stress_results = []
        breaking_point_found = False
        
        for config in stress_configs:
            print(f"\n🔥 Running {config.name}...")
            
            result = await self.run_load_test(config)
            stress_results.append(result)
            
            # Check if this is a breaking point
            success_rate = (result.successful_requests / result.total_requests * 100) if result.total_requests > 0 else 0
            avg_response_time = result.avg_response_time_ms
            
            if success_rate < 90 or avg_response_time > 5000:  # 5 second threshold
                print(f"   🚨 Breaking point detected!")
                print(f"   Success rate dropped to {success_rate:.1f}% or response time exceeded 5000ms ({avg_response_time:.1f}ms)")
                breaking_point_found = True
                break
            
            # Wait between stress levels
            await asyncio.sleep(10)
        
        # Analyze stress test results
        max_concurrent_users = 0
        max_requests_per_second = 0
        
        for result in stress_results:
            if result.successful_requests > 0:
                max_concurrent_users = max(max_concurrent_users, result.config.concurrent_users)
                max_requests_per_second = max(max_requests_per_second, result.requests_per_second)
        
        stress_summary = {
            "breaking_point_found": breaking_point_found,
            "max_concurrent_users_tested": max_concurrent_users,
            "max_requests_per_second_achieved": max_requests_per_second,
            "stress_levels_completed": len(stress_results),
            "results": [asdict(r) for r in stress_results]
        }
        
        print(f"\n🎯 Stress Test Summary:")
        print(f"   Breaking Point Found: {'Yes' if breaking_point_found else 'No'}")
        print(f"   Max Concurrent Users Tested: {max_concurrent_users}")
        print(f"   Max Requests/Second Achieved: {max_requests_per_second:.1f}")
        print(f"   Stress Levels Completed: {len(stress_results)}")
        
        return stress_summary
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.test_results:
            return {"error": "No test results available"}
        
        # Overall statistics
        total_requests = sum(r.total_requests for r in self.test_results)
        total_successful = sum(r.successful_requests for r in self.test_results)
        total_failed = sum(r.failed_requests for r in self.test_results)
        
        all_response_times = []
        for result in self.test_results:
            # Estimate response times from metrics (this is simplified)
            if result.successful_requests > 0:
                all_response_times.extend([result.avg_response_time_ms] * result.successful_requests)
        
        # Calculate percentiles
        if all_response_times:
            overall_avg = statistics.mean(all_response_times)
            overall_p95 = statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) >= 2 else max(all_response_times)
            overall_max = max(all_response_times)
        else:
            overall_avg = overall_p95 = overall_max = 0
        
        report = {
            "summary": {
                "total_tests": len(self.test_results),
                "total_requests": total_requests,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "overall_success_rate": (total_successful / total_requests * 100) if total_requests > 0 else 0,
                "overall_avg_response_time_ms": overall_avg,
                "overall_p95_response_time_ms": overall_p95,
                "overall_max_response_time_ms": overall_max,
                "timestamp": datetime.utcnow().isoformat()
            },
            "test_results": [asdict(result) for result in self.test_results],
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []
        
        if not self.test_results:
            return recommendations
        
        # Analyze response times
        slow_tests = [r for r in self.test_results if r.avg_response_time_ms > 2000]
        if slow_tests:
            recommendations.append(f"Consider optimizing endpoints with slow response times (>{len(slow_tests)} tests exceeded 2000ms)")
        
        # Analyze error rates
        high_error_tests = [r for r in self.test_results if r.failed_requests / r.total_requests > 0.1]
        if high_error_tests:
            recommendations.append(f"Investigate error rates in {len(high_error_tests)} tests (>10% failure rate)")
        
        # Analyze resource usage
        for result in self.test_results:
            if result.resource_usage and "cpu" in result.resource_usage:
                if result.resource_usage["cpu"]["avg"] > 80:
                    recommendations.append("High CPU usage detected - consider scaling or optimizing CPU-intensive operations")
                if result.resource_usage["memory"]["avg_percent"] > 80:
                    recommendations.append("High memory usage detected - investigate potential memory leaks or optimize memory usage")
        
        # General recommendations
        recommendations.extend([
            "Monitor rate limiting compliance to ensure WHOOP API limits are respected",
            "Consider implementing caching for frequently accessed data",
            "Set up monitoring and alerting for production performance metrics",
            "Regularly run performance tests in CI/CD pipeline"
        ])
        
        return recommendations
    
    def export_results(self, filename: Optional[str] = None) -> str:
        """Export performance test results"""
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"whoop_performance_results_{timestamp}.json"
        
        report = self.generate_performance_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filename


class InteractivePerformanceTester:
    """Interactive runner for performance testing"""
    
    def __init__(self):
        self.tester = WhoopPerformanceTester()
    
    async def run(self):
        """Run interactive performance testing menu"""
        print("⚡ WHOOP API Performance & Load Testing Suite")
        print("=" * 60)
        
        await self.show_main_menu()
    
    async def show_main_menu(self):
        """Show main testing menu"""
        while True:
            print(f"\n📋 Performance Testing Menu:")
            print("1.  ⏱️  Response Time Testing")
            print("2.  🚦 Rate Limiting Compliance Testing")
            print("3.  👥 Concurrent Users Testing")
            print("4.  📊 Custom Load Testing")
            print("5.  🔥 Stress Testing (Find Breaking Points)")
            print("6.  🏃‍♂️ Run All Performance Tests")
            print("7.  📈 View Performance Report")
            print("8.  💾 Export Results")
            print("9.  🔄 Clear Results")
            print("10. 🚪 Exit")
            
            choice = input("\nSelect option (1-10): ").strip()
            
            try:
                if choice == "1":
                    await self.tester.test_response_times()
                elif choice == "2":
                    await self.tester.test_rate_limiting_compliance()
                elif choice == "3":
                    await self.test_concurrent_users_menu()
                elif choice == "4":
                    await self.custom_load_test_menu()
                elif choice == "5":
                    await self.tester.run_stress_test()
                elif choice == "6":
                    await self.run_all_tests()
                elif choice == "7":
                    self.view_performance_report()
                elif choice == "8":
                    self.export_results()
                elif choice == "9":
                    self.clear_results()
                elif choice == "10":
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
    
    async def test_concurrent_users_menu(self):
        """Concurrent users testing menu"""
        print("\n👥 Concurrent Users Testing Configuration")
        
        try:
            num_users = int(input("Number of concurrent users (default 5): ") or "5")
            requests_per_user = int(input("Requests per user (default 10): ") or "10")
            
            if num_users > 50:
                confirm = input(f"⚠️  {num_users} users may be high load. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    return
                    
            await self.tester.test_concurrent_users(num_users, requests_per_user)
            
        except ValueError:
            print("❌ Invalid input. Please enter numbers.")
    
    async def custom_load_test_menu(self):
        """Custom load test configuration menu"""
        print("\n📊 Custom Load Test Configuration")
        
        try:
            name = input("Test name: ") or "Custom Load Test"
            concurrent_users = int(input("Concurrent users (default 10): ") or "10")
            requests_per_user = int(input("Requests per user (default 20): ") or "20")
            ramp_up_seconds = int(input("Ramp-up time in seconds (default 10): ") or "10")
            test_duration = int(input("Test duration in seconds (default 60): ") or "60")
            
            print("\nAvailable endpoints:")
            print("1. /api/v1/auth/status/load_test_user (Authentication)")
            print("2. /api/v1/client-status (Client Status)")
            print("3. /api/v1/health-metrics/load_test_user (Health Metrics)")
            print("4. Custom endpoint")
            
            endpoint_choice = input("Select endpoint (1-4): ") or "1"
            
            if endpoint_choice == "1":
                endpoint = "/api/v1/auth/status/load_test_user"
            elif endpoint_choice == "2":
                endpoint = "/api/v1/client-status"
            elif endpoint_choice == "3":
                endpoint = "/api/v1/health-metrics/load_test_user"
            elif endpoint_choice == "4":
                endpoint = input("Enter custom endpoint: ")
            else:
                endpoint = "/api/v1/auth/status/load_test_user"
            
            config = LoadTestConfig(
                name=name,
                concurrent_users=concurrent_users,
                requests_per_user=requests_per_user,
                ramp_up_seconds=ramp_up_seconds,
                test_duration_seconds=test_duration,
                endpoint=endpoint,
                headers={"X-API-Key": self.tester.api_key}
            )
            
            if concurrent_users > 25:
                confirm = input(f"⚠️  {concurrent_users} users may generate high load. Continue? (y/N): ")
                if confirm.lower() != 'y':
                    return
            
            await self.tester.run_load_test(config)
            
        except ValueError:
            print("❌ Invalid input. Please enter valid numbers.")
        except Exception as e:
            print(f"❌ Load test configuration error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all performance tests"""
        print("\n🏃‍♂️ Running All Performance Tests...")
        print("This may take several minutes. Press Ctrl+C to interrupt.")
        
        start_time = time.time()
        
        try:
            # Run tests in sequence
            print("\n1. Response Time Testing...")
            await self.tester.test_response_times()
            
            print("\n2. Rate Limiting Testing...")
            await self.tester.test_rate_limiting_compliance()
            
            print("\n3. Concurrent Users Testing...")
            await self.tester.test_concurrent_users(5, 10)
            
            print("\n4. Load Testing...")
            basic_load_config = LoadTestConfig(
                "Basic Load Test",
                concurrent_users=10,
                requests_per_user=15,
                ramp_up_seconds=10,
                test_duration_seconds=45,
                endpoint="/api/v1/auth/status/full_test_user",
                headers={"X-API-Key": self.tester.api_key}
            )
            await self.tester.run_load_test(basic_load_config)
            
            total_time = time.time() - start_time
            print(f"\n⏱️  All performance tests completed in {total_time:.1f} seconds")
            
            # Show summary
            self.view_performance_report()
            
        except KeyboardInterrupt:
            print("\n⏹️  Performance testing interrupted by user.")
    
    def view_performance_report(self):
        """View performance test report"""
        report = self.tester.generate_performance_report()
        
        if "error" in report:
            print("❌ No performance test results available. Run some tests first.")
            return
        
        summary = report["summary"]
        
        print("\n📈 Performance Test Report")
        print("=" * 50)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"Average Response Time: {summary['overall_avg_response_time_ms']:.1f}ms")
        print(f"95th Percentile Response Time: {summary['overall_p95_response_time_ms']:.1f}ms")
        print(f"Maximum Response Time: {summary['overall_max_response_time_ms']:.1f}ms")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"   {i}. {rec}")
    
    def export_results(self):
        """Export performance results"""
        if not self.tester.test_results:
            print("❌ No results to export. Run some tests first.")
            return
        
        filename = input("Export filename (optional): ").strip()
        
        try:
            exported_file = self.tester.export_results(filename if filename else None)
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
    runner = InteractivePerformanceTester()
    await runner.run()


if __name__ == "__main__":
    print("⚡ WHOOP API Performance & Load Testing Suite")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Performance testing interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")