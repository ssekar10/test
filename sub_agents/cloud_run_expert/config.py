"""Performance optimization configuration."""

import os
from functools import lru_cache
from datetime import datetime, timedelta

# Performance tuning
ENABLE_CACHING = True
CACHE_TTL_SECONDS = 300  # 5 minutes for service configs
PARALLEL_REGION_QUERIES = True
MAX_PARALLEL_CALLS = 3

# Smart defaults
DEFAULT_REGION = "us-east1"
COMMON_REGIONS = ["us-east1", "us-central1"]

# Cache storage
_service_config_cache = {}
_cache_timestamps = {}


def get_cached_config(service_name: str, region: str):
    """Get cached service configuration if available and fresh."""
    if not ENABLE_CACHING:
        return None
    
    cache_key = f"{service_name}|{region}"
    
    if cache_key not in _service_config_cache:
        return None
    
    # Check if cache is still fresh
    cache_time = _cache_timestamps.get(cache_key)
    if cache_time and (datetime.now() - cache_time).seconds < CACHE_TTL_SECONDS:
        return _service_config_cache[cache_key]
    
    # Cache expired
    return None


def set_cached_config(service_name: str, region: str, config: str):
    """Cache service configuration."""
    if not ENABLE_CACHING:
        return
    
    cache_key = f"{service_name}|{region}"
    _service_config_cache[cache_key] = config
    _cache_timestamps[cache_key] = datetime.now()


def clear_cache():
    """Clear all cached configurations."""
    _service_config_cache.clear()
    _cache_timestamps.clear()
