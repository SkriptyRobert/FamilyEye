"""Configuration management for Windows agent."""
import json
import os
from pathlib import Path
from typing import Optional

import sys

# Determine path to config/executable
try:
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        # Use ProgramData for config to allow sharing between Service and User
        program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
        BASE_DIR = Path(program_data) / "FamilyEye" / "Agent"
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Migration: If invalid/missing in ProgramData, check Program Files (Legacy)
        CONFIG_FILE = BASE_DIR / "config.json"
        
        legacy_dir = Path(sys.executable).parent
        legacy_config = legacy_dir / "config.json"
        
        if not CONFIG_FILE.exists() and legacy_config.exists():
            try:
                # Copy legacy config to new location
                with open(legacy_config, 'r') as src, open(CONFIG_FILE, 'w') as dst:
                    dst.write(src.read())
                print(f"[CONFIG] Migrated legacy config to {CONFIG_FILE}")
            except Exception as e:
                print(f"[CONFIG] Failed to migrate legacy config: {e}")

    else:
        # Running as script
        BASE_DIR = Path(__file__).parent.parent
        CONFIG_FILE = BASE_DIR / "config.json"
        
except Exception as e:
    BASE_DIR = Path(".")
    CONFIG_FILE = Path("config.json")

# Load defaults from environment or use defaults
def get_default_config():
    """Get default configuration from environment or defaults."""
    return {
        "backend_url": os.getenv("BACKEND_URL", "https://localhost:8000"),
        "device_id": os.getenv("DEVICE_ID", ""),
        "api_key": os.getenv("API_KEY", ""),
        "polling_interval": int(os.getenv("AGENT_POLLING_INTERVAL", "30")),
        "reporting_interval": int(os.getenv("AGENT_REPORTING_INTERVAL", "300")),
        "cache_duration": int(os.getenv("AGENT_CACHE_DURATION", "300")),
        "ssl_verify": os.getenv("AGENT_SSL_VERIFY", "false").lower() == "true",  # False for self-signed certs
        
        "sync_max_age_seconds": int(os.getenv("AGENT_SYNC_MAX_AGE", "3600")),
        "max_queue_size": int(os.getenv("AGENT_MAX_QUEUE_SIZE", "500")),
        "window_enum_cache_ms": int(os.getenv("AGENT_WINDOW_CACHE_MS", "500")),
        "shutdown_warning_countdown": int(os.getenv("AGENT_SHUTDOWN_WARNING", "60")),
        "monitor_interval": int(os.getenv("AGENT_MONITOR_INTERVAL", "5")), # Fast loop for usage counting
    }

DEFAULT_CONFIG = get_default_config()


class Config:
    """Configuration manager."""
    
    def __init__(self, config_file: str = None):
        self.config_file = Path(config_file) if config_file else CONFIG_FILE
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """Load configuration from file."""
        defaults = get_default_config()
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    merged = defaults.copy()
                    merged.update(config)
                    return merged
            except Exception as e:
                print(f"[CONFIG] Error loading config: {e}")
                return defaults.copy()
        return defaults.copy()
    
    def save_config(self):
        """Save configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value."""
        self.config[key] = value
        self.save_config()
    
    def is_configured(self) -> bool:
        """Check if agent is configured."""
        return bool(self.config.get("device_id") and self.config.get("api_key"))
    
    def get_ssl_verify(self) -> bool:
        """Get SSL verification setting. False = accept self-signed certificates."""
        return self.config.get("ssl_verify", False)


config = Config()

