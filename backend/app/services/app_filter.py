"""
Centralized App Filtering Service.

This service determines:
- Which apps count toward screen time limits (trackable vs hidden)
- App categories (games, browsers, communication, etc.)
- Human-friendly display names

Configuration is loaded from app-config.json and applies immediately to all incoming data.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Set
from functools import lru_cache


class AppFilterService:
    """Centralized app filtering and categorization."""
    
    _instance = None
    _config: Dict = {}
    _blacklist_patterns: List[str] = []
    _whitelist: Dict[str, List[str]] = {}
    _friendly_names: Dict[str, str] = {}
    _whitelist_lookup: Set[str] = set()
    
    def __new__(cls):
        """Singleton pattern - one instance for entire backend."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _get_config_path(self) -> Path:
        """Get path to app-config.json."""
        # Path is backend/config/app-config.json
        # This file is in backend/app/services/
        return Path(__file__).parent.parent.parent / "config" / "app-config.json"
    
    def _load_config(self):
        """Load configuration from JSON file."""
        config_path = self._get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                
            self._blacklist_patterns = [p.lower() for p in self._config.get("blacklistPatterns", [])]
            self._whitelist = self._config.get("whitelist", {})
            self._friendly_names = {k.lower(): v for k, v in self._config.get("friendlyNames", {}).items()}
            
            # Build lookup set for whitelist (all categories combined)
            self._whitelist_lookup = set()
            for category_apps in self._whitelist.values():
                for app in category_apps:
                    self._whitelist_lookup.add(app.lower())
                    
        except FileNotFoundError:
            print(f"Warning: App config not found at {config_path}")
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in app config: {e}")
    
    def reload_config(self):
        """Reload configuration from file. Call this after editing app-config.json."""
        self._load_config()
        # Clear any caches
        self.is_trackable.cache_clear()
        self.get_category.cache_clear()
    
    @lru_cache(maxsize=1024)
    def is_trackable(self, app_name: str) -> bool:
        """
        Returns True if app should count toward screen time.
        
        Strategy:
        1. If app matches any blacklist pattern -> NOT trackable (hidden)
        2. If app is in whitelist -> trackable
        3. Default: trackable (unknown apps are shown, can be blacklisted later)
        """
        if not app_name:
            return False
            
        app_lower = app_name.lower()
        
        # Check blacklist patterns (substring match)
        for pattern in self._blacklist_patterns:
            if pattern in app_lower:
                return False
        
        # Additional hardcoded system processes that should never be tracked
        system_processes = {
            'idle', 'system', 'registry', 'smss', 'csrss', 'wininit',
            'services', 'lsass', 'svchost', 'winlogon', 'dwm',
            'memory compression', 'secure system', 'vmtoolsd',
            'tabtip', 'useroobe', 'aggregatorhost'
        }
        if app_lower in system_processes:
            return False
        
        return True
    
    @lru_cache(maxsize=1024)
    def get_category(self, app_name: str) -> Optional[str]:
        """
        Returns category like 'games', 'browsers', 'communication'.
        Returns None if app is not in any known category.
        """
        if not app_name:
            return None
            
        app_lower = app_name.lower()
        
        for category, apps in self._whitelist.items():
            for app in apps:
                if app.lower() == app_lower or app.lower() in app_lower:
                    return category
        
        return None
    
    def get_friendly_name(self, app_name: str) -> str:
        """
        Returns human-readable name.
        E.g., 'msedge' -> 'Microsoft Edge'
        """
        if not app_name:
            return app_name
            
        clean_name = app_name.lower()
        if clean_name.endswith('.exe'):
            clean_name = clean_name[:-4]
            
        return self._friendly_names.get(clean_name, app_name)
    
    def get_icon_type(self, app_name: str) -> str:
        """
        Returns icon type based on category.
        E.g., 'games' -> 'game', 'browsers' -> 'globe'
        """
        icon_mapping = self._config.get("iconMapping", {})
        category = self.get_category(app_name)
        
        if category and category in icon_mapping:
            return icon_mapping[category]
        
        return "app"  # Default icon
    
    def filter_usage_logs(self, logs: List[Dict]) -> List[Dict]:
        """
        Process a list of usage logs, adding metadata.
        
        Each log gets:
        - is_trackable: bool (counts toward limits)
        - category: str or None
        - friendly_name: str
        - icon_type: str
        """
        result = []
        for log in logs:
            app_name = log.get("app_name", "")
            
            enhanced_log = {
                **log,
                "is_trackable": self.is_trackable(app_name),
                "category": self.get_category(app_name),
                "friendly_name": self.get_friendly_name(app_name),
                "icon_type": self.get_icon_type(app_name)
            }
            result.append(enhanced_log)
        
        return result


# Global singleton instance
app_filter = AppFilterService()
