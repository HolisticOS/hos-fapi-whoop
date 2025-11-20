"""
Diagnostic script to test WHOOP API date parameters
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.whoop_service import WhoopAPIService
from app.services.auth_service import WhoopAuthService
import structlog

logger = structlog.get_logger(__name__)

async def test_date_parameters():
    """Test different date parameter formats"""

    user_id = input("Enter user ID: ").strip()

    auth_service = WhoopAuthService()
    whoop_service = WhoopAPIService()

    # Check if user is authenticated
    user_info = await auth_service.get_user_info(user_id)
    if not user_info or not user_info.get('is_authenticated'):
        print("❌ User not authenticated. Run the main test first.")
        return

    print("\n" + "="*60)
    print("TESTING SLEEP ENDPOINT WITH DIFFERENT PARAMETERS")
    print("="*60)

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    # Test 1: With ISO date strings
    print("\n[TEST 1] With ISO date strings (start/end)")
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    print(f"  start={start_iso}")
    print(f"  end={end_iso}")

    result = await whoop_service.get_sleep_data(
        user_id=user_id,
        start_date=start_iso,
        end_date=end_iso,
        limit=5
    )
    print(f"  ✅ Result: {len(result.records)} sleep records")

    # Test 2: Without date parameters (just limit)
    print("\n[TEST 2] Without date parameters (limit only)")

    # Directly call the API with minimal params
    from app.services.auth_service import WhoopAuthService
    auth_svc = WhoopAuthService()
    token = await auth_svc.get_valid_token(user_id)

    if token:
        import httpx
        url = "https://api.prod.whoop.com/developer/v2/activity/sleep"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Test with limit only
        params_limit_only = {"limit": 5}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params_limit_only)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Result: {len(data.get('records', []))} sleep records")
                if data.get('records'):
                    print(f"  Sample record ID: {data['records'][0].get('id')}")
            else:
                print(f"  ❌ Error: {response.text}")

        # Test with date parameters
        print("\n[TEST 3] With date parameters (start/end)")
        params_with_dates = {
            "limit": 5,
            "start": start_iso,
            "end": end_iso
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params_with_dates)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Result: {len(data.get('records', []))} sleep records")
            else:
                print(f"  ❌ Error: {response.text}")

    print("\n" + "="*60)
    print("TESTING WORKOUT ENDPOINT")
    print("="*60)

    url = "https://api.prod.whoop.com/developer/v2/activity/workout"

    # Test limit only
    print("\n[TEST 4] Workout with limit only")
    params_limit_only = {"limit": 5}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params_limit_only)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Result: {len(data.get('records', []))} workout records")
            if data.get('records'):
                print(f"  Sample record ID: {data['records'][0].get('id')}")
        else:
            print(f"  ❌ Error: {response.text}")

    # Test with dates
    print("\n[TEST 5] Workout with date parameters")
    params_with_dates = {
        "limit": 5,
        "start": start_iso,
        "end": end_iso
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params_with_dates)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Result: {len(data.get('records', []))} workout records")
        else:
            print(f"  ❌ Error: {response.text}")

    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)
    print("\nConclusion:")
    print("- If TEST 2/4 work but TEST 3/5 fail → Date parameters are the problem")
    print("- If all tests fail → Token/auth issue")
    print("- If all tests pass → Something else is wrong")

if __name__ == "__main__":
    asyncio.run(test_date_parameters())
