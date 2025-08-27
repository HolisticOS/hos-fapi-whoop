from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

# =============================================================================
# WHOOP API Response Models (based on real API docs)
# =============================================================================

class WhoopUserProfile(BaseModel):
    """User profile from WHOOP API"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class WhoopRecoveryData(BaseModel):
    """Recovery data from WHOOP API"""
    cycle_id: str
    recovery_score: Optional[float] = None
    hrv: Optional[dict] = None
    resting_heart_rate: Optional[int] = None
    skin_temp_celsius: Optional[float] = None
    respiratory_rate: Optional[float] = None

class WhoopSleepStages(BaseModel):
    """Sleep stages from WHOOP API"""
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    awake_seconds: Optional[int] = None

class WhoopSleepScore(BaseModel):
    """Sleep score from WHOOP API"""
    stage_summary: Optional[float] = None
    sleep_needed_seconds: Optional[int] = None
    respiratory_rate: Optional[float] = None
    sleep_consistency: Optional[float] = None

class WhoopSleepData(BaseModel):
    """Sleep data from WHOOP API"""
    id: str
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    efficiency_percentage: Optional[float] = None
    stages: Optional[WhoopSleepStages] = None
    score: Optional[WhoopSleepScore] = None

class WhoopWorkoutData(BaseModel):
    """Workout data from WHOOP API"""
    id: str
    sport_id: Optional[int] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    strain: Optional[float] = None
    distance_meters: Optional[int] = None
    altitude_gain_meters: Optional[int] = None
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    kilojoules: Optional[int] = None

# =============================================================================
# Database Models (for internal storage)
# =============================================================================

class WhoopUser(BaseModel):
    """Database model for WHOOP user connections"""
    id: Optional[str] = None
    user_id: str = Field(..., description="Internal user ID")
    whoop_user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WhoopRecoveryRecord(BaseModel):
    """Database model for recovery data"""
    id: Optional[str] = None
    user_id: str
    cycle_id: Optional[str] = None
    recovery_score: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    resting_heart_rate: Optional[int] = None
    skin_temp_celsius: Optional[float] = None
    respiratory_rate: Optional[float] = None
    date: date
    recorded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class WhoopSleepRecord(BaseModel):
    """Database model for sleep data"""
    id: Optional[str] = None
    user_id: str
    sleep_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    efficiency_percentage: Optional[float] = None
    sleep_score: Optional[float] = None
    light_sleep_minutes: Optional[int] = None
    rem_sleep_minutes: Optional[int] = None
    deep_sleep_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None
    date: date
    created_at: Optional[datetime] = None

class WhoopWorkoutRecord(BaseModel):
    """Database model for workout data"""
    id: Optional[str] = None
    user_id: str
    workout_id: Optional[str] = None
    sport_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    strain: Optional[float] = None
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories: Optional[int] = None
    kilojoules: Optional[int] = None
    date: date
    created_at: Optional[datetime] = None

class WhoopSyncLog(BaseModel):
    """Database model for sync tracking"""
    id: Optional[str] = None
    user_id: str
    data_type: str = Field(..., description="recovery, sleep, or workout")
    sync_date: date
    last_sync_at: Optional[datetime] = None
    records_synced: int = 0
    status: str = "success"  # success, partial, failed

# =============================================================================
# API Request/Response Models
# =============================================================================

class OAuthAuthorizationRequest(BaseModel):
    """OAuth authorization request"""
    user_id: str
    redirect_uri: str
    scopes: List[str] = ["read:profile", "read:recovery", "read:sleep", "read:workouts", "offline"]

class OAuthAuthorizationResponse(BaseModel):
    """OAuth authorization response"""
    authorization_url: str
    state: str

class OAuthCallbackRequest(BaseModel):
    """OAuth callback request"""
    code: str
    state: str
    user_id: str

class OAuthTokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int
    scope: Optional[str] = None

class HealthMetricsRequest(BaseModel):
    """Request for health metrics"""
    user_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    metric_types: Optional[List[str]] = ["recovery", "sleep", "workout"]

class HealthMetricsResponse(BaseModel):
    """Response with health metrics"""
    user_id: str
    start_date: date
    end_date: date
    recovery_data: List[WhoopRecoveryRecord] = []
    sleep_data: List[WhoopSleepRecord] = []
    workout_data: List[WhoopWorkoutRecord] = []
    last_sync: Optional[datetime] = None

class WebhookEventPayload(BaseModel):
    """WHOOP webhook event payload"""
    user_id: int
    id: int
    type: str  # recovery.updated, sleep.updated, workout.updated
    trace_id: Optional[str] = None

# =============================================================================
# Error Response Models
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[dict] = None

class APIError(BaseModel):
    """API error details"""
    code: str
    message: str
    details: Optional[str] = None