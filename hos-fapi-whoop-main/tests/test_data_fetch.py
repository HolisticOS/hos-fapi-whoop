"""
Interactive Test Script for WHOOP Data Fetch APIs
Tests the new data fetch endpoints: sleep, workout, recovery, cycle

Usage:
    python tests/test_data_fetch.py
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
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


class DataFetchTester:
    def __init__(self):
        self.jwt_token = None
        self.user_id = None
        self.api_url = "http://localhost:8001"
        self.supabase: Optional[Client] = None

    def print_header(self, message):
        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.BOLD}{message}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")

    def print_success(self, message):
        print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

    def print_error(self, message):
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

    def print_info(self, key, value):
        print(f"{Colors.OKCYAN}  {key}:{Colors.ENDC} {value}")

    def setup(self):
        """Initialize Supabase and get JWT token"""
        self.print_header("🔧 Setup")

        # Load Supabase config
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            self.print_error("Missing SUPABASE_URL or SUPABASE_KEY in .env")
            return False

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            self.print_success("Supabase client initialized")
        except Exception as e:
            self.print_error(f"Failed to initialize Supabase: {e}")
            return False

        # Get credentials
        print(f"\n{Colors.BOLD}Enter Supabase credentials:{Colors.ENDC}")
        email = input("  Email: ").strip()
        password = input("  Password: ").strip()

        # Login
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            self.jwt_token = response.session.access_token
            self.user_id = response.user.id

            self.print_success("Authenticated successfully")
            self.print_info("User ID", self.user_id)
            return True

        except Exception as e:
            self.print_error(f"Authentication failed: {e}")
            return False

    def make_request(self, endpoint: str, params: dict = None):
        """Make authenticated API request"""
        url = f"{self.api_url}/api/v1{endpoint}"
        headers = {"Authorization": f"Bearer {self.jwt_token}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.print_error(f"HTTP {response.status_code}: {response.text}")
            return None
        except Exception as e:
            self.print_error(f"Request failed: {e}")
            return None

    def display_record(self, record: dict, data_type: str):
        """Pretty print a single record"""
        if data_type == "recovery":
            score = record.get("score", {})
            print(f"\n  {Colors.BOLD}Recovery Record:{Colors.ENDC}")
            print(f"    Sleep ID: {record.get('sleep_id', 'N/A')}")
            print(f"    Cycle ID: {record.get('cycle_id', 'N/A')}")
            print(f"    Recovery Score: {score.get('recovery_score', 'N/A')}")
            print(f"    HRV: {score.get('hrv_rmssd_milli', 'N/A')} ms")
            print(f"    Resting HR: {score.get('resting_heart_rate', 'N/A')} bpm")
            print(f"    SpO2: {score.get('spo2_percentage', 'N/A')}%")
            print(f"    Skin Temp: {score.get('skin_temp_celsius', 'N/A')}°C")
            print(f"    Created: {record.get('created_at', 'N/A')}")

        elif data_type == "sleep":
            score = record.get("score", {})
            stage_summary = score.get("stage_summary", {})
            print(f"\n  {Colors.BOLD}Sleep Record:{Colors.ENDC}")
            print(f"    Sleep ID: {record.get('id', 'N/A')}")
            print(f"    Start: {record.get('start', 'N/A')}")
            print(f"    End: {record.get('end', 'N/A')}")
            print(f"    Sleep Efficiency: {score.get('sleep_efficiency_percentage', 'N/A')}%")
            print(f"    Sleep Performance: {score.get('sleep_performance_percentage', 'N/A')}%")
            print(f"    Total In Bed: {stage_summary.get('total_in_bed_time_milli', 0) / 3600000:.1f} hours")
            print(f"    Light Sleep: {stage_summary.get('total_light_sleep_time_milli', 0) / 60000:.0f} min")
            print(f"    REM Sleep: {stage_summary.get('total_rem_sleep_time_milli', 0) / 60000:.0f} min")
            print(f"    Deep Sleep: {stage_summary.get('total_slow_wave_sleep_time_milli', 0) / 60000:.0f} min")

        elif data_type == "workout":
            score = record.get("score", {})
            print(f"\n  {Colors.BOLD}Workout Record:{Colors.ENDC}")
            print(f"    Workout ID: {record.get('id', 'N/A')}")
            print(f"    Sport: {record.get('sport_name', 'N/A')}")
            print(f"    Start: {record.get('start', 'N/A')}")
            print(f"    End: {record.get('end', 'N/A')}")
            print(f"    Strain: {score.get('strain', 'N/A')}")
            print(f"    Kilojoules: {score.get('kilojoule', 'N/A')}")
            print(f"    Avg HR: {score.get('average_heart_rate', 'N/A')} bpm")
            print(f"    Max HR: {score.get('max_heart_rate', 'N/A')} bpm")

        elif data_type == "cycle":
            score = record.get("score", {})
            print(f"\n  {Colors.BOLD}Cycle Record:{Colors.ENDC}")
            print(f"    Cycle ID: {record.get('id', 'N/A')}")
            print(f"    Start: {record.get('start', 'N/A')}")
            print(f"    End: {record.get('end', 'N/A')}")
            print(f"    Strain: {score.get('strain', 'N/A')}")
            print(f"    Kilojoules: {score.get('kilojoule', 'N/A')}")
            print(f"    Avg HR: {score.get('average_heart_rate', 'N/A')} bpm")
            print(f"    Max HR: {score.get('max_heart_rate', 'N/A')} bpm")

    def test_endpoint(self, data_type: str):
        """Test a specific data endpoint"""
        self.print_header(f"📊 Fetch {data_type.title()} Data")

        print(f"\n{Colors.BOLD}Query Options:{Colors.ENDC}")
        print("  1. Latest record (default)")
        print("  2. Multiple recent records")
        print("  3. Date range query")

        choice = input("\nSelect option (1-3): ").strip() or "1"

        params = {}

        if choice == "1":
            # Latest record (default)
            params["limit"] = 1

        elif choice == "2":
            # Multiple records
            limit = input("  Number of records (1-100): ").strip() or "5"
            params["limit"] = int(limit)

        elif choice == "3":
            # Date range
            print(f"\n{Colors.BOLD}Enter date range (YYYY-MM-DD):{Colors.ENDC}")

            # Suggest default dates
            today = datetime.now()
            week_ago = today - timedelta(days=7)

            print(f"  Default: {week_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

            start_date = input(f"  Start date [{week_ago.strftime('%Y-%m-%d')}]: ").strip()
            end_date = input(f"  End date [{today.strftime('%Y-%m-%d')}]: ").strip()
            limit = input("  Limit [10]: ").strip() or "10"

            params["start_date"] = start_date or week_ago.strftime('%Y-%m-%d')
            params["end_date"] = end_date or today.strftime('%Y-%m-%d')
            params["limit"] = int(limit)

        # Make request
        print(f"\n{Colors.OKCYAN}GET /api/v1/data/{data_type}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Params: {json.dumps(params)}{Colors.ENDC}")

        result = self.make_request(f"/data/{data_type}", params)

        if not result:
            return

        # Check if result has expected structure
        if not isinstance(result, dict):
            self.print_error(f"Unexpected response format: {type(result)}")
            print(json.dumps(result, indent=2))
            return

        # Display results
        count = result.get('count', len(result.get('records', [])))
        records = result.get('records', [])

        self.print_success(f"Retrieved {count} {data_type} record(s)")

        if count > 0 and records:
            print(f"\n{Colors.BOLD}Records:{Colors.ENDC}")
            for idx, record in enumerate(records, 1):
                print(f"\n{Colors.HEADER}Record {idx}/{count}{Colors.ENDC}")
                self.display_record(record, data_type)

            # Option to show raw JSON
            show_raw = input(f"\n{Colors.BOLD}Show raw JSON? (y/n):{Colors.ENDC} ").strip().lower()
            if show_raw == 'y':
                print(f"\n{Colors.OKCYAN}{json.dumps(result, indent=2)}{Colors.ENDC}")
        else:
            self.print_error(f"No {data_type} records found")
            print(f"\n{Colors.WARNING}Response:{Colors.ENDC}")
            print(json.dumps(result, indent=2))

    def run(self):
        """Main interactive loop"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 70)
        print("  WHOOP Data Fetch API Tester")
        print("=" * 70)
        print(f"{Colors.ENDC}")

        # Setup
        if not self.setup():
            return

        # Main menu loop
        while True:
            self.print_header("📋 Main Menu")
            print("\nSelect data type to fetch:")
            print("  1. Sleep Data")
            print("  2. Workout Data")
            print("  3. Recovery Data")
            print("  4. Cycle Data")
            print("  5. Exit")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == "1":
                self.test_endpoint("sleep")
            elif choice == "2":
                self.test_endpoint("workout")
            elif choice == "3":
                self.test_endpoint("recovery")
            elif choice == "4":
                self.test_endpoint("cycle")
            elif choice == "5":
                self.print_header("✅ Test Session Complete")
                print("\nAll operations completed!")
                break
            else:
                self.print_error("Invalid option. Please select 1-5.")

            # Continue prompt
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")


if __name__ == "__main__":
    tester = DataFetchTester()
    try:
        tester.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠ Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}✗ Test failed: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
