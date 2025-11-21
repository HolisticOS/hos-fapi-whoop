"""
Interactive Test Script for WHOOP Health Insights API (Gemini-powered)
Login with email/password to automatically get JWT token and test the insights API

Usage:
    python test_insights.py
"""

import requests
import json
import os
from datetime import datetime
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


class InsightsTester:
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

    def print_warning(self, message):
        print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

    def setup(self):
        """Initialize Supabase and get JWT token"""
        self.print_header("🔧 Setup & Authentication")

        # Load Supabase config
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            self.print_error("Missing SUPABASE_URL or SUPABASE_KEY in .env")
            print(f"\n{Colors.WARNING}Please add these to your .env file:{Colors.ENDC}")
            print("  SUPABASE_URL=https://your-project.supabase.co")
            print("  SUPABASE_KEY=your_anon_key")
            return False

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            self.print_success("Supabase client initialized")
        except Exception as e:
            self.print_error(f"Failed to initialize Supabase: {e}")
            return False

        # Get credentials
        print(f"\n{Colors.BOLD}Enter your Supabase login credentials:{Colors.ENDC}")
        email = input("  Email: ").strip()
        password = input("  Password: ").strip()

        if not email or not password:
            self.print_error("Email and password are required")
            return False

        # Login
        try:
            print(f"\n{Colors.OKCYAN}Authenticating...{Colors.ENDC}")
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            self.jwt_token = response.session.access_token
            self.user_id = response.user.id

            self.print_success("Authenticated successfully!")
            self.print_info("User ID", self.user_id)
            self.print_info("Token", f"{self.jwt_token[:30]}...")
            return True

        except Exception as e:
            self.print_error(f"Authentication failed: {e}")
            return False

    def check_server(self):
        """Check if API server is running"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                self.print_success(f"API server is running at {self.api_url}")
                return True
            else:
                self.print_error(f"Server returned {response.status_code}")
                return False
        except requests.ConnectionError:
            self.print_error(f"Cannot connect to API server at {self.api_url}")
            self.print_warning("Make sure the server is running:")
            self.print_warning("  ./venv-whoop/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload")
            return False
        except Exception as e:
            self.print_error(f"Server check failed: {e}")
            return False

    def test_insights(self, days_back=7):
        """Test the insights endpoint"""
        self.print_header(f"🤖 Generate Health Insights ({days_back} days)")

        url = f"{self.api_url}/api/v1/data/insights"
        headers = {"Authorization": f"Bearer {self.jwt_token}"}
        params = {"days_back": days_back}

        print(f"\n{Colors.OKCYAN}GET /api/v1/data/insights?days_back={days_back}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}Requesting insights from Gemini AI...{Colors.ENDC}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)

            if response.status_code == 200:
                result = response.json()
                self.display_insights(result)
                return result
            elif response.status_code == 400:
                self.print_error("Bad request - check GEMINI_API_KEY configuration")
                print(f"\n{Colors.WARNING}Response:{Colors.ENDC}")
                print(json.dumps(response.json(), indent=2))
                return None
            elif response.status_code == 401:
                self.print_error("Unauthorized - JWT token is invalid or expired")
                return None
            elif response.status_code == 403:
                self.print_error("Forbidden - WHOOP connection not active")
                self.print_warning("Make sure you have connected your WHOOP account")
                return None
            elif response.status_code == 500:
                self.print_error("Server error during insights generation")
                print(f"\n{Colors.WARNING}Response:{Colors.ENDC}")
                print(json.dumps(response.json(), indent=2))
                return None
            else:
                self.print_error(f"Unexpected status code: {response.status_code}")
                print(response.text)
                return None

        except requests.exceptions.Timeout:
            self.print_error("Request timed out - Gemini API may be slow")
            self.print_warning("This can happen if:")
            self.print_warning("  1. GEMINI_API_KEY is invalid")
            self.print_warning("  2. Gemini API is rate-limited")
            self.print_warning("  3. Large amount of data is being processed")
            return None
        except Exception as e:
            self.print_error(f"Request failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def display_insights(self, result):
        """Pretty print insights results"""
        self.print_success("Insights generated successfully!")

        # Date range
        print(f"\n{Colors.BOLD}📅 Date Range:{Colors.ENDC}")
        date_range = result.get('date_range', {})
        print(f"  Start: {date_range.get('start')}")
        print(f"  End: {date_range.get('end')}")
        print(f"  Days: {date_range.get('days')}")

        # Quality & Model
        print(f"\n{Colors.BOLD}📊 Data Quality:{Colors.ENDC} {result.get('data_quality')}")
        print(f"{Colors.BOLD}🤖 Model Used:{Colors.ENDC} {result.get('model')}")
        print(f"{Colors.BOLD}🕒 Generated:{Colors.ENDC} {result.get('generated_at')}")

        # Summary
        summary = result.get('summary', '')
        if summary:
            print(f"\n{Colors.BOLD}{Colors.OKGREEN}📝 Summary:{Colors.ENDC}")
            print(f"  {summary}")

        # Insights
        insights = result.get('insights', [])
        if insights:
            print(f"\n{Colors.BOLD}{Colors.OKCYAN}💡 Key Insights ({len(insights)}):{Colors.ENDC}")
            for i, insight in enumerate(insights, 1):
                print(f"  {i}. {insight}")

        # Recommendations
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n{Colors.BOLD}{Colors.WARNING}🎯 Recommendations ({len(recommendations)}):{Colors.ENDC}")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

        # Trends
        trends = result.get('trends', {})
        if trends:
            print(f"\n{Colors.BOLD}📈 Trends:{Colors.ENDC}")
            print(f"  Recovery: {trends.get('recovery')}")
            print(f"  Sleep: {trends.get('sleep')}")
            print(f"  Strain: {trends.get('strain')}")
            print(f"  Overall: {trends.get('overall')}")

    def run(self):
        """Main interactive loop"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 70)
        print("  WHOOP Health Insights API Tester (Gemini-powered)")
        print("=" * 70)
        print(f"{Colors.ENDC}")

        # Setup & Login
        if not self.setup():
            return

        # Check server
        print()
        if not self.check_server():
            return

        # Main menu loop
        while True:
            self.print_header("📋 Main Menu")
            print("\nSelect an option:")
            print("  1. Generate insights (7 days)")
            print("  2. Generate insights (14 days)")
            print("  3. Generate insights (30 days)")
            print("  4. Custom days")
            print("  5. View last result (raw JSON)")
            print("  6. Exit")

            choice = input("\nSelect option (1-6): ").strip()

            if choice == "1":
                self.last_result = self.test_insights(days_back=7)
            elif choice == "2":
                self.last_result = self.test_insights(days_back=14)
            elif choice == "3":
                self.last_result = self.test_insights(days_back=30)
            elif choice == "4":
                try:
                    days = int(input("Enter number of days (1-30): ").strip())
                    if 1 <= days <= 30:
                        self.last_result = self.test_insights(days_back=days)
                    else:
                        self.print_error("Days must be between 1 and 30")
                except ValueError:
                    self.print_error("Invalid number")
            elif choice == "5":
                if hasattr(self, 'last_result') and self.last_result:
                    print(f"\n{Colors.OKCYAN}{json.dumps(self.last_result, indent=2)}{Colors.ENDC}")
                else:
                    self.print_warning("No results yet. Generate insights first.")
            elif choice == "6":
                self.print_header("✅ Test Session Complete")
                print("\nThank you for testing the WHOOP Insights API! 🎉")
                break
            else:
                self.print_error("Invalid option. Please select 1-6.")

            # Continue prompt
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")


if __name__ == "__main__":
    tester = InsightsTester()
    try:
        tester.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠ Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}✗ Test failed: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
