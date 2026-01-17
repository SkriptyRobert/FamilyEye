"""
Rate limiting utility for FamilyEye API.
Simple in-memory rate limiter for standalone deployments.
"""
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter.
    Thread-safe using locks.
    """
    
    def __init__(self):
        # Store: {ip: [(timestamp1, count1), ...]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
    
    def _cleanup_old_entries(self, ip: str, window_seconds: int):
        """Remove entries older than the window."""
        current_time = time.time()
        cutoff = current_time - window_seconds
        self._requests[ip] = [
            ts for ts in self._requests[ip] 
            if ts > cutoff
        ]
    
    def is_allowed(self, ip: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            ip: Client IP address
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        with self._lock:
            current_time = time.time()
            
            # Cleanup old entries
            self._cleanup_old_entries(ip, window_seconds)
            
            # Count requests in window
            request_count = len(self._requests[ip])
            
            if request_count >= max_requests:
                remaining = 0
                return False, remaining
            
            # Record this request
            self._requests[ip].append(current_time)
            remaining = max_requests - request_count - 1
            return True, remaining
    
    def get_retry_after(self, ip: str, window_seconds: int) -> int:
        """Get seconds until the oldest request expires from the window."""
        with self._lock:
            if not self._requests[ip]:
                return 0
            oldest = min(self._requests[ip])
            retry_after = int(window_seconds - (time.time() - oldest)) + 1
            return max(0, retry_after)


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(
    ip: str, 
    endpoint: str = "default",
    max_requests: int = 10, 
    window_seconds: int = 60
) -> Tuple[bool, int, int]:
    """
    Check rate limit for an IP and endpoint.
    
    Args:
        ip: Client IP
        endpoint: Endpoint name (for different limits per endpoint)
        max_requests: Max requests allowed
        window_seconds: Time window
        
    Returns:
        Tuple of (is_allowed, remaining, retry_after)
    """
    # Create unique key for IP + endpoint
    key = f"{ip}:{endpoint}"
    
    is_allowed, remaining = rate_limiter.is_allowed(key, max_requests, window_seconds)
    
    if not is_allowed:
        retry_after = rate_limiter.get_retry_after(key, window_seconds)
        logger.warning(f"Rate limit exceeded for {ip} on {endpoint}")
        return False, 0, retry_after
    
    return True, remaining, 0
