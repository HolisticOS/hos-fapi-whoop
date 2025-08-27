"""
Date utility functions for WHOOP API integration
Following the pattern from hos-fapi-hm-sahha-main
"""
from datetime import datetime, date, timedelta, timezone
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

def get_current_date() -> date:
    """Get current date in local timezone"""
    return datetime.now().date()

def get_current_datetime() -> datetime:
    """Get current datetime with UTC timezone"""
    return datetime.now(timezone.utc)

def parse_whoop_datetime(date_string: str) -> Optional[datetime]:
    """
    Parse WHOOP API datetime string to datetime object
    WHOOP uses ISO 8601 format: 2024-01-15T23:30:00.000Z
    """
    try:
        if not date_string:
            return None
            
        # Handle different WHOOP datetime formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # With microseconds
            "%Y-%m-%dT%H:%M:%SZ",     # Without microseconds
            "%Y-%m-%dT%H:%M:%S",      # Without Z
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_string, fmt)
                # Ensure timezone is UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
                
        logger.warning("Failed to parse WHOOP datetime", date_string=date_string)
        return None
        
    except Exception as e:
        logger.error("Error parsing WHOOP datetime", date_string=date_string, error=str(e))
        return None

def datetime_to_date(dt: datetime) -> date:
    """Convert datetime to date"""
    return dt.date() if dt else None

def get_date_range(start_date: Optional[date] = None, end_date: Optional[date] = None, days: int = 7) -> tuple[date, date]:
    """
    Get a date range, defaulting to last N days if not provided
    """
    end_date = end_date or get_current_date()
    start_date = start_date or (end_date - timedelta(days=days - 1))
    
    return start_date, end_date

def format_date_for_whoop_api(target_date: date) -> str:
    """
    Format date for WHOOP API requests
    WHOOP expects ISO format dates
    """
    return target_date.isoformat()

def format_datetime_for_whoop_api(dt: datetime) -> str:
    """
    Format datetime for WHOOP API requests
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def get_sync_date_range(user_id: str, data_type: str, max_days: int = 30) -> tuple[date, date]:
    """
    Calculate the date range for sync operations
    This should be enhanced to check last successful sync from database
    """
    end_date = get_current_date()
    start_date = end_date - timedelta(days=max_days)
    
    # TODO: Query database to get last successful sync date
    # and adjust start_date accordingly
    
    return start_date, end_date

def is_valid_date_range(start_date: date, end_date: date, max_range_days: int = 90) -> bool:
    """
    Validate that date range is reasonable for API calls
    """
    if start_date > end_date:
        return False
    
    if (end_date - start_date).days > max_range_days:
        return False
    
    # Don't allow future dates
    if end_date > get_current_date():
        return False
    
    return True

def split_date_range(start_date: date, end_date: date, chunk_days: int = 7) -> list[tuple[date, date]]:
    """
    Split large date ranges into smaller chunks for API efficiency
    """
    chunks = []
    current_start = start_date
    
    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=chunk_days - 1), end_date)
        chunks.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)
    
    return chunks

def get_sleep_date(sleep_end_time: datetime) -> date:
    """
    Get the date to associate with a sleep session
    Sleep sessions that end after 3 AM are associated with the previous day
    """
    # If sleep ends before 3 AM, it belongs to the previous day
    if sleep_end_time.hour < 3:
        return (sleep_end_time - timedelta(days=1)).date()
    else:
        return sleep_end_time.date()

def seconds_to_minutes(seconds: Optional[int]) -> Optional[int]:
    """Convert seconds to minutes, handling None values"""
    return round(seconds / 60) if seconds is not None else None

def minutes_to_seconds(minutes: Optional[int]) -> Optional[int]:
    """Convert minutes to seconds, handling None values"""
    return minutes * 60 if minutes is not None else None