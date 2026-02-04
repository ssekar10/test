"""Configuration and caching for Dialogflow expert."""

from typing import Optional
import time

# Cache storage with timestamps
_config_cache = {}
_intents_cache = {}
_webhooks_cache = {}

# Cache TTL (5 minutes = 300 seconds)
CACHE_TTL = 300

# Default location for Dialogflow agents
DEFAULT_LOCATION = "us"

# Common Dialogflow CX regions (for reference/validation)
COMMON_LOCATIONS = [
    "us",                       # USA multi-region
    "global",                   # Global multi-region
    "us-central1",              # Iowa, USA
    "us-east1",                 # South Carolina, USA
    "us-west1",                 # Oregon, USA
    "northamerica-northeast1",  # Montréal, Canada
    "europe-west1",             # Belgium
    "europe-west2",             # London, UK
    "europe-west3",             # Frankfurt, Germany
    "europe-west4",             # Netherlands
    "europe-west6",             # Zurich, Switzerland
    "australia-southeast1",     # Sydney, Australia
    "asia-northeast1",          # Tokyo, Japan
    "asia-south1",              # Mumbai, India
    "asia-southeast1",          # Singapore
    "asia-southeast2",          # Jakarta, Indonesia
]


# ---------- Configuration Cache ----------

def get_cached_config(key: str) -> Optional[str]:
    """Get cached agent configuration if not expired.
    
    Args:
        key: Cache key (typically agent_id_location format)
    
    Returns:
        Cached JSON string if available and fresh, None otherwise
    """
    if key in _config_cache:
        data, timestamp = _config_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        # Cache expired, remove it
        del _config_cache[key]
    return None


def set_cached_config(key: str, data: str):
    """Cache agent configuration with timestamp.
    
    Args:
        key: Cache key (typically agent_id_location format)
        data: JSON string to cache
    """
    _config_cache[key] = (data, time.time())


def clear_config_cache():
    """Clear all cached configurations."""
    _config_cache.clear()


# ---------- Intents Cache ----------

def get_cached_intents(key: str) -> Optional[str]:
    """Get cached intents list if not expired.
    
    Args:
        key: Cache key (typically agent_id_location_intents format)
    
    Returns:
        Cached JSON string if available and fresh, None otherwise
    """
    if key in _intents_cache:
        data, timestamp = _intents_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        # Cache expired, remove it
        del _intents_cache[key]
    return None


def set_cached_intents(key: str, data: str):
    """Cache intents list with timestamp.
    
    Args:
        key: Cache key (typically agent_id_location_intents format)
        data: JSON string to cache
    """
    _intents_cache[key] = (data, time.time())


def clear_intents_cache():
    """Clear all cached intents."""
    _intents_cache.clear()


# ---------- Webhooks Cache ----------

def get_cached_webhooks(key: str) -> Optional[str]:
    """Get cached webhooks list if not expired.
    
    Args:
        key: Cache key (typically agent_id_location_webhooks format)
    
    Returns:
        Cached JSON string if available and fresh, None otherwise
    """
    if key in _webhooks_cache:
        data, timestamp = _webhooks_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
        # Cache expired, remove it
        del _webhooks_cache[key]
    return None


def set_cached_webhooks(key: str, data: str):
    """Cache webhooks list with timestamp.
    
    Args:
        key: Cache key (typically agent_id_location_webhooks format)
        data: JSON string to cache
    """
    _webhooks_cache[key] = (data, time.time())


def clear_webhooks_cache():
    """Clear all cached webhooks."""
    _webhooks_cache.clear()


# ---------- Cache Management ----------

def clear_all_caches():
    """Clear all caches (config, intents, webhooks)."""
    clear_config_cache()
    clear_intents_cache()
    clear_webhooks_cache()
    print("[DialogflowCache] All caches cleared")


def get_cache_stats() -> dict:
    """Get statistics about current cache usage.
    
    Returns:
        Dictionary with cache counts and memory usage info
    """
    now = time.time()
    
    # Count expired vs active entries
    active_configs = sum(1 for _, ts in _config_cache.values() if now - ts < CACHE_TTL)
    active_intents = sum(1 for _, ts in _intents_cache.values() if now - ts < CACHE_TTL)
    active_webhooks = sum(1 for _, ts in _webhooks_cache.values() if now - ts < CACHE_TTL)
    
    return {
        "cache_ttl_seconds": CACHE_TTL,
        "config_cache": {
            "total_entries": len(_config_cache),
            "active_entries": active_configs,
            "expired_entries": len(_config_cache) - active_configs,
        },
        "intents_cache": {
            "total_entries": len(_intents_cache),
            "active_entries": active_intents,
            "expired_entries": len(_intents_cache) - active_intents,
        },
        "webhooks_cache": {
            "total_entries": len(_webhooks_cache),
            "active_entries": active_webhooks,
            "expired_entries": len(_webhooks_cache) - active_webhooks,
        },
        "total_active_entries": active_configs + active_intents + active_webhooks,
    }


# ---------- Utility Functions ----------

def is_valid_location(location: str) -> bool:
    """Check if a location string is in the list of common Dialogflow CX locations.
    
    Args:
        location: Location ID to validate
    
    Returns:
        True if location is in COMMON_LOCATIONS, False otherwise
    """
    return location in COMMON_LOCATIONS


def get_default_location() -> str:
    """Get the default location for Dialogflow queries.
    
    Returns:
        Default location string
    """
    return DEFAULT_LOCATION
