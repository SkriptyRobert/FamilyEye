"""Session tracking logic."""
import time
from typing import Dict, List
from datetime import datetime
from ..logger import get_logger

class SessionTracker:
    """Handles app session tracking and kill history."""
    
    def __init__(self):
        self.logger = get_logger("monitor.session")
        self.app_session_start: Dict[str, float] = {}  # app_name -> session start monotonic
        self.process_start_times: Dict[str, float] = {}  # app_name -> timestamp (ISO)
        self.kill_history: List[Dict] = []
        
        # We need a lock, but Python's GIL often suffices for simple dict ops.
        # However, for consistency with previous Monitor, we assume caller handles sync OR we use threading.Lock.
        # The main Core module will likely hold the big lock.
        
    def track_app_session(self, app_name: str):
        """Track when an app session starts (for session duration)."""
        app_lower = app_name.lower()
        current_mono = time.monotonic()
        
        # Record first seen time today
        if app_lower not in self.process_start_times:
            self.process_start_times[app_lower] = datetime.now().isoformat()
            self.logger.debug(f"First detection today: {app_name}")
        
        # Record session start if not already running
        if app_lower not in self.app_session_start:
            self.app_session_start[app_lower] = current_mono
            
    def end_app_session(self, app_name: str):
        """End an app session (app no longer detected)."""
        app_lower = app_name.lower()
        if app_lower in self.app_session_start:
            del self.app_session_start[app_lower]
            
    def get_process_session_duration(self, app_name: str) -> float:
        """Return how long an app has been running in current session (seconds)."""
        app_lower = app_name.lower()
        if app_lower in self.app_session_start:
            return time.monotonic() - self.app_session_start[app_lower]
        return 0.0
        
    def get_first_seen_time(self, app_name: str) -> Optional[str]:
        return self.process_start_times.get(app_name.lower())

    def log_process_kill(self, app_name: str, reason: str, used_seconds: int, 
                         limit_seconds: int, device_uptime_str: str, lock):
        """Log when a process is killed."""
        timestamp = datetime.now().isoformat()
        kill_entry = {
            "app_name": app_name,
            "reason": reason,
            "timestamp": timestamp,
            "used_seconds": used_seconds,
            "limit_seconds": limit_seconds,
            "device_uptime": device_uptime_str
        }
        
        with lock:
            self.kill_history.append(kill_entry)
            # Keep only last 100 entries
            if len(self.kill_history) > 100:
                self.kill_history = self.kill_history[-100:]
        
        self.logger.info(f"Process killed: {app_name} (reason: {reason}, used: {used_seconds}s/{limit_seconds}s)")
        
    def get_kill_history(self, lock) -> List[Dict]:
        """Return recent kill history."""
        with lock:
            return list(self.kill_history)
            
    def clear_kill_history(self, lock):
        """Clear kill history."""
        with lock:
            self.kill_history.clear()
            
    def clear_daily_stats(self):
        """Clear daily session stats."""
        self.app_session_start.clear()
        # Keep process_start_times? Yes, usually relevant for "first seen today". 
        # But if it's a new day, we should probably clear it.
        self.process_start_times.clear()

    @staticmethod
    def is_screen_locked() -> bool:
        """Check if screen is currently locked or on secure desktop (UAC/Login)."""
        import ctypes
        
        try:
            user32 = ctypes.windll.user32
            # DESKTOP_SWITCHDESKTOP = 0x0100
            # If we fail to open desktop with this right, it usually means it's locked/UAC
            hDesktop = user32.OpenInputDesktop(0, False, 0x0100)
            
            if hDesktop == 0:
                # Could not open input desktop - assume locked
                return True
                
            user32.CloseDesktop(hDesktop)
            return False
            
        except Exception:
            # Fallback safe assumption
            return False
