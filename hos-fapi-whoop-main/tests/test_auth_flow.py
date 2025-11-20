"""
Test script for WHOOP API authentication flow with Supabase JWT
Tests the complete flow: Supabase login -> WHOOP OAuth -> Data sync -> Data retrieval

Prerequisites:
1. well-planned-api running on port 8000
2. hos-fapi-whoop running on port 8009
3. Valid Supabase user credentials
4. WHOOP API credentials configured

Usage:
    python tests/test_auth_flow.py
"""

import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration
WELL_PLANNED_API_URL = "https://well-planned-api.onrender.com"
WHOOP_API_URL = "http://localhost:8001"

# Test user credentials (update with your test user)
TEST_USER_EMAIL = "ksteja99@gmail.com"  # Update this
TEST_USER_PASSWORD = "12345678"   # Update this


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class WhoopAPITester:
    """Test suite for WHOOP API with Supabase authentication"""

    def __init__(self):
        self.jwt_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.whoop_auth_url: Optional[str] = None
        self.test_results = []

    def print_step(self, message: str):
        """Print a test step"""
        print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{message}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}")

    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")
        self.test_results.append(("PASS", message))

    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")
        self.test_results.append(("FAIL", message))

    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

    def print_info(self, key: str, value: Any):
        """Print info key-value pair"""
        print(f"{Colors.OKCYAN}  {key}: {Colors.ENDC}{value}")

    def test_1_supabase_login(self) -> bool:
        """Test 1: Login to Supabase via well-planned-api"""
        self.print_step("Test 1: Authenticate with Supabase")

        try:
            url = f"{WELL_PLANNED_API_URL}/api/auth/login"
            payload = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }

            print(f"POST {url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.jwt_token = data.get("access_token") or data.get("token")
                self.user_id = data.get("user", {}).get("id") if isinstance(data.get("user"), dict) else data.get("user_id")

                if self.jwt_token:
                    self.print_success("Successfully authenticated with Supabase")
                    self.print_info("User ID", self.user_id)
                    self.print_info("JWT Token", f"{self.jwt_token[:50]}...")
                    return True
                else:
                    self.print_error("No JWT token in response")
                    print(f"Response: {json.dumps(data, indent=2)}")
                    return False
            else:
                self.print_error(f"Login failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            self.print_error("Connection failed - is well-planned-api running on port 8000?")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_2_check_whoop_status(self) -> bool:
        """Test 2: Check WHOOP linkage status"""
        self.print_step("Test 2: Check WHOOP Account Linkage Status")

        if not self.jwt_token:
            self.print_error("No JWT token available. Run test 1 first.")
            return False

        try:
            url = f"{WHOOP_API_URL}/api/v1/whoop/auth/status"
            headers = {
                "Authorization": f"Bearer {self.jwt_token}"
            }

            print(f"GET {url}")
            print(f"Headers: Authorization: Bearer {self.jwt_token[:50]}...")

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                is_authenticated = data.get("is_authenticated", False)
                whoop_user_id = data.get("whoop_user_id")

                self.print_success("Successfully checked WHOOP status")
                self.print_info("WHOOP Linked", is_authenticated)
                self.print_info("WHOOP User ID", whoop_user_id or "Not linked")

                if not is_authenticated:
                    self.print_warning("WHOOP account not linked yet. Will test OAuth flow.")

                return True
            else:
                self.print_error(f"Status check failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            self.print_error("Connection failed - is hos-fapi-whoop running on port 8009?")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_3_initiate_whoop_oauth(self) -> bool:
        """Test 3: Initiate WHOOP OAuth flow"""
        self.print_step("Test 3: Initiate WHOOP OAuth Flow")

        if not self.jwt_token:
            self.print_error("No JWT token available. Run test 1 first.")
            return False

        try:
            url = f"{WHOOP_API_URL}/api/v1/whoop/auth/login"
            headers = {
                "Authorization": f"Bearer {self.jwt_token}"
            }

            print(f"POST {url}")
            print(f"Headers: Authorization: Bearer {self.jwt_token[:50]}...")

            response = requests.post(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.whoop_auth_url = data.get("auth_url")

                self.print_success("Successfully initiated WHOOP OAuth")
                self.print_info("Auth URL", self.whoop_auth_url[:100] + "..." if self.whoop_auth_url else "None")

                if self.whoop_auth_url:
                    print(f"\n{Colors.WARNING}{'='*60}{Colors.ENDC}")
                    print(f"{Colors.WARNING}MANUAL STEP REQUIRED:{Colors.ENDC}")
                    print(f"{Colors.WARNING}1. Open this URL in your browser:{Colors.ENDC}")
                    print(f"{Colors.OKCYAN}{self.whoop_auth_url}{Colors.ENDC}")
                    print(f"{Colors.WARNING}2. Authorize WHOOP access{Colors.ENDC}")
                    print(f"{Colors.WARNING}3. Wait for callback to complete{Colors.ENDC}")
                    print(f"{Colors.WARNING}{'='*60}{Colors.ENDC}")

                return True
            else:
                self.print_error(f"OAuth initiation failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_4_wait_for_oauth_completion(self) -> bool:
        """Test 4: Wait for user to complete OAuth flow"""
        self.print_step("Test 4: Waiting for OAuth Completion")

        if not self.jwt_token:
            self.print_error("No JWT token available.")
            return False

        print(f"{Colors.WARNING}Waiting for you to complete the OAuth flow...{Colors.ENDC}")
        print(f"{Colors.WARNING}Press Enter after you've authorized WHOOP access...{Colors.ENDC}")
        input()

        # Check status again
        time.sleep(2)  # Give callback time to process

        try:
            url = f"{WHOOP_API_URL}/api/v1/whoop/auth/status"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                is_authenticated = data.get("is_authenticated", False)

                if is_authenticated:
                    self.print_success("WHOOP account successfully linked!")
                    self.print_info("WHOOP User ID", data.get("whoop_user_id"))
                    return True
                else:
                    self.print_error("WHOOP account not linked yet")
                    print(f"Status: {json.dumps(data, indent=2)}")
                    return False
            else:
                self.print_error(f"Status check failed: {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_5_sync_whoop_data(self) -> bool:
        """Test 5: Sync WHOOP data to database"""
        self.print_step("Test 5: Sync WHOOP Data to Database")

        if not self.jwt_token:
            self.print_error("No JWT token available.")
            return False

        try:
            url = f"{WHOOP_API_URL}/api/v1/sync"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            params = {
                "days_back": 7,
                "data_types": "recovery,sleep,workout,cycle"
            }

            print(f"POST {url}")
            print(f"Params: {json.dumps(params, indent=2)}")

            response = requests.post(url, headers=headers, params=params, timeout=60)

            if response.status_code == 200:
                data = response.json()
                self.print_success("Data sync completed")

                storage_summary = data.get("storage_summary", {})
                self.print_info("Recovery stored", storage_summary.get("recovery_stored", 0))
                self.print_info("Sleep stored", storage_summary.get("sleep_stored", 0))
                self.print_info("Workouts stored", storage_summary.get("workouts_stored", 0))
                self.print_info("Cycles stored", storage_summary.get("cycles_stored", 0))
                self.print_info("Total stored", storage_summary.get("total_stored", 0))

                return True
            else:
                self.print_error(f"Sync failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_6_get_recovery_data(self) -> bool:
        """Test 6: Get recovery data"""
        self.print_step("Test 6: Get Recovery Data")

        if not self.jwt_token:
            self.print_error("No JWT token available.")
            return False

        try:
            url = f"{WHOOP_API_URL}/api/v1/data/recovery"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            params = {"days": 7}

            print(f"GET {url}")
            print(f"Params: {json.dumps(params, indent=2)}")

            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                recovery_count = data.get("summary", {}).get("recovery_records", 0)

                self.print_success(f"Retrieved {recovery_count} recovery records")

                if recovery_count > 0:
                    # Show first record
                    first_record = data.get("recovery_data", [])[0] if data.get("recovery_data") else None
                    if first_record:
                        self.print_info("Latest Recovery Score", first_record.get("recovery_score"))
                        self.print_info("HRV (ms)", first_record.get("hrv_rmssd_milli"))
                        self.print_info("Resting HR", first_record.get("resting_heart_rate"))

                return True
            else:
                self.print_error(f"Failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_7_get_sleep_data(self) -> bool:
        """Test 7: Get sleep data"""
        self.print_step("Test 7: Get Sleep Data")

        if not self.jwt_token:
            self.print_error("No JWT token available.")
            return False

        try:
            url = f"{WHOOP_API_URL}/api/v1/data/sleep"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            params = {"days": 7}

            print(f"GET {url}")

            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                sleep_count = data.get("summary", {}).get("sleep_records", 0)

                self.print_success(f"Retrieved {sleep_count} sleep records")

                if sleep_count > 0:
                    first_record = data.get("sleep_data", [])[0] if data.get("sleep_data") else None
                    if first_record:
                        total_sleep_ms = first_record.get("total_sleep_time_milli", 0)
                        total_sleep_hours = total_sleep_ms / (1000 * 60 * 60)
                        self.print_info("Latest Sleep Duration", f"{total_sleep_hours:.2f} hours")

                return True
            else:
                self.print_error(f"Failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def test_8_get_workout_data(self) -> bool:
        """Test 8: Get workout data"""
        self.print_step("Test 8: Get Workout Data")

        if not self.jwt_token:
            self.print_error("No JWT token available.")
            return False

        try:
            url = f"{WHOOP_API_URL}/api/v1/data/workouts"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            params = {"days": 7}

            print(f"GET {url}")

            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                workout_count = data.get("summary", {}).get("workout_records", 0)

                self.print_success(f"Retrieved {workout_count} workout records")

                if workout_count > 0:
                    first_record = data.get("workout_data", [])[0] if data.get("workout_data") else None
                    if first_record:
                        self.print_info("Latest Strain Score", first_record.get("strain_score"))
                        self.print_info("Sport", first_record.get("sport_name", "Unknown"))

                return True
            else:
                self.print_error(f"Failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

    def print_summary(self):
        """Print test summary"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

        passed = sum(1 for status, _ in self.test_results if status == "PASS")
        failed = sum(1 for status, _ in self.test_results if status == "FAIL")
        total = len(self.test_results)

        for status, message in self.test_results:
            if status == "PASS":
                print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

        print(f"\n{Colors.BOLD}Total: {total} | Passed: {passed} | Failed: {failed}{Colors.ENDC}")

        if failed == 0:
            print(f"{Colors.OKGREEN}All tests passed! 🎉{Colors.ENDC}\n")
        else:
            print(f"{Colors.FAIL}Some tests failed. Please review the errors above.{Colors.ENDC}\n")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}WHOOP API Test Suite with Supabase Authentication{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

        print(f"{Colors.OKCYAN}Configuration:{Colors.ENDC}")
        print(f"  Well-Planned API: {WELL_PLANNED_API_URL}")
        print(f"  WHOOP API: {WHOOP_API_URL}")
        print(f"  Test User: {TEST_USER_EMAIL}")

        # Run tests
        if not self.test_1_supabase_login():
            self.print_warning("Stopping tests - Supabase login failed")
            self.print_summary()
            return

        self.test_2_check_whoop_status()

        # Ask if user wants to run OAuth flow
        print(f"\n{Colors.WARNING}Do you want to test the WHOOP OAuth flow? (y/n): {Colors.ENDC}", end="")
        response = input().strip().lower()

        if response == 'y':
            if self.test_3_initiate_whoop_oauth():
                if self.test_4_wait_for_oauth_completion():
                    # OAuth successful, continue with data tests
                    self.test_5_sync_whoop_data()
                    self.test_6_get_recovery_data()
                    self.test_7_get_sleep_data()
                    self.test_8_get_workout_data()
        else:
            # Check if already linked, if so run data tests
            url = f"{WHOOP_API_URL}/api/v1/whoop/auth/status"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200 and response.json().get("is_authenticated"):
                self.print_info("WHOOP already linked", "Proceeding with data tests")
                self.test_5_sync_whoop_data()
                self.test_6_get_recovery_data()
                self.test_7_get_sleep_data()
                self.test_8_get_workout_data()
            else:
                self.print_warning("WHOOP not linked - skipping data tests")

        self.print_summary()


def main():
    """Main entry point"""
    # Check if user has updated credentials
    if TEST_USER_EMAIL == "test@example.com" or TEST_USER_PASSWORD == "your_password":
        print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.FAIL}ERROR: Please update test credentials in the script{Colors.ENDC}")
        print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}\n")
        print(f"Edit the file and update:")
        print(f"  TEST_USER_EMAIL = 'your_actual_email@example.com'")
        print(f"  TEST_USER_PASSWORD = 'your_actual_password'\n")
        return

    tester = WhoopAPITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
