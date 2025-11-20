"""
WHOOP User Login and Daily Data Fetch Test
============================================
This script:
1. Initiates OAuth flow for WHOOP account connection
2. Fetches current day recovery, sleep, and workout data
3. Saves results to a text file

Usage:
    python tests/test_user_daily_data.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.whoop_service import WhoopAPIService
from app.services.auth_service import WhoopAuthService
from app.config.settings import settings
import structlog

logger = structlog.get_logger(__name__)


class WhoopDailyDataTest:
    """Test script for WHOOP OAuth and daily data fetching"""

    def __init__(self):
        self.auth_service = WhoopAuthService()
        self.whoop_service = WhoopAPIService()
        self.output_folder = Path(__file__).parent.parent / "test_output"
        self.output_folder.mkdir(exist_ok=True)

    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "="*60)
        print(f"  {text}")
        print("="*60 + "\n")

    def print_step(self, step_num, text):
        """Print formatted step"""
        print(f"\n[STEP {step_num}] {text}")
        print("-" * 60)

    async def start_oauth_flow(self, user_id: str):
        """
        Step 1: Initiate OAuth flow and get authorization URL
        """
        self.print_step(1, "Starting OAuth Authorization Flow")

        try:
            # Generate authorization URL using auth_service
            oauth_data = await self.auth_service.initiate_oauth(user_id)
            auth_url = oauth_data['auth_url']
            state = oauth_data['state']

            print(f"\n✅ Authorization URL generated successfully!")
            print(f"🔐 State: {state}")
            print(f"\n📋 Your WHOOP Authorization URL:")
            print(f"\n{auth_url}\n")
            print("👉 Please:")
            print("   1. Copy the URL above")
            print("   2. Paste it in your browser")
            print("   3. Log in to your WHOOP account")
            print("   4. Authorize the application")
            print("   5. You'll be redirected to a callback URL")
            print("   6. Copy the FULL callback URL from your browser")

            # Store state for callback verification
            self.oauth_state = state
            return True

        except Exception as e:
            print(f"\n❌ Failed to generate authorization URL: {e}")
            logger.error("OAuth flow failed", error=str(e))
            return False

    async def handle_callback(self, user_id: str, callback_url: str):
        """
        Step 2: Handle OAuth callback and exchange code for tokens
        """
        self.print_step(2, "Processing OAuth Callback")

        try:
            # Extract authorization code from callback URL
            if "code=" not in callback_url:
                print("❌ Invalid callback URL - no authorization code found")
                return False

            # Parse the code and state from URL
            import urllib.parse
            parsed = urllib.parse.urlparse(callback_url)
            params = urllib.parse.parse_qs(parsed.query)

            code = params.get('code', [None])[0]
            state = params.get('state', [None])[0]

            if not code:
                print("❌ No authorization code in callback URL")
                return False

            print(f"📝 Authorization code extracted: {code[:20]}...")
            print(f"🔐 State: {state}")
            print("🔄 Exchanging code for access token...")

            # Exchange code for tokens using auth_service
            result = await self.auth_service.handle_callback(
                code=code,
                state=state
            )

            if result:
                print("\n✅ Successfully connected to WHOOP account!")
                print(f"   Access token received and stored in database")
                return True
            else:
                print("\n❌ Failed to exchange code for tokens")
                return False

        except Exception as e:
            print(f"\n❌ Error processing callback: {e}")
            logger.error("Callback handling failed", error=str(e))
            import traceback
            traceback.print_exc()
            return False

    async def fetch_daily_data(self, user_id: str):
        """
        Step 3: Fetch today's recovery, sleep, and workout data
        """
        self.print_step(3, "Fetching Today's Health Data")

        try:
            # Calculate date range (last 7 days for more data)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)  # Get last 7 days

            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()

            print(f"📅 Fetching data from: {start_date.strftime('%Y-%m-%d %H:%M')} UTC")
            print(f"                  to: {end_date.strftime('%Y-%m-%d %H:%M')} UTC\n")

            # Fetch recovery data
            print("🔄 Fetching recovery data...")
            recovery_collection = await self.whoop_service.get_recovery_data(
                user_id=user_id,
                start_date=start_iso,
                end_date=end_iso,
                limit=10  # Get up to 10 recent records
            )

            # Fetch sleep data
            print("🔄 Fetching sleep data...")
            sleep_collection = await self.whoop_service.get_sleep_data(
                user_id=user_id,
                start_date=start_iso,
                end_date=end_iso,
                limit=10  # Get up to 10 recent records
            )

            # Fetch workout data
            print("🔄 Fetching workout data...")
            workout_collection = await self.whoop_service.get_workout_data(
                user_id=user_id,
                start_date=start_iso,
                end_date=end_iso,
                limit=10  # Get up to 10 recent records
            )

            # Fetch cycle data (includes strain and potentially step count)
            print("🔄 Fetching cycle data (strain & activity)...")
            cycle_collection = await self.whoop_service.get_cycle_data(
                user_id=user_id,
                start_date=start_iso,
                end_date=end_iso,
                limit=10  # Get up to 10 recent records
            )

            print("\n✅ Data fetching completed!")
            print(f"   Recovery records: {len(recovery_collection.records)}")
            print(f"   Sleep records: {len(sleep_collection.records)}")
            print(f"   Workout records: {len(workout_collection.records)}")
            print(f"   Cycle records: {len(cycle_collection.data) if cycle_collection else 0}")

            return {
                'recovery': recovery_collection.records,
                'sleep': sleep_collection.records,
                'workouts': workout_collection.records,
                'cycles': cycle_collection.data if cycle_collection else [],
                'fetch_time': datetime.now(timezone.utc)
            }

        except Exception as e:
            print(f"\n❌ Error fetching data: {e}")
            logger.error("Data fetch failed", error=str(e))
            return None

    def format_recovery_data(self, recovery_records):
        """Format recovery data for display"""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("RECOVERY DATA")
        lines.append("="*60)

        if not recovery_records:
            lines.append("\nNo recovery data found for today.")
            return "\n".join(lines)

        for i, record in enumerate(recovery_records, 1):
            lines.append(f"\n--- Recovery Record {i} ---")
            lines.append(f"Cycle ID: {record.cycle_id}")
            lines.append(f"Recovery Score: {record.recovery_score}%")
            lines.append(f"HRV (RMSSD): {record.hrv_rmssd} ms")
            lines.append(f"Resting Heart Rate: {record.resting_heart_rate} bpm")
            lines.append(f"Recorded At: {record.recorded_at}")

        return "\n".join(lines)

    def format_sleep_data(self, sleep_records):
        """Format sleep data for display"""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("SLEEP DATA")
        lines.append("="*60)

        if not sleep_records:
            lines.append("\nNo sleep data found for today.")
            return "\n".join(lines)

        for i, record in enumerate(sleep_records, 1):
            lines.append(f"\n--- Sleep Record {i} ---")
            lines.append(f"Sleep ID: {record.id}")
            lines.append(f"Start: {record.start}")
            lines.append(f"End: {record.end}")

            # Calculate duration in hours
            if record.total_sleep_time_milli:
                hours = record.total_sleep_time_milli / (1000 * 60 * 60)
                lines.append(f"Total Sleep Time: {hours:.2f} hours")

            if record.time_in_bed_milli:
                hours = record.time_in_bed_milli / (1000 * 60 * 60)
                lines.append(f"Time in Bed: {hours:.2f} hours")

            lines.append(f"Cycle ID: {record.cycle_id}")

        return "\n".join(lines)

    def format_workout_data(self, workout_records):
        """Format workout data for display"""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("WORKOUT DATA")
        lines.append("="*60)

        if not workout_records:
            lines.append("\nNo workout data found for today.")
            return "\n".join(lines)

        for i, record in enumerate(workout_records, 1):
            lines.append(f"\n--- Workout Record {i} ---")
            lines.append(f"Workout ID: {record.id}")
            lines.append(f"Sport: {record.sport_name or 'Unknown'} (ID: {record.sport_id})")
            lines.append(f"Start: {record.start}")
            lines.append(f"End: {record.end}")
            lines.append(f"Strain Score: {record.strain_score if record.strain_score else 'N/A'}")
            lines.append(f"Average Heart Rate: {record.average_heart_rate if record.average_heart_rate else 'N/A'} bpm")
            lines.append(f"Max Heart Rate: {record.max_heart_rate if record.max_heart_rate else 'N/A'} bpm")

            # Convert kilojoules to calories (1 kJ = 0.239 kcal)
            if record.calories_burned:
                calories = record.calories_burned * 0.239
                lines.append(f"Calories: {calories:.1f} kcal ({record.calories_burned:.1f} kJ)")
            else:
                lines.append(f"Calories: N/A")

            if record.distance_meters:
                km = record.distance_meters / 1000
                lines.append(f"Distance: {km:.2f} km")

        return "\n".join(lines)

    def format_cycle_data(self, cycle_records):
        """Format cycle data for display (includes strain and activity)"""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("CYCLE DATA (Daily Strain & Activity)")
        lines.append("="*60)

        if not cycle_records:
            lines.append("\nNo cycle data found for today.")
            return "\n".join(lines)

        for i, record in enumerate(cycle_records, 1):
            lines.append(f"\n--- Cycle Record {i} ---")
            lines.append(f"Cycle ID: {record.id}")
            lines.append(f"Start: {record.start}")
            lines.append(f"End: {record.end if record.end else 'Ongoing'}")
            lines.append(f"Score State: {record.score_state if record.score_state else 'N/A'}")

            # Extract score data if available
            if record.score:
                score = record.score
                lines.append(f"Day Strain: {score.get('strain', 'N/A')}")
                lines.append(f"Kilojoules: {score.get('kilojoule', 'N/A')}")

                # Check for average heart rate
                if score.get('average_heart_rate'):
                    lines.append(f"Average Heart Rate: {score['average_heart_rate']} bpm")

            # Check raw_data for additional metrics
            if record.raw_data:
                raw = record.raw_data
                # Some WHOOP integrations may include step count
                if 'steps' in raw:
                    lines.append(f"Steps: {raw['steps']}")
                if raw.get('score', {}).get('activity_stats'):
                    stats = raw['score']['activity_stats']
                    if 'total_steps' in stats:
                        lines.append(f"Total Steps: {stats['total_steps']}")

        return "\n".join(lines)

    def save_results(self, user_id: str, data: dict):
        """
        Step 4: Save results to text file
        """
        self.print_step(4, "Saving Results to File")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"whoop_daily_data_{user_id}_{timestamp}.txt"
            filepath = self.output_folder / filename

            with open(filepath, 'w') as f:
                # Header
                f.write("="*60 + "\n")
                f.write("WHOOP DAILY DATA TEST RESULTS\n")
                f.write("="*60 + "\n")
                f.write(f"User ID: {user_id}\n")
                f.write(f"Fetch Time: {data['fetch_time'].strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
                f.write(f"API Version: v2\n")

                # Recovery data
                f.write(self.format_recovery_data(data['recovery']))

                # Sleep data
                f.write(self.format_sleep_data(data['sleep']))

                # Workout data
                f.write(self.format_workout_data(data['workouts']))

                # Cycle data
                f.write(self.format_cycle_data(data['cycles']))

                # Raw JSON data (for debugging)
                f.write("\n\n" + "="*60)
                f.write("\nRAW DATA (JSON)")
                f.write("\n" + "="*60 + "\n")

                f.write("\n--- Recovery Raw Data ---\n")
                f.write(json.dumps(
                    [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in data['recovery']],
                    indent=2,
                    default=str
                ))

                f.write("\n\n--- Sleep Raw Data ---\n")
                f.write(json.dumps(
                    [s.model_dump() if hasattr(s, 'model_dump') else s.dict() for s in data['sleep']],
                    indent=2,
                    default=str
                ))

                f.write("\n\n--- Workout Raw Data ---\n")
                f.write(json.dumps(
                    [w.model_dump() if hasattr(w, 'model_dump') else w.dict() for w in data['workouts']],
                    indent=2,
                    default=str
                ))

                f.write("\n\n--- Cycle Raw Data ---\n")
                # Handle both Pydantic models and regular objects
                cycle_data = []
                for c in data['cycles']:
                    if hasattr(c, 'model_dump'):
                        cycle_data.append(c.model_dump())
                    elif hasattr(c, 'dict'):
                        cycle_data.append(c.dict())
                    else:
                        cycle_data.append(c.__dict__)
                f.write(json.dumps(cycle_data, indent=2, default=str))

            print(f"\n✅ Results saved successfully!")
            print(f"📁 File location: {filepath}")
            print(f"📊 File size: {filepath.stat().st_size} bytes")

            return filepath

        except Exception as e:
            print(f"\n❌ Error saving results: {e}")
            return None

    async def run_interactive_test(self):
        """Run the interactive test flow"""
        self.print_header("WHOOP User Login and Daily Data Test")

        print("This script will:")
        print("  1. Connect your WHOOP account via OAuth")
        print("  2. Fetch today's recovery, sleep, and workout data")
        print("  3. Save results to a text file")

        # Get user ID
        print("\n" + "-"*60)
        user_id = input("\nEnter a User ID for testing (e.g., 'test_user_001'): ").strip()

        if not user_id:
            print("❌ User ID is required. Exiting.")
            return

        # Check if already connected
        print(f"\n🔍 Checking if user '{user_id}' is already connected...")
        user_info = await self.auth_service.get_user_info(user_id)
        is_connected = user_info and user_info.get('is_authenticated') and not user_info.get('is_token_expired')

        if is_connected:
            print("✅ User is already connected to WHOOP!")
            reconnect = input("\nDo you want to reconnect? (y/n): ").strip().lower()

            if reconnect != 'y':
                print("\n📊 Proceeding to fetch data with existing connection...")
            else:
                # Start OAuth flow
                success = await self.start_oauth_flow(user_id)
                if not success:
                    return

                # Wait for callback URL
                callback_url = input("\n👉 Paste the full callback URL here: ").strip()

                # Handle callback
                success = await self.handle_callback(user_id, callback_url)
                if not success:
                    return
        else:
            print("❌ User is not connected. Starting OAuth flow...\n")

            # Start OAuth flow
            success = await self.start_oauth_flow(user_id)
            if not success:
                return

            # Wait for callback URL
            callback_url = input("\n👉 Paste the full callback URL here: ").strip()

            # Handle callback
            success = await self.handle_callback(user_id, callback_url)
            if not success:
                return

        # Fetch today's data
        data = await self.fetch_daily_data(user_id)

        if not data:
            print("\n❌ Failed to fetch data. Test aborted.")
            return

        # Save results
        filepath = self.save_results(user_id, data)

        if filepath:
            self.print_header("TEST COMPLETED SUCCESSFULLY")
            print(f"✅ All steps completed!")
            print(f"📄 Results saved to: {filepath}")
            print(f"\n💡 You can now:")
            print(f"   - View the results file: cat {filepath}")
            print(f"   - Check test_output folder for all test results")


async def main():
    """Main entry point"""
    test = WhoopDailyDataTest()
    await test.run_interactive_test()


if __name__ == "__main__":
    print("\n🚀 Starting WHOOP Daily Data Test...\n")

    # Check environment variables
    if not settings.WHOOP_CLIENT_ID or not settings.WHOOP_CLIENT_SECRET:
        print("❌ ERROR: WHOOP credentials not configured!")
        print("Please set WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET in .env file")
        sys.exit(1)

    # Run the test
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
