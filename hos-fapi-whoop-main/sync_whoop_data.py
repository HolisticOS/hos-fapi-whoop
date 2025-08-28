#!/usr/bin/env python3
"""
Sync WHOOP data to Supabase database
"""

import requests
import json
import time

BASE_URL = "http://localhost:8009"
API_KEY = "dev-api-key-change-in-production" 
USER_ID = "test_real_user_001"

def check_auth_status():
    """Check current authentication status and token validity"""
    print("Checking authentication status...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/status/{USER_ID}",
            headers={"X-API-Key": API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            conn_status = data.get("connection_status", {})
            
            print(f"  Connected: {conn_status.get('connected')}")
            print(f"  Status: {conn_status.get('status')}")
            print(f"  Token Valid: {conn_status.get('token_valid')}")
            print(f"  Token Expires: {conn_status.get('token_expires_at')}")
            print(f"  WHOOP User ID: {conn_status.get('whoop_user_id')}")
            
            return conn_status.get('token_valid', False), conn_status.get('can_refresh', False)
        else:
            print(f"  Auth check failed: {response.status_code}")
            return False, False
            
    except Exception as e:
        print(f"  Error checking auth: {e}")
        return False, False

def refresh_token():
    """Attempt to refresh the authentication token"""
    print("Attempting to refresh token...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/whoop/auth/refresh",
            headers={"X-API-Key": API_KEY},
            json={"user_id": USER_ID},
            timeout=30
        )
        
        if response.status_code == 200:
            print("  Token refreshed successfully")
            return True
        else:
            print(f"  Token refresh failed: {response.status_code}")
            print(f"  Details: {response.text}")
            return False
            
    except Exception as e:
        print(f"  Token refresh error: {e}")
        return False

def initiate_oauth_reauth():
    """Initiate OAuth re-authentication flow"""
    print("Initiating OAuth re-authentication...")
    
    try:
        # Start OAuth flow
        oauth_request = {
            "user_id": USER_ID,
            "redirect_uri": f"{BASE_URL}/api/v1/whoop/auth/callback",
            "scopes": ["read:profile", "read:recovery", "read:sleep", "read:cycles", "read:workout", "read:body_measurement"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/whoop/auth/authorize",
            json=oauth_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            auth_url = data.get('authorization_url')
            
            print("OAuth flow initiated")
            print(f"\nAUTHORIZATION URL:")
            print(auth_url)
            print(f"\nINSTRUCTIONS:")
            print("1. Click the URL above (or copy/paste into browser)")
            print("2. Log in to your WHOOP account")
            print("3. Click 'Authorize' to grant permissions") 
            print("4. After authorization, you'll be redirected (may show error page)")
            print("5. Press ENTER here to continue...")
            
            input()  # Wait for user to complete OAuth
            
            # Check if OAuth completed successfully
            print("Checking if OAuth completed...")
            token_valid, _ = check_auth_status()
            
            if token_valid:
                print("OAuth re-authentication successful!")
                return True
            else:
                print("OAuth re-authentication may have failed")
                print("Please ensure you completed the authorization in your browser")
                return False
                
        else:
            print(f"Failed to initiate OAuth: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"OAuth initiation error: {e}")
        return False

def sync_whoop_data(days_back=7, data_types="recovery,sleep,workout"):
    """Sync WHOOP data for the authenticated user"""
    print(f"\nStarting WHOOP data sync for user: {USER_ID}")
    print(f"Data types: {data_types}")
    print(f"Days back: {days_back}")
    print("-" * 50)
    
    try:
        # Call the sync endpoint
        response = requests.post(
            f"{BASE_URL}/api/v1/sync/{USER_ID}",
            headers={"X-API-Key": API_KEY},
            params={
                "data_types": data_types,
                "days_back": days_back,
                "force_refresh": True
            },
            timeout=60  # Sync can take time
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("SYNC SUCCESSFUL!")
            print(f"Sync completed: {json.dumps(data, indent=2)}")
            
            # Show detailed results
            if "whoop_api_data" in data:
                api_data = data["whoop_api_data"]
                summary = api_data.get("summary", {})
                print("\n📊 WHOOP API DATA SUMMARY:")
                print(f"  Cycles: {summary.get('cycles_count', 0)}")
                print(f"  Recovery: {summary.get('recovery_count', 0)}")
                print(f"  Sleep: {summary.get('sleep_count', 0)}")
                print(f"  Workouts: {summary.get('workout_count', 0)}")
                
                # Check if we got empty data
                total_records = sum(summary.values()) if summary else 0
                if total_records == 0:
                    print("\n⚠️ WARNING: No data returned from WHOOP API")
                    print("Possible reasons:")
                    print("- No recent WHOOP activity (try extending days_back)")
                    print("- Token expired (will attempt refresh)")
                    print("- New WHOOP account with no historical data")
                    return False  # Indicate empty data
                else:
                    print(f"\n✅ Successfully fetched {total_records} total records")
                    return True
                    
        elif response.status_code == 404:
            print("❌ User not found or not authenticated")
            print("Run OAuth flow first to authenticate")
            return False
            
        elif response.status_code == 502:
            print("❌ WHOOP API error")
            print(f"Details: {response.text}")
            return False
            
        else:
            print(f"❌ Sync failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        print("Make sure the server is running on http://localhost:8001")
        return False

def check_synced_data():
    """Check what data was synced to database"""
    print("\n🔍 Checking synced data in database...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/health-metrics/{USER_ID}",
            headers={"X-API-Key": API_KEY},
            params={
                "source": "database",  # Get from database only
                "days_back": 7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ DATABASE DATA:")
            
            # Show data counts
            if "data" in data:
                db_data = data["data"]
                print(f"  Recovery records: {len(db_data.get('recovery', []))}")
                print(f"  Sleep records: {len(db_data.get('sleep', []))}")  
                print(f"  Workout records: {len(db_data.get('workouts', []))}")
                
                # Show sample data
                if db_data.get('recovery'):
                    print(f"\n📈 Latest Recovery Score: {db_data['recovery'][0].get('recovery_score', 'N/A')}")
                    
        else:
            print(f"❌ Failed to check database: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    print("WHOOP DATA SYNC TO SUPABASE")
    print("=" * 50)
    
    # 1. Check authentication status
    token_valid, can_refresh = check_auth_status()
    
    # 2. Handle token expiration
    if not token_valid:
        if can_refresh:
            print("\n⚠️ Token expired - attempting refresh...")
            if refresh_token():
                # Re-check status after refresh
                token_valid, _ = check_auth_status()
            else:
                print("❌ Token refresh failed - need OAuth re-authentication")
                token_valid = False
        
        # If still not valid, trigger OAuth re-authentication
        if not token_valid:
            print("\nAuthentication required - starting OAuth flow...")
            if initiate_oauth_reauth():
                token_valid, _ = check_auth_status()
            else:
                print("OAuth re-authentication failed. Cannot proceed with sync.")
                print("\nMANUAL STEPS:")
                print("1. Ensure the server is running")
                print("2. Check your internet connection")
                print("3. Verify WHOOP credentials are correct")
                print("\nCannot proceed with sync. Exiting.")
                exit(1)
    
    # 3. Try sync with current authentication
    print("\n" + "=" * 30)
    success = sync_whoop_data(days_back=30, data_types="recovery,sleep,workout")  # Try 30 days
    
    # 4. If sync failed due to empty data, try token refresh and retry
    if not success and token_valid:
        print("\n🔄 Got empty data - attempting token refresh and retry...")
        if refresh_token():
            print("Token refreshed, retrying sync...")
            success = sync_whoop_data(days_back=30, data_types="recovery,sleep,workout")
    
    # 5. Check what was synced
    if success:
        time.sleep(2)
        check_synced_data()
    else:
        print("\n💡 TROUBLESHOOTING TIPS:")
        print("1. Check your WHOOP app - do you see recent data?")
        print("2. Make sure you've been wearing your WHOOP device")
        print("3. Try running the OAuth flow again if token refresh failed")
        print("4. New WHOOP accounts may not have historical data")
    
    print("\n✅ Sync process completed!")