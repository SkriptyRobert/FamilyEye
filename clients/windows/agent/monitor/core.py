"""Core application monitoring orchestrator.

Refactored from monolithic monitor.py for maintainability.
"""
import time
import psutil
import threading
from collections import defaultdict
from typing import Dict, List, Optional
from ..logger import get_logger
from ..config import config

from .usage_cache import UsageCache
from .process_tracking import ProcessTracker
from .window_detection import WindowDetector
from .session import SessionTracker


class AppMonitor:
    """Monitor running applications based on Window Visibility and CLI tools."""
    
    def __init__(self):
        self.logger = get_logger("monitor")
        
        # Sub-modules
        self.usage_cache = UsageCache()
        self.process_tracker = ProcessTracker()
        self.window_detector = WindowDetector(self.process_tracker, config)
        self.session_tracker = SessionTracker()
        
        # Core state
        self.usage_today: Dict[str, float] = defaultdict(float)
        self.usage_pending: Dict[str, float] = defaultdict(float)
        self.lock = threading.Lock()
        
        # Absolute wall-clock active time
        self.device_usage_today = 0.0
        self.device_usage_pending = 0.0
        
        self.app_metadata: Dict[str, Dict] = {} # app_name -> {exe, title, is_focused}
        self.current_detections = {} # app_name -> {pid, original_name, title}
        self.focused_app = None
        self.active_apps = set()
        self.raw_processes = []
        
        self.last_update = time.monotonic()
        self.boot_time = psutil.boot_time()
        self.last_cache_save = time.monotonic()
        self.debug_counter = 0
        
        # Track last report date
        self.last_date = time.strftime('%Y-%m-%d')
        
        # Load cache
        self._load_usage_cache()
        
        self.local_time_provider = None
        self.utc_time_provider = None

    def set_time_providers(self, local_provider, utc_provider):
        """Set trusted time providers."""
        self.local_time_provider = local_provider
        self.utc_time_provider = utc_provider

    def _load_usage_cache(self):
        """Load usage stats from cache."""
        dev_today, dev_pending = self.usage_cache.load(self.usage_today, self.usage_pending)
        self.device_usage_today = dev_today
        self.device_usage_pending = dev_pending
        
    def _save_usage_cache(self):
        """Save usage stats to cache."""
        self.usage_cache.save(
            self.usage_today, self.usage_pending,
            self.device_usage_today, self.device_usage_pending,
            self.boot_time
        )

    def update(self):
        """Update monitoring data - Smart Detection Strategy."""
        current_time = time.monotonic()
        elapsed = current_time - self.last_update
        self.last_update = current_time
        if elapsed <= 0: elapsed = 0.1
        
        # 1. Identify which PID is in the Foreground (Focus)
        self.focused_app = self.window_detector.get_active_window_app()

        # 2. Identify which PIDs have visible windows
        pid_titles = self.window_detector.get_pids_with_visible_windows()
        windowed_pids = set(pid_titles.keys())
        
        # 3. Iterate processes
        running_user_apps = set()
        raw_process_list = []
        self.current_detections = {} 

        try:
            # Use psutil.process_iter only once per tick
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'username']):
                try:
                    app_name = self.process_tracker.get_app_name(proc)
                    if not app_name: continue
                    
                    if self.process_tracker.is_ignored(app_name):
                        continue

                    pid = proc.info['pid']
                    exe_path = proc.info.get('exe')
                    original_name = self.process_tracker.get_original_filename(exe_path) if exe_path else app_name
                    window_title = pid_titles.get(pid, "")

                    # --- Detection Logic ---
                    is_user_app = False
                    
                    # Criteria A: Has a visible window?
                    if pid in windowed_pids:
                        is_user_app = True
                        
                    # Criteria B: Is a known CLI tool?
                    elif self.process_tracker.is_cli_tool(app_name):
                        is_user_app = True
                        
                    # Criteria C: Service Mode Fallback
                    elif not windowed_pids:
                        try:
                            # Safely check username
                            username = proc.info.get('username')
                            if not username: # Fallback if not retrieved initially
                                username = proc.username().lower()
                            else:
                                username = username.lower()
                                
                            if 'authority' not in username and 'system' not in username and 'service' not in username:
                                is_user_app = True
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            pass

                    # Add to raw list
                    raw_process_list.append(f"{app_name} (Orig: {original_name}, PID: {pid})")

                    if is_user_app:
                        # Normalize agent name
                        if app_name.lower() in ["child_agent", "childagent", "agent_service", "familyeye"]:
                            app_name = "FamilyEye Agent"
                        
                        running_user_apps.add(app_name)
                        
                        # Store metadata
                        is_focused = (app_name == self.focused_app)
                        self.app_metadata[app_name] = {
                            "exe": exe_path or app_name,
                            "title": window_title if window_title else (self.app_metadata.get(app_name, {}).get("title", "")),
                            "is_focused": is_focused
                        }

                        # Store metadata for enforcer
                        self.current_detections[app_name] = {
                            "pid": pid,
                            "original_name": original_name,
                            "title": window_title
                        }

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except KeyError:
                    continue
                except Exception as e:
                    continue
        except Exception as e:
            self.logger.error(f"Error in monitor update loop: {e}")

        self.active_apps = running_user_apps
        self.raw_processes = raw_process_list
        
        # DETECT DATE CHANGE
        if self.local_time_provider:
            current_date = self.local_time_provider().strftime('%Y-%m-%d')
        else:
            current_date = time.strftime('%Y-%m-%d')
            
        if current_date != self.last_date:
            self.logger.info(f"New day detected ({current_date}), resetting daily stats.")
            self.reset_daily_stats_internal()
            self.last_date = current_date

        # Apply Usage
        if elapsed <= 0: elapsed = 0
 
        if running_user_apps:
            self.device_usage_today += elapsed
            self.device_usage_pending += elapsed
            
            # Defense against persistent dict corruption (rare but seen before)
            if not isinstance(self.usage_today, defaultdict):
                self.usage_today = defaultdict(float, self.usage_today)
            if not isinstance(self.usage_pending, defaultdict):
                self.usage_pending = defaultdict(float, self.usage_pending)

            try:
                for app_name in running_user_apps:
                    self.usage_today[app_name] += elapsed
                    self.usage_pending[app_name] += elapsed
                    self.session_tracker.track_app_session(app_name)
            except Exception as e:
                self.logger.error(f"Critical error in accumulation loop: {e}")
            
            # End old sessions
            active_list = [a.lower() for a in running_user_apps]
            for app_name in list(self.session_tracker.app_session_start.keys()):
                if app_name not in active_list:
                    self.session_tracker.end_app_session(app_name)
                
        # Periodically save cache
        if current_time - self.last_cache_save > 60:
            self._save_usage_cache()
            self.last_cache_save = current_time
        
        # Debug logging
        self.debug_counter += 1
        if self.debug_counter % 12 == 0:
            tracked_apps = list(self.usage_today.keys())[:10]
            self.logger.debug(f"SmartMonitor: Tracking {len(running_user_apps)} active apps. "
                            f"Focused: {self.focused_app}, Top: {tracked_apps}")

    def reset_daily_stats_internal(self):
        """Reset stats without lock (called from update)."""
        self.usage_today.clear()
        self.usage_pending.clear()
        self.device_usage_today = 0.0
        self.device_usage_pending = 0.0
        self.session_tracker.clear_daily_stats()
        self.usage_cache.clear()

    def get_usage_stats(self) -> Dict[str, float]:
        """Return cumulative stats for today."""
        with self.lock:
            return dict(self.usage_today)
    
    def get_pending_usage(self):
        """Return a copy of pending usage."""
        with self.lock:
            return self.usage_pending.copy()
            
    def snap_pending_usage(self):
        """Return pending usage and clear it."""
        with self.lock:
            snap = self.usage_pending.copy()
            self.usage_pending = defaultdict(float)
            self.device_usage_pending = 0.0
            self._save_usage_cache()
            return snap
            
    def clear_pending_usage(self):
        """Clear pending delta."""
        with self.lock:
            self.usage_pending.clear()
            self.device_usage_pending = 0.0
            self._save_usage_cache()

    def get_device_usage(self) -> float:
        """Return total wall-clock active time for today."""
        return self.device_usage_today

    def reset_daily_stats(self):
        """Full reset with lock."""
        with self.lock:
            self.reset_daily_stats_internal()

    def get_running_processes(self):
        """Return active processes."""
        with self.lock:
            return sorted(list(self.active_apps))

    def get_device_uptime(self) -> float:
        return time.time() - self.boot_time
    
    def get_device_uptime_formatted(self) -> str:
        uptime = self.get_device_uptime()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    def log_process_kill(self, app_name: str, reason: str, used_seconds: int = 0, limit_seconds: int = 0):
        self.session_tracker.log_process_kill(
            app_name, reason, used_seconds, limit_seconds, 
            self.get_device_uptime_formatted(), self.lock
        )
    
    def get_kill_history(self) -> List[Dict]:
        return self.session_tracker.get_kill_history(self.lock)
    
    def clear_kill_history(self):
        self.session_tracker.clear_kill_history(self.lock)
    
    def get_enhanced_usage_stats(self) -> Dict:
        """Return enhanced usage stats for backend reporting."""
        with self.lock:
            stats = {
                "device_uptime_seconds": int(self.get_device_uptime()),
                "device_usage_today_seconds": int(self.device_usage_today),
                "active_apps_count": len(self.active_apps),
                "focused_app": self.focused_app,
                "apps": {}
            }
            
            for app_name, duration in self.usage_today.items():
                meta = self.app_metadata.get(app_name, {})
                start_time = self.session_tracker.get_first_seen_time(app_name)
                session_duration = self.session_tracker.get_process_session_duration(app_name)
                
                stats["apps"][app_name] = {
                    "usage_today_seconds": int(duration),
                    "session_duration_seconds": int(session_duration),
                    "first_seen_today": start_time,
                    "is_active": app_name in self.active_apps,
                    "is_focused": meta.get("is_focused", False),
                    "exe_path": meta.get("exe", ""),
                    "window_title": meta.get("title", "")
                }
            
            return stats
