"""
Caching utilities for WHOOP API responses
Follows the pattern from hos-fapi-hm-sahha-main
"""
from cachetools import TTLCache
from typing import Any, Optional
import hashlib
import json
from app.config.settings import settings

# Global cache instances with TTL from settings
overview_cache = TTLCache(maxsize=1000, ttl=settings.CACHE_TTL_OVERVIEW)
metrics_cache = TTLCache(maxsize=5000, ttl=settings.CACHE_TTL_METRICS)

def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a consistent cache key from arguments
    """
    # Convert all arguments to strings and create a combined key
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        key_parts.append(str(arg))
    
    # Add keyword arguments in sorted order for consistency
    for key in sorted(kwargs.keys()):
        key_parts.append(f"{key}={kwargs[key]}")
    
    # Create hash of the combined key to ensure consistent length
    combined_key = "|".join(key_parts)
    return hashlib.md5(combined_key.encode()).hexdigest()

def get_cached_overview(cache_key: str) -> Optional[Any]:
    """
    Get cached overview data
    """
    return overview_cache.get(cache_key)

def set_cached_overview(cache_key: str, data: Any) -> None:
    """
    Store overview data in cache
    """
    overview_cache[cache_key] = data

def get_cached_metrics(cache_key: str) -> Optional[Any]:
    """
    Get cached metrics data
    """
    return metrics_cache.get(cache_key)

def set_cached_metrics(cache_key: str, data: Any) -> None:
    """
    Store metrics data in cache
    """
    metrics_cache[cache_key] = data

def clear_user_cache(user_id: str) -> None:
    """
    Clear all cached data for a specific user
    """
    # Remove all entries that contain the user_id in the key
    keys_to_remove = []
    
    for key in overview_cache.keys():
        if user_id in str(key):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        overview_cache.pop(key, None)
    
    keys_to_remove = []
    for key in metrics_cache.keys():
        if user_id in str(key):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        metrics_cache.pop(key, None)

def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring
    """
    return {
        "overview_cache": {
            "size": len(overview_cache),
            "maxsize": overview_cache.maxsize,
            "ttl": overview_cache.ttl
        },
        "metrics_cache": {
            "size": len(metrics_cache),
            "maxsize": metrics_cache.maxsize,
            "ttl": metrics_cache.ttl
        }
    }