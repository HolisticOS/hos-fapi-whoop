"""
Interactive Test Script for WHOOP API
Guides you through the complete authentication and testing flow

Usage:
    python tests/interactive_test.py
"""

import requests
import json
import time
import getpass
import os
from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


class InteractiveWhoopTester:
    def __init__(self):
        self.jwt_token = None
        self.user_id = None
        self.whoop_api_url = None
        self.supabase_url = None
        self.supabase_key = None
        self.supabase: Client = None

    def print_header(self, message):
        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{message}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")

    def print_success(self, message):
        print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

    def print_error(self, message):
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

    def print_warning(self, message):
        print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

    def print_info(self, key, value):
        print(f"{Colors.OKCYAN}  {key}:{Colors.ENDC} {value}")

    def setup_configuration(self):
        """Load configuration from .env file"""
        self.print_header("🔧 Loading Configuration")

        # Load Supabase Configuration from .env
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            self.print_error("Missing Supabase configuration in .env file")
            print(f"\n{Colors.WARNING}Please add the following to your .env file:{Colors.ENDC}")
            print("  SUPABASE_URL=https://your-project.supabase.co")
            print("  SUPABASE_KEY=your_anon_key")
            return False

        self.print_info("Supabase URL", supabase_url[:50] + "...")
        self.print_info("Supabase Key", supabase_key[:30] + "...")

        self.supabase_url = supabase_url
        self.supabase_key = supabase_key

        # Initialize Supabase client
        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.print_success("Supabase client initialized")
        except Exception as e:
            self.print_error(f"Failed to initialize Supabase: {str(e)}")
            return False

        # WHOOP API URL (allow override or use default)
        default_whoop = "http://localhost:8001"
        whoop_from_env = os.getenv("WHOOP_API_URL", default_whoop)

        print(f"\n{Colors.BOLD}WHOOP API URL{Colors.ENDC}")
        print(f"   Press Enter to use: {whoop_from_env}")
        whoop_url = input(f"   Or enter custom URL: ").strip()
        self.whoop_api_url = whoop_url if whoop_url else whoop_from_env

        self.print_success("Configuration loaded!")
        self.print_info("WHOOP API", self.whoop_api_url)
        return True

    def test_api_connectivity(self):
        """Test if WHOOP API is reachable"""
        self.print_header("🔌 Testing API Connectivity")

        # Test WHOOP API
        print(f"\n{Colors.BOLD}Testing WHOOP API...{Colors.ENDC}")
        try:
            response = requests.get(f"{self.whoop_api_url}/", timeout=5)
            if response.status_code == 200:
                self.print_success(f"WHOOP API is reachable (Status: {response.status_code})")
            else:
                self.print_warning(f"WHOOP API responded but with status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.print_error("WHOOP API is NOT reachable")
            self.print_warning("Make sure hos-fapi-whoop is running on the configured port")
            return False
        except Exception as e:
            self.print_error(f"Error connecting to WHOOP API: {str(e)}")
            return False

        return True

    def interactive_login(self):
        """Interactive Supabase login"""
        self.print_header("🔐 Supabase Authentication")

        if not self.supabase:
            self.print_error("Supabase client not initialized")
            return False

        # Get credentials
        print(f"\n{Colors.BOLD}Enter your Supabase credentials:{Colors.ENDC}")
        email = input("  Email: ").strip()
        password = getpass.getpass("  Password: ")

        print(f"\n{Colors.BOLD}Authenticating with Supabase...{Colors.ENDC}")

        try:
            # Sign in with Supabase directly
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.session:
                self.jwt_token = response.session.access_token
                self.user_id = response.user.id if response.user else None

                self.print_success("Successfully authenticated!")
                self.print_info("User ID", self.user_id)
                self.print_info("JWT Token", f"{self.jwt_token[:50]}...")
                return True
            else:
                self.print_error("Authentication failed - no session returned")
                return False

        except Exception as e:
            self.print_error(f"Authentication failed: {str(e)}")
            error_message = str(e).lower()

            if "invalid login credentials" in error_message or "invalid" in error_message:
                self.print_warning("Invalid email or password. Please try again.")
            elif "email not confirmed" in error_message:
                self.print_warning("Please verify your email before signing in.")
            else:
                self.print_warning("Check your Supabase configuration and credentials.")

            return False

    def manual_token_entry(self):
        """Allow manual JWT token entry"""
        self.print_header("🔑 Manual Token Entry")

        print(f"\n{Colors.WARNING}If you already have a JWT token, you can enter it manually{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Otherwise, press Enter to skip{Colors.ENDC}")

        token = input("\nJWT Token: ").strip()

        if token:
            self.jwt_token = token
            self.print_success("Token saved!")
            self.print_info("Token", f"{token[:50]}...")
            return True

        return False

    def check_whoop_status(self):
        """Check WHOOP linkage status"""
        self.print_header("📊 WHOOP Account Status")

        if not self.jwt_token:
            self.print_error("No JWT token available")
            return False

        try:
            url = f"{self.whoop_api_url}/api/v1/whoop/auth/status"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}

            print(f"GET {url}")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                is_authenticated = data.get("is_authenticated", False)
                whoop_user_id = data.get("whoop_user_id")

                self.print_success("Successfully checked WHOOP status")
                self.print_info("WHOOP Linked", "Yes ✓" if is_authenticated else "No ✗")
                if whoop_user_id:
                    self.print_info("WHOOP User ID", whoop_user_id)

                return is_authenticated
            else:
                self.print_error(f"Status check failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return False

    def initiate_whoop_oauth(self):
        """Initiate WHOOP OAuth"""
        self.print_header("🔗 Link WHOOP Account")

        if not self.jwt_token:
            self.print_error("No JWT token available")
            return False

        try:
            url = f"{self.whoop_api_url}/api/v1/whoop/auth/login"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}

            print(f"POST {url}")
            response = requests.post(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                auth_url = data.get("auth_url")

                self.print_success("OAuth initiated successfully!")

                print(f"\n{Colors.WARNING}{'='*70}{Colors.ENDC}")
                print(f"{Colors.BOLD}ACTION REQUIRED:{Colors.ENDC}")
                print(f"\n1. Open this URL in your browser:")
                print(f"{Colors.OKCYAN}{auth_url}{Colors.ENDC}")
                print(f"\n2. Login to WHOOP and authorize access")
                print(f"3. Wait for the success page")
                print(f"{Colors.WARNING}{'='*70}{Colors.ENDC}")

                input(f"\n{Colors.BOLD}Press Enter after completing OAuth...{Colors.ENDC}")

                # Check status after OAuth
                time.sleep(2)
                if self.check_whoop_status():
                    self.print_success("WHOOP account successfully linked!")
                    return True
                else:
                    self.print_warning("WHOOP still not linked - try again")
                    return False
            else:
                self.print_error(f"OAuth initiation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return False

    def sync_data(self):
        """Sync WHOOP data"""
        self.print_header("🔄 Sync WHOOP Data")

        if not self.jwt_token:
            self.print_error("No JWT token available")
            return False

        # Ask how many days
        print(f"\n{Colors.BOLD}How many days of data to sync?{Colors.ENDC}")
        days = input(f"  Days (1-30, default 7): ").strip()
        days_back = int(days) if days and days.isdigit() else 7

        print(f"\n{Colors.OKCYAN}Note: Syncing {days_back} days will fetch individual records for each day{Colors.ENDC}")

        try:
            url = f"{self.whoop_api_url}/api/v1/sync"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            params = {
                "days_back": days_back,
                "data_types": "recovery,sleep,workout,cycle"
            }

            print(f"\nPOST {url}")
            print(f"Syncing {days_back} days of data...")

            response = requests.post(url, headers=headers, params=params, timeout=60)

            if response.status_code == 200:
                data = response.json()
                storage_summary = data.get("storage_summary", {})

                self.print_success("Data sync completed!")
                self.print_info("Recovery records", storage_summary.get("recovery_stored", 0))
                self.print_info("Sleep records", storage_summary.get("sleep_stored", 0))
                self.print_info("Workout records", storage_summary.get("workouts_stored", 0))
                self.print_info("Cycle records", storage_summary.get("cycles_stored", 0))
                self.print_info("Total stored", storage_summary.get("total_stored", 0))
                return True
            else:
                self.print_error(f"Sync failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return False

    def get_recovery_data(self):
        """Get recovery data"""
        self.print_header("💚 Recovery Data")

        if not self.jwt_token:
            self.print_error("No JWT token available")
            return False

        try:
            url = f"{self.whoop_api_url}/api/v1/data/recovery"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            params = {"days": 7}

            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                recovery_count = data.get("summary", {}).get("recovery_records", 0)

                self.print_success(f"Retrieved {recovery_count} recovery records")

                if recovery_count > 0:
                    records = data.get("recovery_data", [])[:3]  # Show first 3
                    for i, record in enumerate(records, 1):
                        print(f"\n  Record {i}:")
                        print(f"    Recovery Score: {record.get('recovery_score', 'N/A')}")
                        print(f"    HRV: {record.get('hrv_rmssd_milli', 'N/A')} ms")
                        print(f"    Resting HR: {record.get('resting_heart_rate', 'N/A')} bpm")
                return True
            else:
                self.print_error(f"Failed: {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return False

    def run_interactive_flow(self):
        """Run the complete interactive flow"""
        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}🚀 WHOOP API Interactive Test Suite{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")

        # Step 1: Configuration
        if not self.setup_configuration():
            self.print_error("\n❌ Configuration failed - please check Supabase credentials")
            return

        # Step 2: Test connectivity
        if not self.test_api_connectivity():
            self.print_error("\n❌ API not reachable - please check WHOOP service is running")
            return

        # Step 3: Authentication
        if not self.interactive_login():
            print(f"\n{Colors.WARNING}Would you like to enter a JWT token manually? (y/n):{Colors.ENDC} ", end="")
            if input().strip().lower() == 'y':
                if not self.manual_token_entry():
                    self.print_error("\n❌ No authentication available - stopping")
                    return
            else:
                self.print_error("\n❌ Authentication required - stopping")
                return

        # Step 4: Check WHOOP status
        is_linked = self.check_whoop_status()

        # Step 5: Link WHOOP if needed
        if not is_linked:
            print(f"\n{Colors.WARNING}WHOOP account not linked. Link it now? (y/n):{Colors.ENDC} ", end="")
            if input().strip().lower() == 'y':
                if not self.initiate_whoop_oauth():
                    self.print_warning("WHOOP not linked - skipping data operations")
                    return

        # Step 6: Sync data
        print(f"\n{Colors.WARNING}Sync WHOOP data? (y/n):{Colors.ENDC} ", end="")
        if input().strip().lower() == 'y':
            self.sync_data()

        # Step 7: Get data
        print(f"\n{Colors.WARNING}Fetch recovery data? (y/n):{Colors.ENDC} ", end="")
        if input().strip().lower() == 'y':
            self.get_recovery_data()

        # Done
        self.print_header("✅ Test Session Complete")
        print(f"\n{Colors.OKGREEN}All operations completed!{Colors.ENDC}\n")


def main():
    tester = InteractiveWhoopTester()
    tester.run_interactive_flow()


if __name__ == "__main__":
    main()
