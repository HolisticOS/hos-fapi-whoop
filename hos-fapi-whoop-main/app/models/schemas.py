"""
WHOOP API Models with UUID Support
Handles UUID identifiers for Sleep and Workout resources
"""

from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
from app.utils.uuid_utils import is_valid_uuid, normalize_whoop_id

# =============================================================================
# WHOOP API v2 Response Models (with UUID identifiers)
# =============================================================================

class WhoopSleepStages(BaseModel):
    """Sleep stages from WHOOP API"""
    light_sleep_milli: Optional[int] = Field(None, description="Light sleep in milliseconds")
    rem_sleep_milli: Optional[int] = Field(None, description="REM sleep in milliseconds")
    slow_wave_sleep_milli: Optional[int] = Field(None, description="Deep/slow wave sleep in milliseconds")
    awake_time_milli: Optional[int] = Field(None, description="Awake time in milliseconds")
    
    # Legacy support for seconds format
    light_sleep_seconds: Optional[int] = None
    rem_sleep_seconds: Optional[int] = None
    deep_sleep_seconds: Optional[int] = None
    awake_seconds: Optional[int] = None
    
    @model_validator(mode='before')
    @classmethod
    def convert_milli_to_seconds(cls, values):
        """Convert milliseconds to seconds for backward compatibility"""
        if isinstance(values, dict):
            # Convert light_sleep_seconds
            if values.get('light_sleep_seconds') is None and values.get('light_sleep_milli') is not None:
                values['light_sleep_seconds'] = values['light_sleep_milli'] // 1000
            
            # Convert rem_sleep_seconds
            if values.get('rem_sleep_seconds') is None and values.get('rem_sleep_milli') is not None:
                values['rem_sleep_seconds'] = values['rem_sleep_milli'] // 1000
            
            # Convert deep_sleep_seconds (from slow_wave_sleep_milli)
            if values.get('deep_sleep_seconds') is None and values.get('slow_wave_sleep_milli') is not None:
                values['deep_sleep_seconds'] = values['slow_wave_sleep_milli'] // 1000
            
            # Convert awake_seconds
            if values.get('awake_seconds') is None and values.get('awake_time_milli') is not None:
                values['awake_seconds'] = values['awake_time_milli'] // 1000
        
        return values

class WhoopSleepScore(BaseModel):
    """Sleep score from WHOOP API"""
    sleep_efficiency: Optional[float] = Field(None, description="Sleep efficiency percentage")
    sleep_consistency: Optional[float] = Field(None, description="Sleep consistency percentage")
    sleep_performance_percentage: Optional[float] = Field(None, description="Overall sleep performance")
    respiratory_rate: Optional[float] = Field(None, description="Average respiratory rate")

class WhoopSleepData(BaseModel):
    """Sleep data from WHOOP API with UUID identifiers"""
    id: str = Field(..., description="UUID identifier for sleep record")
    activity_v1_id: Optional[int] = Field(None, description="Backward compatibility v1 integer ID")
    user_id: int = Field(..., description="User ID")
    
    # Time and duration
    start: str = Field(..., description="Start time in ISO format")
    end: str = Field(..., description="End time in ISO format") 
    timezone_offset: Optional[str] = Field(None, description="Timezone offset")
    
    # Sleep metrics (in milliseconds for v2)
    total_sleep_time_milli: Optional[int] = Field(None, description="Total sleep time in milliseconds")
    time_in_bed_milli: Optional[int] = Field(None, description="Time in bed in milliseconds")
    
    # Sleep stages
    sleep_stages: Optional[WhoopSleepStages] = None
    
    # Sleep quality metrics
    sleep_score: Optional[WhoopSleepScore] = None
    
    # Cycle reference (int in v2 API)
    cycle_id: Optional[int] = Field(None, description="Reference to cycle ID")
    
    # Raw data storage
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Complete API response")
    
    @field_validator('id')
    @classmethod
    def validate_uuid(cls, v):
        """Validate UUID format"""
        if not is_valid_uuid(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v
    
    @field_validator('start', 'end')
    @classmethod
    def validate_datetime_format(cls, v):
        """Validate datetime format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid datetime format: {v}")
    
    @property
    def start_datetime(self) -> datetime:
        """Convert start string to datetime object"""
        return datetime.fromisoformat(self.start.replace('Z', '+00:00'))
    
    @property
    def end_datetime(self) -> datetime:
        """Convert end string to datetime object"""
        return datetime.fromisoformat(self.end.replace('Z', '+00:00'))
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate duration in seconds"""
        if self.total_sleep_time_milli:
            return self.total_sleep_time_milli // 1000
        return None

class WhoopWorkoutZones(BaseModel):
    """Heart rate zones from WHOOP API"""
    zone_zero_milli: Optional[int] = Field(None, description="Zone 0 duration in milliseconds")
    zone_one_milli: Optional[int] = Field(None, description="Zone 1 duration in milliseconds")
    zone_two_milli: Optional[int] = Field(None, description="Zone 2 duration in milliseconds")
    zone_three_milli: Optional[int] = Field(None, description="Zone 3 duration in milliseconds")
    zone_four_milli: Optional[int] = Field(None, description="Zone 4 duration in milliseconds")
    zone_five_milli: Optional[int] = Field(None, description="Zone 5 duration in milliseconds")

class WhoopWorkoutData(BaseModel):
    """Workout data from WHOOP API with UUID identifiers"""
    id: str = Field(..., description="UUID identifier for workout record")
    activity_v1_id: Optional[int] = Field(None, description="Backward compatibility v1 integer ID")
    user_id: int = Field(..., description="User ID")
    
    # Workout identification
    sport_id: int = Field(..., description="Sport/activity type ID")
    sport_name: Optional[str] = Field(None, description="Sport name")
    
    # Time and duration
    start: str = Field(..., description="Start time in ISO format")
    end: str = Field(..., description="End time in ISO format")
    timezone_offset: Optional[str] = Field(None, description="Timezone offset")
    
    # Performance metrics
    strain_score: Optional[float] = Field(None, description="Strain score")
    average_heart_rate: Optional[int] = Field(None, description="Average heart rate")
    max_heart_rate: Optional[int] = Field(None, description="Maximum heart rate")
    calories_burned: Optional[float] = Field(None, description="Calories burned (kilojoules from API)")
    distance_meters: Optional[float] = Field(None, description="Distance in meters")
    altitude_gain_meters: Optional[float] = Field(None, description="Altitude gain in meters")
    
    # Heart rate zones
    heart_rate_zones: Optional[WhoopWorkoutZones] = None
    
    # Raw data storage
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Complete API response")
    
    @field_validator('id')
    @classmethod
    def validate_uuid(cls, v):
        """Validate UUID format"""
        if not is_valid_uuid(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v
    
    @field_validator('start', 'end')
    @classmethod
    def validate_datetime_format(cls, v):
        """Validate datetime format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid datetime format: {v}")
    
    @property
    def start_datetime(self) -> datetime:
        """Convert start string to datetime object"""
        return datetime.fromisoformat(self.start.replace('Z', '+00:00'))
    
    @property
    def end_datetime(self) -> datetime:
        """Convert end string to datetime object"""
        return datetime.fromisoformat(self.end.replace('Z', '+00:00'))
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Calculate duration in seconds"""
        start_dt = self.start_datetime
        end_dt = self.end_datetime
        return int((end_dt - start_dt).total_seconds())

class WhoopRecoveryData(BaseModel):
    """Recovery data from WHOOP API (structure unchanged from v1)"""
    cycle_id: int = Field(..., description="Cycle ID (integer in v2 API)")
    user_id: int = Field(..., description="User ID")
    
    # Recovery metrics
    recovery_score: Optional[float] = Field(None, description="Recovery score percentage")
    hrv_rmssd: Optional[float] = Field(None, description="HRV RMSSD in milliseconds")
    resting_heart_rate: Optional[float] = Field(None, description="Resting heart rate in BPM")
    respiratory_rate: Optional[float] = Field(None, description="Respiratory rate")
    
    # Additional scores
    hrv_score: Optional[float] = Field(None, description="HRV score percentage")
    rhr_score: Optional[float] = Field(None, description="RHR score percentage") 
    respiratory_score: Optional[float] = Field(None, description="Respiratory score percentage")
    
    # Metadata
    recorded_at: str = Field(..., description="When recovery was recorded")
    
    # Raw data storage
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Complete API response")
    
    @property
    def recorded_datetime(self) -> datetime:
        """Convert recorded_at string to datetime object"""
        return datetime.fromisoformat(self.recorded_at.replace('Z', '+00:00'))

# =============================================================================
# Collection Response Models
# =============================================================================

class WhoopSleepCollection(BaseModel):
    """Collection of sleep records from API"""
    records: List[WhoopSleepData] = []
    next_token: Optional[str] = Field(None, description="Pagination token")
    total_count: Optional[int] = Field(None, description="Total available records")

class WhoopWorkoutCollection(BaseModel):
    """Collection of workout records from API"""
    records: List[WhoopWorkoutData] = []
    next_token: Optional[str] = Field(None, description="Pagination token")
    total_count: Optional[int] = Field(None, description="Total available records")

class WhoopRecoveryCollection(BaseModel):
    """Collection of recovery records from API"""
    records: List[WhoopRecoveryData] = []
    next_token: Optional[str] = Field(None, description="Pagination token")
    total_count: Optional[int] = Field(None, description="Total available records")

# =============================================================================
# Database Storage Models
# =============================================================================

class WhoopSleepRecord(BaseModel):
    """Database model for v2 sleep data with UUID support"""
    id: Optional[str] = Field(None, description="Database record ID")
    user_id: str = Field(..., description="Internal user ID")
    
    # v2 identifiers
    sleep_uuid: str = Field(..., description="UUID identifier")
    sleep_v1_id: Optional[int] = Field(None, description="v1 integer ID for compatibility")
    cycle_id: Optional[str] = Field(None, description="Associated cycle ID")
    
    # Sleep timing
    start_time: datetime = Field(..., description="Sleep start time")
    end_time: datetime = Field(..., description="Sleep end time")
    timezone_offset: Optional[str] = Field(None, description="Timezone offset")
    
    # Sleep metrics (stored in milliseconds)
    total_sleep_time_milli: Optional[int] = None
    time_in_bed_milli: Optional[int] = None
    awake_time_milli: Optional[int] = None
    light_sleep_milli: Optional[int] = None
    slow_wave_sleep_milli: Optional[int] = None
    rem_sleep_milli: Optional[int] = None
    
    # Sleep quality scores
    sleep_efficiency: Optional[float] = None
    sleep_consistency: Optional[float] = None
    sleep_performance_percentage: Optional[float] = None
    respiratory_rate: Optional[float] = None
    
    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('sleep_uuid')
    @classmethod
    def validate_sleep_uuid(cls, v):
        """Validate sleep UUID format"""
        if not is_valid_uuid(v):
            raise ValueError(f"Invalid sleep UUID: {v}")
        return v

class WhoopWorkoutRecord(BaseModel):
    """Database model for v2 workout data with UUID support"""
    id: Optional[str] = Field(None, description="Database record ID")
    user_id: str = Field(..., description="Internal user ID")
    
    # v2 identifiers
    workout_uuid: str = Field(..., description="UUID identifier")
    workout_v1_id: Optional[int] = Field(None, description="v1 integer ID for compatibility")
    
    # Workout identification
    sport_id: int = Field(..., description="Sport type ID")
    sport_name: Optional[str] = None
    
    # Workout timing
    start_time: datetime = Field(..., description="Workout start time")
    end_time: datetime = Field(..., description="Workout end time")
    timezone_offset: Optional[str] = Field(None, description="Timezone offset")
    
    # Performance metrics
    strain_score: Optional[float] = None
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    calories_burned: Optional[int] = None
    distance_meters: Optional[float] = None
    
    # Heart rate zones (in milliseconds)
    zone_zero_milli: Optional[int] = None
    zone_one_milli: Optional[int] = None
    zone_two_milli: Optional[int] = None
    zone_three_milli: Optional[int] = None
    zone_four_milli: Optional[int] = None
    zone_five_milli: Optional[int] = None
    
    # Metadata
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('workout_uuid')
    @classmethod
    def validate_workout_uuid(cls, v):
        """Validate workout UUID format"""
        if not is_valid_uuid(v):
            raise ValueError(f"Invalid workout UUID: {v}")
        return v

class WhoopRecoveryRecord(BaseModel):
    """Database model for v2 recovery data (structure mostly unchanged)"""
    id: Optional[str] = Field(None, description="Database record ID")
    user_id: str = Field(..., description="Internal user ID")
    
    # Identifiers (cycle ID remains consistent)
    cycle_id: str = Field(..., description="Cycle ID")
    
    # Recovery metrics
    recovery_score: Optional[float] = None
    hrv_rmssd: Optional[float] = None
    resting_heart_rate: Optional[float] = None
    respiratory_rate: Optional[float] = None
    
    # Additional scores
    hrv_score: Optional[float] = None
    rhr_score: Optional[float] = None
    respiratory_score: Optional[float] = None
    
    # Metadata
    recorded_at: datetime = Field(..., description="When recovery was recorded")
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# =============================================================================
# Migration Models
# =============================================================================

class WhoopMigrationMapping(BaseModel):
    """Model for tracking v1 to v2 ID migrations"""
    id: Optional[str] = None
    resource_type: str = Field(..., description="sleep, workout, etc.")
    v1_id: int = Field(..., description="Original v1 integer ID")
    v2_uuid: str = Field(..., description="New UUID identifier")
    user_id: str = Field(..., description="Associated user")
    migration_status: str = Field(default="completed", description="Migration status")
    created_at: Optional[datetime] = None
    
    @field_validator('v2_uuid')
    @classmethod
    def validate_v2_uuid(cls, v):
        """Validate v2 UUID format"""
        if not is_valid_uuid(v):
            raise ValueError(f"Invalid v2 UUID: {v}")
        return v

# =============================================================================
# Cycle Models (defined before WhoopDataResponse to avoid forward reference)
# =============================================================================

class WhoopCycleData(BaseModel):
    """WHOOP Cycle Data"""
    id: str = Field(..., description="Cycle ID")
    user_id: int = Field(..., description="WHOOP user ID")
    created_at: datetime = Field(..., description="Cycle creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    start: datetime = Field(..., description="Cycle start time")
    end: Optional[datetime] = Field(None, description="Cycle end time")
    timezone_offset: str = Field(..., description="Timezone offset")
    score_state: str = Field(..., description="Score state")
    score: Optional[Dict[str, Any]] = Field(None, description="Cycle score data")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw API response")

class WhoopCycleCollection(BaseModel):
    """Collection of WHOOP cycles"""
    data: List[WhoopCycleData] = Field(default_factory=list)
    next_token: Optional[str] = None

# =============================================================================
# Unified Response Model
# =============================================================================

class WhoopDataResponse(BaseModel):
    """Unified response model for v2 data with pagination"""
    sleep_data: List[WhoopSleepData] = []
    workout_data: List[WhoopWorkoutData] = []
    recovery_data: List[WhoopRecoveryData] = []
    cycle_data: List[WhoopCycleData] = []
    next_token: Optional[str] = None
    total_records: int = 0
    api_version: str = "v2"

# =============================================================================
# Webhook Models
# =============================================================================

class WhoopProfileData(BaseModel):
    """WHOOP Profile Data"""
    user_id: int = Field(..., description="WHOOP user ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw API response")

class WhoopBodyMeasurementData(BaseModel):
    """WHOOP Body Measurement Data"""
    user_id: int = Field(..., description="WHOOP user ID")
    height_meter: Optional[float] = Field(None, description="Height in meters")
    weight_kilogram: Optional[float] = Field(None, description="Weight in kilograms")
    max_heart_rate: Optional[int] = Field(None, description="Maximum heart rate")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw API response")

# =============================================================================

class WhoopWebhookEvent(BaseModel):
    """WHOOP webhook event payload for with UUID identifiers"""
    user_id: int = Field(..., description="WHOOP user ID")
    id: str = Field(..., description="Resource UUID (for sleep/workout) or cycle ID (for recovery)")
    type: str = Field(..., description="Event type: recovery.updated, sleep.updated, workout.updated")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")
    
    @model_validator(mode='after')
    @classmethod
    def validate_resource_id(cls, model):
        """Validate resource ID format based on event type"""
        event_type = model.type
        resource_id = model.id
        
        if event_type in ['sleep.updated', 'workout.created', 'workout.updated']:
            # Sleep and workout events should have UUID identifiers
            if not is_valid_uuid(resource_id):
                raise ValueError(f"Expected UUID for {event_type}, got: {resource_id}")
        # Recovery events use cycle IDs which can be various formats
        
        return model

# Export all models
__all__ = [
    # API Response Models
    "WhoopSleepData",
    "WhoopWorkoutData", 
    "WhoopRecoveryData",
    "WhoopCycleData",
    "WhoopProfileData",
    "WhoopBodyMeasurementData",
    "WhoopSleepStages",
    "WhoopSleepScore",
    "WhoopWorkoutZones",
    
    # Collection Models
    "WhoopSleepCollection",
    "WhoopWorkoutCollection",
    "WhoopRecoveryCollection",
    "WhoopCycleCollection",
    
    # Database Storage Models
    "WhoopSleepRecord",
    "WhoopWorkoutRecord",
    "WhoopRecoveryRecord",
    
    # Migration Models
    "WhoopMigrationMapping",
    "WhoopDataResponse",
    
    # Webhook Models
    "WhoopWebhookEvent"
]