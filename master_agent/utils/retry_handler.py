"""
Retry logic with exponential backoff for API failures.
"""
import logging
import asyncio
import time
from functools import wraps
from google.api_core.exceptions import (
    ResourceExhausted,
    DeadlineExceeded,
    ServiceUnavailable,
    TooManyRequests,
)

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 5
RETRY_MIN_WAIT = 1
RETRY_MAX_WAIT = 60
RETRY_MULTIPLIER = 2


def async_with_retry(max_retries=MAX_RETRIES):
    """
    Decorator for async functions with exponential backoff.
    
    Usage:
        @async_with_retry(max_retries=3)
        async def my_api_call():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            wait_time = RETRY_MIN_WAIT
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (ResourceExhausted, TooManyRequests, ServiceUnavailable, DeadlineExceeded) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"🔄 [{func.__name__}] Attempt {attempt + 1}/{max_retries} failed: {e.__class__.__name__}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                        wait_time = min(wait_time * RETRY_MULTIPLIER, RETRY_MAX_WAIT)
                    else:
                        logger.error(f"❌ [{func.__name__}] All {max_retries} attempts failed")
                        raise
                except Exception as e:
                    # Don't retry non-transient errors
                    if "429" in str(e) or "Resource exhausted" in str(e):
                        # It's a rate limit error in disguise
                        last_exception = e
                        if attempt < max_retries - 1:
                            logger.warning(f"🔄 [{func.__name__}] Rate limit detected, retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            wait_time = min(wait_time * RETRY_MULTIPLIER, RETRY_MAX_WAIT)
                            continue
                    logger.error(f"❌ [{func.__name__}] Non-retryable error: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator


def with_retry(max_retries=MAX_RETRIES):
    """
    Decorator for sync functions with exponential backoff.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            wait_time = RETRY_MIN_WAIT
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ResourceExhausted, TooManyRequests, ServiceUnavailable, DeadlineExceeded) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"🔄 [{func.__name__}] Attempt {attempt + 1}/{max_retries} failed. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        wait_time = min(wait_time * RETRY_MULTIPLIER, RETRY_MAX_WAIT)
                    else:
                        logger.error(f"❌ [{func.__name__}] All {max_retries} attempts failed")
                        raise
                except Exception as e:
                    logger.error(f"❌ [{func.__name__}] Non-retryable error: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator
