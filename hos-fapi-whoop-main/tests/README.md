# WHOOP FastAPI Microservice - Testing Suite

Comprehensive testing suite for the WHOOP FastAPI microservice providing OAuth integration, health data retrieval, and database synchronization capabilities.

## 🚀 Quick Start

### Prerequisites

1. **WHOOP API Service Running**
   ```bash
   cd hos-fapi-whoop-main
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

2. **Install Test Dependencies**
   ```bash
   pip install pytest pytest-asyncio httpx structlog psutil
   ```

3. **Environment Configuration**
   ```bash
   # Copy and configure environment variables
   cp .env.example .env
   # Edit .env with your WHOOP API credentials and database settings
   ```

### Run Tests

```bash
# 1. Quick smoke test
python tests/manual_testing_suite.py
# Select option 2: "Test Basic Endpoints"

# 2. Comprehensive automated tests
pytest tests/automated_test_suite.py -v

# 3. Complete testing suite
python tests/manual_testing_suite.py
# Select option 1: "Run Complete Test Suite"
```

## 📁 Test Suite Components

| Test File | Purpose | Usage |
|-----------|---------|-------|
| **manual_testing_suite.py** | 🎮 Interactive manual testing with real scenarios | `python manual_testing_suite.py` |
| **automated_test_suite.py** | 🤖 Automated pytest-compatible test suite | `pytest automated_test_suite.py -v` |
| **postman_collection_equivalent.py** | 📬 Postman-like request collections in Python | `python postman_collection_equivalent.py` |
| **performance_load_tests.py** | ⚡ Performance and load testing with rate limit compliance | `python performance_load_tests.py` |
| **error_edge_case_tests.py** | ⚠️ Error handling and edge case validation | `python error_edge_case_tests.py` |
| **end_to_end_integration_tests.py** | 🔄 Complete workflow integration testing | `python end_to_end_integration_tests.py` |
| **TESTING_GUIDE.md** | 📚 Comprehensive testing documentation | [View Guide](TESTING_GUIDE.md) |

## 🎯 Test Coverage

### API Endpoints Tested

- ✅ **OAuth Flow**: `/api/v1/whoop/auth/oauth-config`, `/api/v1/whoop/auth/authorize`, `/api/v1/whoop/auth/callback`
- ✅ **Data Endpoints**: `/api/v1/data/recovery/{user_id}`, `/api/v1/health-metrics/{user_id}`
- ✅ **Status Endpoints**: `/api/v1/client-status`, `/api/v1/auth/status/{user_id}`
- ✅ **Health Checks**: `/health/ready`, `/health/live`

### Testing Categories

| Category | Coverage | Key Tests |
|----------|----------|-----------|
| **Functionality** | Core API operations | Endpoint responses, data formats |
| **Authentication** | API key validation | Valid/invalid keys, missing auth |
| **OAuth 2.0** | Complete flow with PKCE | Authorization, callback, state management |
| **Data Retrieval** | Health metrics APIs | Recovery, sleep, workout data |
| **Error Handling** | Input validation | Invalid parameters, edge cases |
| **Performance** | Response times & load | Rate limiting, concurrent users |
| **Security** | Vulnerability testing | SQL injection, XSS, input sanitization |
| **Integration** | Database operations | CRUD, data synchronization |

## 📊 Example Test Results

### Manual Testing Suite Output
```bash
🧪 WHOOP FastAPI Microservice - Manual Testing Suite
============================================================

📊 Overall Results:
   Total Tests: 45
   Passed: 42 ✅
   Failed: 3 ❌
   Success Rate: 93.3%
   
🕐 Test completed at: 2024-01-15 14:30:22 UTC
```

### Automated Test Results
```bash
====================== test session starts ======================
collected 38 items

tests/automated_test_suite.py::TestBasicEndpoints::test_root_endpoint PASSED [ 2%]
tests/automated_test_suite.py::TestOAuthFlow::test_oauth_flow_initiation PASSED [ 5%]
tests/automated_test_suite.py::TestDataRetrievalEndpoints::test_health_metrics_basic PASSED [ 8%]
...

====================== 35 passed, 3 failed in 45.23s ======================
```

### Performance Test Results
```bash
⚡ Performance Test Results:
   Response Time - Auth Status: ✅ 245ms (< 1000ms target)
   Response Time - Health Metrics: ✅ 1,234ms (< 2000ms target)
   Concurrent Users (5): ✅ 4.2 req/sec, 98.5% success rate
   Rate Limiting: ✅ Compliant with 100/min limit
```

## 🔧 Configuration

### Environment Variables

```env
# Required for API testing
SERVICE_API_KEY=dev-api-key-change-in-production
API_HOST=0.0.0.0
API_PORT=8001

# Required for OAuth testing
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret
WHOOP_REDIRECT_URL=http://localhost:8001/api/v1/whoop/auth/callback

# Optional for database integration tests
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Test Configuration

```python
# Test Suite Configuration
TEST_CONFIG = {
    "api_base_url": "http://localhost:8001",
    "service_api_key": "dev-api-key-change-in-production",
    "performance_threshold_ms": 2000,
    "rate_limit_test_requests": 10,
    "concurrent_test_count": 5
}
```

## 🎮 Interactive Testing

### Manual Testing Menu
```bash
$ python tests/manual_testing_suite.py

📋 Testing Menu:
1.  🏃‍♂️ Run Complete Test Suite
2.  🔧 Test Basic Endpoints  
3.  🔐 Test OAuth Configuration & Flow
4.  🔑 Test Authentication Endpoints
5.  📊 Test Data Retrieval Endpoints
6.  ⚠️  Test Error Handling
7.  ⚡ Test Rate Limiting & Performance
8.  💾 Test Database Integration
9.  📝 Generate Test Report
10. ⚙️  Configuration & Setup
11. 🚪 Exit

Select option (1-11): 
```

### Postman Collection Equivalent
```bash
$ python tests/postman_collection_equivalent.py

🧪 WHOOP API Postman Collection Equivalent
============================================================

📋 Main Menu (Environment: Development):
1.  🚀 Execute All Collections
2.  📁 Execute Specific Collection
3.  🔍 Execute Single Request
4.  🌍 Switch Environment
5.  🔧 Manage Variables
...
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Ensure API is running on correct port
   curl http://localhost:8001/health/ready
   ```

2. **Authentication Errors**
   ```bash
   # Check API key configuration
   echo $SERVICE_API_KEY
   ```

3. **Database Connection Issues**
   ```bash
   # Verify Supabase credentials
   echo $SUPABASE_URL
   echo $SUPABASE_KEY
   ```

4. **OAuth Configuration Missing**
   ```bash
   # Set WHOOP API credentials
   export WHOOP_CLIENT_ID="your-client-id"
   export WHOOP_CLIENT_SECRET="your-client-secret"
   ```

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python tests/manual_testing_suite.py
```

## 📈 CI/CD Integration

### GitHub Actions Example
```yaml
name: WHOOP API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      env:
        SERVICE_API_KEY: ${{ secrets.SERVICE_API_KEY }}
      run: pytest tests/automated_test_suite.py -v
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
echo "Running WHOOP API smoke tests..."
python tests/manual_testing_suite.py --automated --basic-only
if [ $? -ne 0 ]; then
    echo "❌ Tests failed - commit blocked"
    exit 1
fi
```

## 🏆 Best Practices

### Test Data Management
```python
# Use unique test identifiers
test_user_id = f"test_user_{int(time.time())}"

# Clean up test data
async def cleanup_test_data(user_id: str):
    # Remove test user from all tables
    pass
```

### Test Organization
```python
# Organize tests by functionality
class TestOAuthFlow:
    """Test complete OAuth 2.0 authorization flow"""
    
    def test_oauth_configuration(self):
        """Test OAuth config endpoint"""
        pass
    
    def test_authorization_initiation(self):
        """Test OAuth authorization start"""
        pass
```

### Error Validation
```python
# Validate both success and failure cases
def test_invalid_api_key(self):
    response = self.client.get("/api/v1/client-status", 
                              headers={"X-API-Key": "invalid"})
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()
```

## 📚 Additional Resources

- **[Complete Testing Guide](TESTING_GUIDE.md)** - Comprehensive documentation
- **[API Documentation](../README.md)** - WHOOP API service documentation
- **[Database Schema](../migrations/)** - Database structure and migrations

## 🤝 Contributing

### Adding New Tests

1. **Create test case**: Follow existing patterns in test files
2. **Add to appropriate suite**: Choose manual, automated, or specialized testing
3. **Include documentation**: Add test description and expected behavior
4. **Update this README**: Document new test capabilities

### Test File Structure
```python
# Standard test file structure
class TestCategory:
    """Test category description"""
    
    def setup_method(self):
        """Setup for each test method"""
        pass
    
    def test_specific_functionality(self):
        """Test specific functionality"""
        # Arrange
        # Act  
        # Assert
        pass
```

## 📞 Support

For issues with the testing suite:

1. **Check [TESTING_GUIDE.md](TESTING_GUIDE.md)** for detailed troubleshooting
2. **Review test output** for specific error messages
3. **Verify configuration** - ensure all environment variables are set
4. **Check API service** - confirm WHOOP API is running and accessible

---

**Happy Testing! 🧪**