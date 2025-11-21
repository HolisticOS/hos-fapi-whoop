"""Quick test to see which server is responding"""
import requests

# Test root endpoint
response = requests.get("http://localhost:8001/")
print("Root endpoint response:")
print(response.json())
print()

# Test if we can reach the docs
try:
    docs_response = requests.get("http://localhost:8001/docs")
    print(f"Docs accessible: {docs_response.status_code == 200}")
except Exception as e:
    print(f"Docs error: {e}")
print()

# Test if we can see OpenAPI spec
try:
    openapi_response = requests.get("http://localhost:8001/openapi.json")
    openapi_data = openapi_response.json()

    # Check if data endpoints are in the spec
    paths = openapi_data.get('paths', {})
    data_endpoints = [path for path in paths.keys() if '/data/' in path]

    print(f"OpenAPI spec accessible: {openapi_response.status_code == 200}")
    print(f"Data endpoints in spec: {data_endpoints}")
except Exception as e:
    print(f"OpenAPI error: {e}")
