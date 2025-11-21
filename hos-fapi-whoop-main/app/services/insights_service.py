"""
WHOOP Health Insights Service using Gemini 2.5 Flash
Generates AI-powered insights from 7 days of raw WHOOP health data
"""

import json
from datetime import datetime, timedelta, date, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID
import structlog
from cachetools import TTLCache
from google import genai

from app.config.settings import settings
from app.models.database import WhoopDataService

logger = structlog.get_logger(__name__)


class WhoopInsightsService:
    """
    Service for generating AI-powered health insights using Gemini 2.5 Flash

    Features:
    - Analyzes 7 days of raw WHOOP data (recovery, sleep, cycle, workout)
    - Uses Gemini 2.5 Flash for fast, cost-efficient insights generation
    - Caches insights for 1 hour to reduce API costs
    - Provides actionable health recommendations
    """

    def __init__(self):
        self.data_service = WhoopDataService()

        # Initialize Gemini client
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not configured - insights service will not work")
            self.client = None
        else:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Gemini client initialized", model=settings.GEMINI_MODEL)

        # Cache for insights (TTL: 1 hour)
        self.cache = TTLCache(maxsize=100, ttl=settings.CACHE_TTL_INSIGHTS)

    async def generate_insights(
        self,
        user_id: UUID,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Generate AI-powered insights from user's WHOOP data

        Args:
            user_id: Authenticated user's UUID
            days_back: Number of days of historical data to analyze (default: 7)

        Returns:
            Dictionary containing insights, trends, and recommendations
        """
        try:
            cache_key = f"{user_id}_{days_back}"

            # Check cache first
            if cache_key in self.cache:
                logger.info("📦 Returning cached insights", user_id=str(user_id))
                return self.cache[cache_key]

            if not self.client:
                raise ValueError("Gemini API key not configured")

            # Calculate date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days_back)

            logger.info(
                "🔍 Fetching WHOOP data for insights",
                user_id=str(user_id),
                date_range=f"{start_date} to {end_date}",
                days=days_back
            )

            # Fetch raw WHOOP data from database
            whoop_data = await self.data_service.get_comprehensive_health_data(
                user_id,
                start_date,
                end_date
            )

            # Validate we have data
            if not self._has_sufficient_data(whoop_data):
                return {
                    "user_id": str(user_id),
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                        "days": days_back
                    },
                    "insights": [],
                    "summary": "Insufficient data available. Please ensure your WHOOP device is syncing data.",
                    "recommendations": [],
                    "trends": {
                        "recovery": "unknown",
                        "sleep": "unknown",
                        "strain": "unknown",
                        "overall": "Insufficient data for trend analysis"
                    },
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "data_quality": "insufficient",
                    "model": settings.GEMINI_MODEL
                }

            # Prepare data for Gemini
            formatted_data = self._format_data_for_analysis(whoop_data, start_date, end_date)

            # Generate insights using Gemini
            logger.info("🤖 Generating insights with Gemini 2.5 Flash", user_id=str(user_id))
            insights_response = await self._generate_gemini_insights(formatted_data)

            # Structure the response
            result = {
                "user_id": str(user_id),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": days_back
                },
                "insights": insights_response.get("insights", []),
                "summary": insights_response.get("summary", ""),
                "recommendations": insights_response.get("recommendations", []),
                "trends": insights_response.get("trends", {}),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_quality": self._assess_data_quality(whoop_data),
                "model": settings.GEMINI_MODEL
            }

            # Cache the result
            self.cache[cache_key] = result

            logger.info(
                "✅ Insights generated successfully",
                user_id=str(user_id),
                insights_count=len(result["insights"]),
                recommendations_count=len(result["recommendations"])
            )

            return result

        except Exception as e:
            logger.error("Failed to generate insights", user_id=str(user_id), error=str(e))
            raise

    def _has_sufficient_data(self, whoop_data: Dict[str, Any]) -> bool:
        """Check if we have enough data for meaningful insights"""
        recovery_count = len(whoop_data.get("recovery", []))
        sleep_count = len(whoop_data.get("sleep", []))
        strain_count = len(whoop_data.get("cycles") or whoop_data.get("workouts", []))

        # Need at least 3 days of any data type
        return (recovery_count >= 3) or (sleep_count >= 3) or (strain_count >= 3)

    def _assess_data_quality(self, whoop_data: Dict[str, Any]) -> str:
        """Assess the quality/completeness of available data"""
        recovery_count = len(whoop_data.get("recovery", []))
        sleep_count = len(whoop_data.get("sleep", []))
        cycle_count = len(whoop_data.get("cycles", []))
        workout_count = len(whoop_data.get("workouts", []))

        total_records = recovery_count + sleep_count + cycle_count + workout_count

        if total_records >= 20:
            return "excellent"
        elif total_records >= 15:
            return "good"
        elif total_records >= 10:
            return "fair"
        else:
            return "limited"

    def _format_data_for_analysis(
        self,
        whoop_data: Dict[str, Any],
        start_date: date,
        end_date: date
    ) -> str:
        """
        Format raw WHOOP data into a structured summary for Gemini analysis

        Focuses on key metrics without overwhelming the model with unnecessary detail
        """
        summary_lines = [
            f"# WHOOP Health Data Analysis ({start_date} to {end_date})",
            "",
            "## Data Overview",
        ]

        # Recovery data summary
        recovery_data = whoop_data.get("recovery", [])
        if recovery_data:
            summary_lines.append("\n### Recovery Metrics")
            for record in recovery_data:
                score = record.get("score", {})
                created_at = record.get("created_at", "Unknown")
                summary_lines.append(
                    f"- {created_at[:10]}: Recovery Score {score.get('recovery_score', 'N/A')}%, "
                    f"HRV {score.get('hrv_rmssd_milli', 'N/A')}ms, "
                    f"RHR {score.get('resting_heart_rate', 'N/A')}bpm"
                )

        # Sleep data summary
        sleep_data = whoop_data.get("sleep", [])
        if sleep_data:
            summary_lines.append("\n### Sleep Metrics")
            for record in sleep_data:
                score = record.get("score", {})
                start = record.get("start", "Unknown")
                total_sleep_hrs = score.get("total_sleep_time_milli", 0) / 3600000  # Convert ms to hours
                summary_lines.append(
                    f"- {start[:10]}: {total_sleep_hrs:.1f}h sleep, "
                    f"Performance {score.get('sleep_performance_percentage', 'N/A')}%, "
                    f"Efficiency {score.get('sleep_efficiency_percentage', 'N/A')}%"
                )

        # Cycle/Strain data summary
        cycle_data = whoop_data.get("cycles", [])
        if cycle_data:
            summary_lines.append("\n### Daily Strain & Activity")
            for record in cycle_data:
                score = record.get("score", {})
                start = record.get("start", "Unknown")
                summary_lines.append(
                    f"- {start[:10]}: Strain {score.get('strain', 'N/A')}, "
                    f"Calories {score.get('kilojoule', 0) * 0.239:.0f}kcal, "
                    f"Avg HR {score.get('average_heart_rate', 'N/A')}bpm"
                )

        # Workout data summary
        workout_data = whoop_data.get("workouts", [])
        if workout_data:
            summary_lines.append(f"\n### Workouts ({len(workout_data)} total)")
            for record in workout_data[:5]:  # Show first 5 workouts
                score = record.get("score", {})
                start = record.get("start", "Unknown")
                sport = record.get("sport_id", "Unknown Activity")
                summary_lines.append(
                    f"- {start[:10]}: {sport}, Strain {score.get('strain', 'N/A')}, "
                    f"Avg HR {score.get('average_heart_rate', 'N/A')}bpm"
                )

        return "\n".join(summary_lines)

    async def _generate_gemini_insights(self, formatted_data: str) -> Dict[str, Any]:
        """
        Call Gemini 2.5 Flash API to generate insights from formatted data

        Uses structured prompting to ensure consistent, actionable output
        """
        system_prompt = """You are an expert health and wellness coach analyzing WHOOP health data.

Your task is to provide:
1. Key insights about patterns in recovery, sleep, and strain
2. A brief summary of overall health trends
3. Actionable recommendations for improvement
4. Identified trends (improving, declining, stable)

Focus on:
- Recovery patterns and their relationship to sleep/strain
- Sleep quality and consistency
- Strain management and recovery balance
- Heart rate variability (HRV) trends
- Practical, specific recommendations

Respond ONLY with valid JSON in this exact format:
{
  "insights": [
    "Insight 1: specific observation about the data",
    "Insight 2: another specific observation",
    "Insight 3: pattern or correlation identified"
  ],
  "summary": "Brief 2-3 sentence overview of health status and key trends",
  "recommendations": [
    "Recommendation 1: specific, actionable advice",
    "Recommendation 2: another actionable suggestion",
    "Recommendation 3: lifestyle or training adjustment"
  ],
  "trends": {
    "recovery": "improving|declining|stable",
    "sleep": "improving|declining|stable",
    "strain": "improving|declining|stable",
    "overall": "Brief description of overall trend"
  }
}"""

        user_prompt = f"{formatted_data}\n\nAnalyze this WHOOP health data and provide insights, summary, recommendations, and trends in JSON format."

        try:
            # Call Gemini API
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=user_prompt,
                config={
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "max_output_tokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
                    "response_mime_type": "application/json",
                    "system_instruction": system_prompt
                }
            )

            # Parse JSON response
            insights_json = json.loads(response.text)

            return insights_json

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Gemini JSON response", error=str(e), response=response.text)
            # Return fallback structure
            return {
                "insights": ["Data analysis in progress. Please try again."],
                "summary": "Unable to generate insights at this time.",
                "recommendations": ["Ensure your WHOOP device is syncing regularly."],
                "trends": {
                    "recovery": "unknown",
                    "sleep": "unknown",
                    "strain": "unknown",
                    "overall": "Insufficient data for trend analysis"
                }
            }
        except Exception as e:
            logger.error("Gemini API call failed", error=str(e))
            raise

    def clear_cache(self, user_id: Optional[UUID] = None):
        """Clear insights cache for a specific user or all users"""
        if user_id:
            # Clear all cache entries for this user
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(str(user_id))]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info("🧹 Cleared insights cache for user", user_id=str(user_id))
        else:
            self.cache.clear()
            logger.info("🧹 Cleared all insights cache")
