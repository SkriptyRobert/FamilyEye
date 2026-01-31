"""Rule caching utilities for offline resilience."""
import os
import json
import time
from typing import Dict, List, Optional
from ..logger import get_logger


class RuleCache:
    """Handles rule caching for offline operation."""
    
    def __init__(self):
        self.logger = get_logger('ENFORCER.CACHE')
        
    def get_cache_path(self) -> str:
        """Get path for rules cache file."""
        import sys
        if getattr(sys, 'frozen', False):
            # Use ProgramData for cache
            program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
            base_dir = os.path.join(program_data, 'FamilyEye', 'Agent')
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, 'rules_cache.json')
        else:
            return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rules_cache.json')
        
    def save(self, rules: List[Dict], usage_by_app: Dict[str, int], 
             daily_usage: int, get_utc_timestamp) -> None:
        """Save current rules to local cache.
        
        Args:
            rules: List of rule dictionaries
            usage_by_app: Dict of app name to usage seconds
            daily_usage: Total device usage today in seconds
            get_utc_timestamp: Callable that returns current UTC timestamp
        """
        try:
            cache_data = {
                "timestamp": get_utc_timestamp(),
                "rules": rules,
                "usage_by_app": usage_by_app,
                "daily_usage": daily_usage
            }
            with open(self.get_cache_path(), 'w') as f:
                json.dump(cache_data, f)
            self.logger.debug("Rules cached locally")
        except Exception as e:
            self.logger.error(f"Failed to cache rules: {e}")
            
    def load(self) -> Optional[Dict]:
        """Load rules from local cache.
        
        Returns:
            Dict with keys: rules, usage_by_app, daily_usage, or None if failed
        """
        try:
            cache_path = self.get_cache_path()
            if not os.path.exists(cache_path):
                return None
                
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # Check cache age (optional, maybe warn if too old)
            cache_ts = cache_data.get("timestamp", 0)
            cache_age = time.time() - cache_ts
            
            result = {
                "rules": cache_data.get("rules", []),
                "usage_by_app": cache_data.get("usage_by_app", {}),
                "daily_usage": cache_data.get("daily_usage", 0),
                "cache_age_seconds": int(cache_age)
            }
            
            self.logger.info(f"Loaded {len(result['rules'])} rules from local cache (age: {int(cache_age/60)}m)")
            return result
        except Exception as e:
            self.logger.warning(f"Failed to load cached rules: {e}")
            return None
