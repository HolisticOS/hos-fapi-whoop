"""
Quick test script for WHOOP API endpoints
Simple version for quick testing

Usage:
    python tests/quick_test.py
"""

import requests
import json

# UPDATE THESE VALUES
WHOOP_API_URL = "http://localhost:8009"
SUPABASE_JWT_TOKEN = "your_jwt_token_here"  # Get this from well-planned-api login


def test_endpoint(method: str, endpoint: str, **kwargs):
    """Test an API endpoint"""
    url = f"{WHOOP_API_URL}{endpoint}"
    headers = kwargs.pop("headers", {})

    # Add auth header if token is set
    if SUPABASE_JWT_TOKEN and SUPABASE_JWT_TOKEN != "your_jwt_token_here":
        headers["Authorization"] = f"Bearer {SUPABASE_JWT_TOKEN}"

    print(f"\n{'='*60}")
    print(f"{method} {url}")
    print(f"{'='*60}")

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, **kwargs)
        elif method == "POST":
            response = requests.post(url, headers=headers, **kwargs)
        else:
            print(f"Unsupported method: {method}")
            return

        print(f"Status: {response.status_code}")
        print(f"Response:")
        print(json.dumps(response.json(), indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")


def main():
    """Run quick tests"""
    if SUPABASE_JWT_TOKEN == "your_jwt_token_here":
        print("\n⚠️  WARNING: Please update SUPABASE_JWT_TOKEN in the script")
        print("Get your JWT token by logging in via well-planned-api first\n")
        return

    print("\n🧪 WHOOP API Quick Test Suite")
    print("="*60)

    # Test 1: Check WHOOP status
    test_endpoint("GET", "/api/v1/whoop/auth/status")

    # Test 2: Initiate WHOOP OAuth (if needed)
    print("\n📌 To link WHOOP account, uncomment the line below:")
    # test_endpoint("POST", "/api/v1/whoop/auth/login")

    # Test 3: Sync data
    print("\n📌 To sync WHOOP data, uncomment the line below:")
    # test_endpoint("POST", "/api/v1/sync", params={"days_back": 7})

    # Test 4: Get recovery data
    test_endpoint("GET", "/api/v1/data/recovery", params={"days": 7})

    # Test 5: Get sleep data
    test_endpoint("GET", "/api/v1/data/sleep", params={"days": 7})

    # Test 6: Get workout data
    test_endpoint("GET", "/api/v1/data/workouts", params={"days": 7})

    print("\n✅ Tests complete!")


if __name__ == "__main__":
    main()
