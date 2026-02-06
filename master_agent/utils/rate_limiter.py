"""
Async-aware rate limiting for all API calls.
Prevents 429 Resource Exhausted errors.
"""
import time
import logging
import asyncio
from collections import deque
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe and async-safe sliding window rate limiter."""
    
    def __init__(self, max_calls: int = 100, window_seconds: float = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = deque()
        self.sync_lock = Lock()
        self._async_lock = None
        logger.info(f"RateLimiter initialized: {max_calls} calls per {window_seconds}s")
    
    def _get_async_lock(self):
        """Lazy-load async lock."""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock
    
    async def acquire(self):
        """Async rate limit acquisition."""
        lock = self._get_async_lock()
        async with lock:
            now = time.time()
            self._cleanup(now)
            
            if len(self.calls) >= self.max_calls:
                oldest_call = self.calls[0]
                sleep_time = self.window_seconds - (now - oldest_call) + 0.1
                
                if sleep_time > 0:
                    logger.warning(f"⏳ Rate limit reached, sleeping {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)
                    await self.acquire()
                    return
            
            self.calls.append(now)
    
    def acquire_sync(self):
        """Sync rate limit acquisition."""
        with self.sync_lock:
            now = time.time()
            self._cleanup(now)
            
            if len(self.calls) >= self.max_calls:
                oldest_call = self.calls[0]
                sleep_time = self.window_seconds - (now - oldest_call) + 0.1
                
                if sleep_time > 0:
                    logger.warning(f"⏳ Rate limit reached, sleeping {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                    self.acquire_sync()
                    return
            
            self.calls.append(now)
    
    def _cleanup(self, now):
        """Remove expired calls from window."""
        while self.calls and self.calls[0] < now - self.window_seconds:
            self.calls.popleft()
    
    def get_stats(self):
        """Get current rate limit status."""
        now = time.time()
        self._cleanup(now)
        return {
            "current_calls": len(self.calls),
            "max_calls": self.max_calls,
            "window_seconds": self.window_seconds,
            "remaining": self.max_calls - len(self.calls),
            "utilization": f"{(len(self.calls) / self.max_calls) * 100:.1f}%"
        }


# Global rate limiters
rate_limiter = RateLimiter(max_calls=100, window_seconds=60)  # General API
bigquery_rate_limiter = RateLimiter(max_calls=50, window_seconds=60)  # BigQuery specific
