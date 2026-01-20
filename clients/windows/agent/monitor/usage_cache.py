"""Usage stats caching utilities."""
import os
import sys
import time
import psutil
import json
from collections import defaultdict
from typing import Dict
from ..logger import get_logger

class UsageCache:
    """Handles usage stats persistence."""
    
    def __init__(self):
        self.logger = get_logger("monitor.cache")
        
    def get_cache_path(self):
        """Get path for usage cache file."""
        if getattr(sys, 'frozen', False):
            # Use ProgramData for cache
            program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
            base_dir = os.path.join(program_data, 'FamilyEye', 'Agent')
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, 'usage_cache.json')
        else:
            return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usage_cache.json')
            
    def save(self, usage_today: Dict[str, float], usage_pending: Dict[str, float],
             device_usage_today: float, device_usage_pending: float, boot_time: float):
        """Save current usage stats to local cache using Monotonic Time."""
        try:
            # Use Monotonic Timestamp for internal validity check
            ts = time.time() 
            mono_ts = time.monotonic()
            
            cache_data = {
                "timestamp": ts,               # Wall clock (debug only)
                "monotonic_timestamp": mono_ts,# Trusted internal clock
                "boot_time": boot_time,        # Reboot detection ID
                "usage_today": dict(usage_today),
                "usage_pending": dict(usage_pending),
                "device_usage_today": device_usage_today,
                "device_usage_pending": device_usage_pending
            }
            with open(self.get_cache_path(), 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            self.logger.error(f"Failed to cache usage stats: {e}")
            
    def load(self, usage_today: Dict[str, float], usage_pending: Dict[str, float]) -> tuple:
        """Load usage stats from local cache with Strict Monotonic Validation.
        
        Args:
            usage_today: Dict to populate with loaded data
            usage_pending: Dict to populate with loaded data
            
        Returns:
            Tuple of (device_usage_today, device_usage_pending)
        """
        device_usage_today = 0.0
        device_usage_pending = 0.0
        
        try:
            cache_path = self.get_cache_path()
            if not os.path.exists(cache_path):
                return 0.0, 0.0
                
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # CACHE VALIDATION (Strict Mode)
            cache_boot = cache_data.get("boot_time", 0)
            cache_mono = cache_data.get("monotonic_timestamp", 0)
            
            current_boot = psutil.boot_time() # Fresh boot time
            current_mono = time.monotonic()
            
            # 1. REBOOT CHECK
            if abs(cache_boot - current_boot) > 5:
                self.logger.info(f"System reboot detected (Boot delta: {abs(cache_boot - current_boot):.1f}s). Starting fresh.")
                return 0.0, 0.0

            # 2. MONOTONIC AGE CHECK
            age = current_mono - cache_mono
            if age > 3600:
                self.logger.info(f"Cache expired (Age: {age:.0f}s > 3600s). Starting fresh.")
                return 0.0, 0.0
            
            # 3. FUTURE CHECK
            if age < -10:
                self.logger.warning(f"Cache from future detected ({age:.0f}s). Discarding.")
                return 0.0, 0.0
            
            # Load today's cumulative stats
            cached_today = cache_data.get("usage_today", cache_data.get("app_usage", {}))
            for app, duration in cached_today.items():
                usage_today[app] = duration
            
            device_usage_today = cache_data.get("device_usage_today", 0.0)
                
            # Load pending stats
            cached_pending = cache_data.get("usage_pending", {})
            for app, duration in cached_pending.items():
                usage_pending[app] = duration
            
            device_usage_pending = cache_data.get("device_usage_pending", 0.0)
                
            self.logger.info(f"Loaded usage stats (Apps: {len(usage_today)}, Active: {int(device_usage_today)}s, Cache Age: {int(age)}s)")
            
            return device_usage_today, device_usage_pending
            
        except Exception as e:
            self.logger.warning(f"Failed to load cached usage: {e}")
            return 0.0, 0.0
    
    def clear(self):
        """Delete cache file."""
        try:
            cache_path = self.get_cache_path()
            if os.path.exists(cache_path):
                os.remove(cache_path)
        except Exception:
            pass
