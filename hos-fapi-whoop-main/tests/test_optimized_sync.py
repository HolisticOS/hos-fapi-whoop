"""
Optimized sync strategy to maximize user capacity in free tier.

This script implements time-aware endpoint selection:
- Morning: Recovery + Sleep (2 calls)
- Midday: Workout + Cycle (2 calls)
- Evening: Workout + Cycle (2 calls)

Total: 6 calls per user per day (vs 12 with naive approach)
Capacity: ~1,666 users (vs ~800)
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.whoop_service import WhoopAPIService
from app.services.auth_service import WhoopAuthService
import structlog

logger = structlog.get_logger(__name__)


class OptimizedSyncStrategy:
    """Smart sync strategy that calls only relevant endpoints based on time of day"""

    def __init__(self):
        self.auth_service = WhoopAuthService()
        self.whoop_service = WhoopAPIService()

    def get_sync_window(self) -> str:
        """
        Determine current sync window based on time of day (UTC).

        Returns:
            'morning' (6-11 UTC), 'midday' (11-18 UTC), or 'evening' (18-6 UTC)
        """
        current_hour = datetime.now(timezone.utc).hour

        if 6 <= current_hour < 11:
            return 'morning'
        elif 11 <= current_hour < 18:
            return 'midday'
        else:
            return 'evening'

    async def sync_user_data(
        self,
        user_id: str,
        sync_window: str = None,
        force_all: bool = False
    ) -> Dict[str, Any]:
        """
        Sync user data with time-aware endpoint selection.

        Args:
            user_id: User identifier
            sync_window: Override sync window ('morning', 'midday', 'evening')
            force_all: Force all endpoints regardless of time (testing only)

        Returns:
            Dict with sync results and API call count
        """
        if sync_window is None:
            sync_window = self.get_sync_window()

        print(f"\n{'='*60}")
        print(f"🔄 OPTIMIZED SYNC - {sync_window.upper()} WINDOW")
        print(f"{'='*60}")
        print(f"User: {user_id}")
        print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Check authentication
        user_info = await self.auth_service.get_user_info(user_id)
        if not user_info or not user_info.get('is_authenticated'):
            print("❌ User not authenticated")
            return {'error': 'not_authenticated', 'api_calls': 0}

        # Date range for last 7 days (to ensure we get recent data)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        results = {}
        api_call_count = 0

        # Time-aware endpoint selection
        if force_all or sync_window == 'morning':
            # Morning: Recovery (new daily score) + Sleep (previous night)
            print("\n📊 Fetching morning endpoints...")
            print("   - Recovery data (today's readiness)")
            print("   - Sleep data (last night)")

            try:
                recovery = await self.whoop_service.get_recovery_data(
                    user_id=user_id,
                    start_date=start_iso,
                    end_date=end_iso,
                    limit=3
                )
                results['recovery'] = {
                    'count': len(recovery.records),
                    'latest': recovery.records[0] if recovery.records else None
                }
                api_call_count += 1
                print(f"   ✅ Recovery: {len(recovery.records)} records")
            except Exception as e:
                results['recovery'] = {'error': str(e)}
                print(f"   ❌ Recovery: {e}")

            try:
                sleep = await self.whoop_service.get_sleep_data(
                    user_id=user_id,
                    limit=3
                )
                results['sleep'] = {
                    'count': len(sleep.records),
                    'latest': sleep.records[0] if sleep.records else None
                }
                api_call_count += 1
                print(f"   ✅ Sleep: {len(sleep.records)} records")
            except Exception as e:
                results['sleep'] = {'error': str(e)}
                print(f"   ❌ Sleep: {e}")

        if force_all or sync_window in ['midday', 'evening']:
            # Midday/Evening: Workout + Cycle (activity tracking)
            print("\n💪 Fetching activity endpoints...")
            print("   - Workout data (recent exercises)")
            print("   - Cycle data (daily strain)")

            try:
                workout = await self.whoop_service.get_workout_data(
                    user_id=user_id,
                    limit=3
                )
                results['workout'] = {
                    'count': len(workout.records),
                    'latest': workout.records[0] if workout.records else None
                }
                api_call_count += 1
                print(f"   ✅ Workout: {len(workout.records)} records")
            except Exception as e:
                results['workout'] = {'error': str(e)}
                print(f"   ❌ Workout: {e}")

            try:
                cycle = await self.whoop_service.get_cycle_data(
                    user_id=user_id,
                    start_date=start_iso,
                    end_date=end_iso,
                    limit=3
                )
                results['cycle'] = {
                    'count': len(cycle.records),
                    'latest': cycle.records[0] if cycle.records else None
                }
                api_call_count += 1
                print(f"   ✅ Cycle: {len(cycle.records)} records")
            except Exception as e:
                results['cycle'] = {'error': str(e)}
                print(f"   ❌ Cycle: {e}")

        results['api_calls'] = api_call_count
        results['sync_window'] = sync_window

        print(f"\n{'='*60}")
        print(f"✅ Sync Complete - {api_call_count} API calls used")
        print(f"{'='*60}")

        return results

    async def simulate_daily_syncs(self, user_id: str):
        """
        Simulate all 3 daily syncs for capacity planning.

        This helps visualize API usage patterns.
        """
        print(f"\n{'#'*60}")
        print("📅 SIMULATING FULL DAY OF SYNCS")
        print(f"{'#'*60}")

        total_calls = 0

        # Morning sync
        morning = await self.sync_user_data(user_id, sync_window='morning')
        total_calls += morning.get('api_calls', 0)

        await asyncio.sleep(1)  # Small delay between syncs

        # Midday sync
        midday = await self.sync_user_data(user_id, sync_window='midday')
        total_calls += midday.get('api_calls', 0)

        await asyncio.sleep(1)

        # Evening sync
        evening = await self.sync_user_data(user_id, sync_window='evening')
        total_calls += evening.get('api_calls', 0)

        print(f"\n{'#'*60}")
        print(f"📊 DAILY SUMMARY")
        print(f"{'#'*60}")
        print(f"Total API calls per user per day: {total_calls}")
        print(f"WHOOP daily limit: 10,000 requests")
        print(f"Maximum users with this strategy: {10_000 // total_calls:,} users")
        print(f"{'#'*60}")


async def main():
    """Interactive test for optimized sync strategy"""
    sync_strategy = OptimizedSyncStrategy()

    print("\n" + "="*60)
    print("WHOOP OPTIMIZED SYNC STRATEGY TESTER")
    print("="*60)
    print("\nThis script demonstrates time-aware endpoint selection")
    print("to maximize user capacity in WHOOP's free tier.")
    print("\nOptions:")
    print("1. Test current sync window (auto-detect time)")
    print("2. Simulate full day (all 3 sync windows)")
    print("3. Test specific window (morning/midday/evening)")
    print("="*60)

    choice = input("\nEnter choice (1-3): ").strip()
    user_id = input("Enter user ID: ").strip()

    if choice == '1':
        # Current window
        results = await sync_strategy.sync_user_data(user_id)

        # Save results
        output_file = Path(__file__).parent.parent / f"sync_results_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")

    elif choice == '2':
        # Simulate full day
        await sync_strategy.simulate_daily_syncs(user_id)

    elif choice == '3':
        # Specific window
        print("\nSync Windows:")
        print("- morning: Recovery + Sleep (2 calls)")
        print("- midday: Workout + Cycle (2 calls)")
        print("- evening: Workout + Cycle (2 calls)")
        window = input("\nEnter window (morning/midday/evening): ").strip().lower()

        if window in ['morning', 'midday', 'evening']:
            results = await sync_strategy.sync_user_data(user_id, sync_window=window)

            # Save results
            output_file = Path(__file__).parent.parent / f"sync_results_{user_id}_{window}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {output_file}")
        else:
            print("❌ Invalid window. Use: morning, midday, or evening")


if __name__ == "__main__":
    asyncio.run(main())
