#!/usr/bin/env python3
"""
Real User OAuth Integration Test
Tests complete OAuth flow + data fetching with actual WHOOP accounts

Prerequisites:
1. Run database migration: migrations/004_oauth_tables.sql
2. Update WHOOP app redirect URL to: http://localhost:8009/api/v1/auth/callback
3. Server running on port 8009

Usage:
python tests/test_real_user_oauth.py
"""

import asyncio
import sys
import os
import json
import webbrowser
from datetime import datetime, date, timedelta
import httpx
from urllib.parse import parse_qs, urlparse

# Add the app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.auth_service import WhoopAuthService
from app.services.whoop_service import WhoopAPIService
from app.models.database import WhoopDataService
from app.config.database import get_supabase_client
import structlog

# Configure logging
logger = structlog.get_logger(__name__)

class RealUserOAuthTester:
    """Complete OAuth + API testing with real users"""
    
    def __init__(self):
        self.base_url = "http://localhost:8009"  # Your API server
        self.auth_service = WhoopAuthService()
        self.whoop_service = WhoopAPIService()
        self.data_service = WhoopDataService()
        self.supabase = get_supabase_client()
        
    async def check_server_status(self) -> bool:
        """Check if the API server is running"""
        print("🔍 Checking server status...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/whoop/auth/")
                
                if response.status_code == 200:
                    print("✅ Server is running and responding")
                    return True
                else:
                    print(f"❌ Server responded with status {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Server is not responding: {str(e)}")
            print("   Make sure server is running: uvicorn app.main:app --host 0.0.0.0 --port 8009 --reload")
            return False
    
    async def check_database_tables(self) -> bool:
        """Check if OAuth database tables exist"""
        print("🗄️  Checking database tables...")
        
        if not self.supabase:
            print("❌ No Supabase connection")
            return False
        
        try:
            # Check if OAuth tables exist
            tables_to_check = ['whoop_oauth_states', 'whoop_users']
            
            for table in tables_to_check:
                try:
                    result = self.supabase.table(table).select("*").limit(1).execute()
                    print(f"✅ Table {table} exists")
                except Exception as e:
                    if "does not exist" in str(e).lower():
                        print(f"❌ Table {table} missing - run migrations/004_oauth_tables.sql")
                        return False
                    else:
                        print(f"⚠️  Table {table} check failed: {str(e)}")
            
            print("✅ Database tables ready")
            return True
            
        except Exception as e:
            print(f"❌ Database check failed: {str(e)}")
            return False
    
    async def start_oauth_flow(self, user_id: str) -> str:
        """Start OAuth flow and return authorization URL"""
        print(f"🔐 Starting OAuth flow for user: {user_id}")
        
        try:
            # Call login endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/whoop/auth/login",
                    params={"user_id": user_id}
                )
            
            if response.status_code == 200:
                data = response.json()
                auth_url = data["auth_url"]
                
                print(f"✅ OAuth flow initiated")
                print(f"🔗 Authorization URL generated")
                return auth_url
            else:
                print(f"❌ OAuth initiation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ OAuth initiation error: {str(e)}")
            return None
    
    async def wait_for_oauth_completion(self, user_id: str, timeout_minutes: int = 5) -> bool:
        """Wait for user to complete OAuth flow"""
        print(f"⏳ Waiting for OAuth completion (timeout: {timeout_minutes} minutes)")
        print("   Complete the authorization in your browser...")
        print("   Press Ctrl+C to cancel")
        
        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        
        try:
            while datetime.now() - start_time < timeout:
                # Check if user is now authenticated
                try:
                    user_data = self.supabase.table('whoop_users').select('*').eq('whoop_user_id', user_id).execute()
                    
                    if user_data.data:
                        user = user_data.data[0]
                        if user.get('access_token'):
                            print(f"✅ OAuth completed successfully!")
                            print(f"   User {user_id} is now authenticated")
                            return True
                    # Wait a bit before checking again
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    # Continue waiting even if check fails
                    await asyncio.sleep(2)
            
            print(f"⏰ OAuth timeout after {timeout_minutes} minutes")
            return False
        except KeyboardInterrupt:
            print("\n⏹️  OAuth cancelled by user")
            return False
    
    async def test_user_authentication(self, user_id: str) -> bool:
        """Test if user is properly authenticated"""
        print(f"🔐 Testing authentication for user: {user_id}")
        
        try:
            # Check auth status via API
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/whoop/auth/status/{user_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("is_authenticated"):
                    print(f"✅ User is authenticated")
                    print(f"   Token expires: {data.get('token_expires_at')}")
                    print(f"   Has refresh token: {data.get('has_refresh_token')}")
                    return True
                else:
                    print(f"❌ User is not authenticated")
                    return False
            else:
                print(f"❌ Auth status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Auth test error: {str(e)}")
            return False
    
    async def test_whoop_data_fetch(self, user_id: str) -> dict:
        """Test fetching real WHOOP data for authenticated user"""
        print(f"📊 Testing WHOOP data fetch for user: {user_id}")
        
        results = {
            'sleep': None,
            'recovery': None,
            'workout': None,
            'cycles': None,
            'profile': None,
            'body_measurements': None
        }
        
        # Test date range (last 7 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        try:
            # Test sleep data
            print("   😴 Fetching sleep data...")
            sleep_data = await self.whoop_service.get_sleep_data(
                user_id=user_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            if sleep_data and hasattr(sleep_data, 'records') and sleep_data.records:
                results['sleep'] = len(sleep_data.records)
                print(f"   ✅ Sleep data: {len(sleep_data.records)} records")
            else:
                print(f"   ⚠️  Sleep data: No records found")
            
            # Test recovery data
            print("   💪 Fetching recovery data...")
            recovery_data = await self.whoop_service.get_recovery_data(
                user_id=user_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            if recovery_data and hasattr(recovery_data, 'records') and recovery_data.records:
                results['recovery'] = len(recovery_data.records)
                print(f"   ✅ Recovery data: {len(recovery_data.records)} records")
            else:
                print(f"   ⚠️  Recovery data: No records found")
            
            # Test workout data
            print("   🏃 Fetching workout data...")
            workout_data = await self.whoop_service.get_workout_data(
                user_id=user_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            if workout_data and hasattr(workout_data, 'records') and workout_data.records:
                results['workout'] = len(workout_data.records)
                print(f"   ✅ Workout data: {len(workout_data.records)} records")
            else:
                print(f"   ⚠️  Workout data: No records found")
            
            # Test cycles data
            print("   📅 Fetching cycles data...")
            cycles_data = await self.whoop_service.get_cycle_data(
                user_id=user_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            if cycles_data and hasattr(cycles_data, 'data') and cycles_data.data:
                results['cycles'] = len(cycles_data.data)
                print(f"   ✅ Cycles data: {len(cycles_data.data)} records")
            else:
                print(f"   ⚠️  Cycles data: No records found")
            
            # Test profile data
            print("   👤 Fetching profile data...")
            profile_data = await self.whoop_service.get_profile_data(user_id=user_id)
            
            if profile_data:
                results['profile'] = 1
                print(f"   ✅ Profile data: Retrieved")
                print(f"       Name: {profile_data.first_name} {profile_data.last_name}")
                print(f"       Email: {profile_data.email}")
            else:
                print(f"   ⚠️  Profile data: Not found")
            
            # Test body measurements data
            print("   📏 Fetching body measurements...")
            body_data = await self.whoop_service.get_body_measurement_data(user_id=user_id)
            
            if body_data:
                results['body_measurements'] = 1
                print(f"   ✅ Body measurements: Retrieved")
                if body_data.height_meter:
                    print(f"       Height: {body_data.height_meter}m")
                if body_data.weight_kilogram:
                    print(f"       Weight: {body_data.weight_kilogram}kg")
                if body_data.max_heart_rate:
                    print(f"       Max HR: {body_data.max_heart_rate} bpm")
            else:
                print(f"   ⚠️  Body measurements: Not found")
            
            print(f"✅ Complete data fetch test completed")
            return results
            
        except Exception as e:
            print(f"❌ Data fetch failed: {str(e)}")
            return results
    
    async def test_database_storage(self, user_id: str) -> bool:
        """Test storing fetched data in Supabase"""
        print(f"🗄️  Testing database storage for user: {user_id}")
        
        try:
            # Check if we have any stored data
            tables_to_check = ['whoop_sleep_v2', 'whoop_recovery_v2']
            total_records = 0
            
            for table in tables_to_check:
                try:
                    result = self.supabase.table(table).select("*", count="exact").limit(0).execute()
                    count = result.count if hasattr(result, 'count') else 0
                    print(f"   📋 {table}: {count} records")
                    total_records += count
                except Exception as e:
                    print(f"   ❌ {table}: Error checking - {str(e)}")
            
            print(f"✅ Database storage check completed: {total_records} total records")
            return total_records > 0
            
        except Exception as e:
            print(f"❌ Database storage test failed: {str(e)}")
            return False
    
    async def run_complete_user_test(self, user_id: str) -> bool:
        """Run complete test flow for a real user"""
        print("🚀 Starting Complete Real User OAuth Test")
        print("=" * 60)
        
        # Step 1: Check prerequisites
        if not await self.check_server_status():
            return False
        
        if not await self.check_database_tables():
            return False
        
        # Step 2: Check if user is already authenticated
        print(f"\n👤 Testing user: {user_id}")
        is_already_authenticated = await self.test_user_authentication(user_id)
        
        if not is_already_authenticated:
            # Step 3: Start OAuth flow
            auth_url = await self.start_oauth_flow(user_id)
            if not auth_url:
                return False
            
            print(f"\n🌐 Opening authorization URL in browser...")
            print(f"   URL: {auth_url}")
            
            # Try to open browser
            try:
                webbrowser.open(auth_url)
                print("✅ Browser opened - complete OAuth in browser")
            except:
                print("⚠️  Could not open browser automatically")
                print("   Please copy the URL above and open manually")
            
            # Step 4: Wait for OAuth completion
            oauth_success = await self.wait_for_oauth_completion(user_id)
            if not oauth_success:
                return False
        else:
            print("✅ User already authenticated, skipping OAuth flow")
        
        # Step 5: Test authentication
        auth_success = await self.test_user_authentication(user_id)
        if not auth_success:
            return False
        
        # Step 6: Test data fetching
        print(f"\n📊 Testing WHOOP API data access...")
        data_results = await self.test_whoop_data_fetch(user_id)
        
        # Step 7: Test database storage
        storage_success = await self.test_database_storage(user_id)
        
        # Final summary
        print("\n" + "=" * 60)
        print("🎉 REAL USER TEST RESULTS:")
        print(f"✅ User authenticated: {user_id}")
        print(f"📊 Sleep records: {data_results.get('sleep', 0) or 0}")
        print(f"💪 Recovery records: {data_results.get('recovery', 0) or 0}")
        print(f"🏃 Workout records: {data_results.get('workout', 0) or 0}")
        print(f"📅 Cycle records: {data_results.get('cycles', 0) or 0}")
        print(f"👤 Profile data: {'Retrieved' if data_results.get('profile') else 'Not found'}")
        print(f"📏 Body measurements: {'Retrieved' if data_results.get('body_measurements') else 'Not found'}")
        print(f"🗄️  Database storage: {'Working' if storage_success else 'No data'}")
        
        # Check if we got any data at all
        data_retrieved = any([
            data_results.get('sleep', 0),
            data_results.get('recovery', 0), 
            data_results.get('workout', 0),
            data_results.get('cycles', 0),
            data_results.get('profile'),
            data_results.get('body_measurements')
        ])
        
        overall_success = auth_success and data_retrieved
        
        if overall_success:
            print("\n🎉 SUCCESS! Your automated OAuth system is working!")
            print("✅ Users can sign in automatically")
            print("✅ Tokens are stored in database")
            print("✅ Real WHOOP data is accessible")
        else:
            print("\n⚠️  PARTIAL SUCCESS - Check the issues above")
        
        return overall_success

async def main():
    """Main test execution"""
    tester = RealUserOAuthTester()
    
    print("🔑 Real User OAuth Integration Test")
    print("=" * 50)
    
    # Get user ID for testing
    user_id = input("Enter a test user ID (e.g., 'user123'): ").strip()
    if not user_id:
        user_id = "test_user_oauth"
        print(f"Using default user ID: {user_id}")
    
    print(f"\n🎯 Testing with user ID: {user_id}")
    print("This will:")
    print("1. Check server and database")
    print("2. Start OAuth flow (opens browser)")
    print("3. Wait for you to complete OAuth")
    print("4. Test data access with stored tokens")
    print("5. Verify database storage")
    
    continue_test = input("\nContinue? (y/N): ").strip().lower()
    if continue_test != 'y':
        print("Test cancelled.")
        return
    
    # Run complete test
    success = await tester.run_complete_user_test(user_id)
    
    if success:
        print(f"\n🎯 Next Steps:")
        print(f"1. Your OAuth system is ready for production!")
        print(f"2. Users can now sign in at: POST /api/v1/auth/login")
        print(f"3. Data flows automatically from WHOOP → Database")
        print(f"4. Build your app features on top of this foundation")
        
        # Offer to test another user
        another_test = input(f"\nTest another user? (y/N): ").strip().lower()
        if another_test == 'y':
            new_user_id = input("Enter new user ID: ").strip()
            if new_user_id:
                await tester.run_complete_user_test(new_user_id)
    else:
        print(f"\n🔧 Troubleshooting:")
        print(f"1. Ensure database migration is run")
        print(f"2. Check WHOOP app redirect URL configuration")
        print(f"3. Verify server is running on port 8009")
        print(f"4. Check OAuth scopes in WHOOP Developer Portal")

if __name__ == "__main__":
    asyncio.run(main())