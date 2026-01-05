"""Simple TTL cache for API responses.

This provides a lightweight in-memory cache to reduce database load
for frequently accessed statistics endpoints. No external dependencies needed.
"""
import time
import threading
from functools import wraps
from typing import Any, Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL support.
    
    Designed for minimal resource usage:
    - No external dependencies (no Redis)
    - Automatic cleanup of expired entries
    - Thread-safe operations
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
            max_size: Maximum number of cached items (prevents memory bloat)
        """
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if time.time() < expires_at:
                    logger.debug(f"Cache HIT: {key}")
                    return value
                # Expired - remove it
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache with TTL."""
        with self._lock:
            # Prevent unbounded growth
            if len(self._cache) >= self.max_size:
                self._cleanup_expired()
                # If still too large, remove oldest 10%
                if len(self._cache) >= self.max_size:
                    self._evict_oldest(int(self.max_size * 0.1))
            
            self._cache[key] = (value, time.time() + (ttl or self.default_ttl))
            logger.debug(f"Cache SET: {key}")
    
    def delete(self, key: str):
        """Remove specific key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching a pattern (simple prefix match)."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug(f"Cleared {len(keys_to_delete)} keys matching '{pattern}'")
    
    def _cleanup_expired(self):
        """Remove all expired entries (called within lock)."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for key in expired_keys:
            del self._cache[key]
    
    def _evict_oldest(self, count: int):
        """Evict oldest entries (called within lock)."""
        sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
        for key, _ in sorted_items[:count]:
            del self._cache[key]
    
    @property
    def size(self) -> int:
        """Current number of items in cache."""
        return len(self._cache)


# Global cache instances for different use cases
stats_cache = SimpleCache(default_ttl=300, max_size=500)  # 5 min TTL for stats


def cache_response(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache endpoint responses.
    
    Usage:
        @cache_response(ttl=300, key_prefix="usage_by_hour")
        async def get_usage_by_hour(device_id: int, days: int, ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and relevant parameters
            # Extract device_id and other params from kwargs
            device_id = kwargs.get('device_id', args[0] if args else 'unknown')
            
            # Build key from relevant parameters
            key_parts = [key_prefix or func.__name__, str(device_id)]
            for k, v in sorted(kwargs.items()):
                if k not in ('current_user', 'db'):  # Skip non-cacheable params
                    key_parts.append(f"{k}={v}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached = stats_cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            stats_cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_device_cache(device_id: int):
    """Invalidate all cached stats for a specific device."""
    stats_cache.clear_pattern(f"usage_by_hour:{device_id}")
    stats_cache.clear_pattern(f"usage_trends:{device_id}")
    stats_cache.clear_pattern(f"weekly_pattern:{device_id}")
    stats_cache.clear_pattern(f"app_details:{device_id}")
    stats_cache.clear_pattern(f"app_trends:{device_id}")
    logger.info(f"Invalidated cache for device {device_id}")
