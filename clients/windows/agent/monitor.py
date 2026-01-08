"""Application monitoring."""
import os
import sys
import psutil
import time
from typing import Dict, Set, Optional, List
from collections import defaultdict
from .logger import get_logger
from .system_noise_filter import system_noise_filter

class AppMonitor:
    """Monitor running applications based on Window Visibility and CLI tools."""
    
    # 1. CLI Tools - Applications without windows that developers/users use
    CLI_TOOLS = {
        'cmd', 'powershell', 'pwsh', 'windowsterminal', 
        'python', 'pythonw', 'py', 
        'node', 'npm', 'git', 'java', 'javac',
        'code', 'cursor', 'vim', 'nvim',
        'ssh', 'ftp', 'bash', 'wsl'
    }

    # NOTE: Filtering moved to Backend (Path A architecture)
    # Agent sends ALL data, Backend decides what counts toward limits
    
    focused_app = None # Class-level or instance level? Instance is better.
    
    # 4. Helper processes to consolidate under main app
    # Maps helper process names to their main app name for unified tracking
    HELPER_TO_MAIN = {
        'steamwebhelper': 'steam',
        'steamservice': 'steam',
        'discordptb': 'discord',
        'discordcanary': 'discord',
        'discord_voice': 'discord',
        'chromedriver': 'chrome',
        'chrome_crashpad': 'chrome',
        'msedgewebview2': 'msedge',
        'firefoxprivatebridge': 'firefox',
        'epicwebhelper': 'epicgameslauncher',
        'riotclientservices': 'riotclient',
        'leagueclientux': 'leagueclient',
        'battlenet_helper': 'battle.net',
    }

    # NOTE: System noise filtering is now handled by SystemNoiseFilter class
    # See system_noise_filter.py for the comprehensive Win10/11 process list
    # Legacy IGNORED_PROCESSES kept for backward compatibility
    IGNORED_PROCESSES = set()  # Delegated to SystemNoiseFilter
    IGNORED_WINDOWS = set()    # Delegated to SystemNoiseFilter
    
    
    def __init__(self):
        self.logger = get_logger("monitor")
        
        # Split tracking model:
        # usage_today: Persistent absolute total for enforcement/local UI
        # usage_pending: Transient delta to be sent to backend
        self.usage_today: Dict[str, float] = defaultdict(float)
        self.usage_pending: Dict[str, float] = defaultdict(float)
        
        import threading
        self.lock = threading.Lock()
        
        # Absolute wall-clock active time (not sum of apps)
        self.device_usage_today = 0.0
        self.device_usage_pending = 0.0
        
        self.app_metadata: Dict[str, Dict] = {} # app_name -> {exe, title, is_focused}
        self.last_update = time.monotonic()
        self.boot_time = psutil.boot_time() # Detect reboots
        self.last_cache_save = time.monotonic()
        self.debug_counter = 0
        self.current_detections = {}
        self.focused_app = None
        self.active_apps = set()
        self.raw_processes = []
        
        # Track last report date to trigger daily reset
        self.last_date = time.strftime('%Y-%m-%d')
        
        # New: Robust identification
        self.metadata_cache: Dict[str, str] = {} # path -> original_filename
        self.pid_titles: Dict[int, str] = {}     # pid -> window_title
        
        # NEW: Enhanced tracking for better parental control
        # Track process start times (when app was first detected today)
        self.process_start_times: Dict[str, float] = {}  # app_name -> timestamp
        # Track process kill history (for enforcer logging)
        self.kill_history: List[Dict] = []  # [{app_name, reason, timestamp, used_seconds, limit_seconds}]
        # Track how long each app has been continuously running
        self.app_session_start: Dict[str, float] = {}  # app_name -> session start monotonic
        
        # Load cached usage logs on startup
        self._load_usage_cache()
        
        self.local_time_provider = None
        self.utc_time_provider = None

    def set_time_providers(self, local_provider, utc_provider):
        """Set trusted time providers (Local for daily reset, UTC for cache)."""
        self.local_time_provider = local_provider
        self.utc_time_provider = utc_provider

    def _get_cache_path(self):
        """Get path for usage cache file."""
        if getattr(sys, 'frozen', False):
            # Use ProgramData for cache
            program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
            base_dir = os.path.join(program_data, 'FamilyEye', 'Agent')
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, 'usage_cache.json')
        else:
            return os.path.join(os.path.dirname(__file__), 'usage_cache.json')
        
    def _save_usage_cache(self):
        """Save current usage stats to local cache using Monotonic Time."""
        try:
            import json
            
            # Use Monotonic Timestamp for internal validity check
            # We still store wall-clock 'timestamp' for debugging/human readability
            ts = time.time() 
            mono_ts = time.monotonic()
            
            # Determine current date using trusted provider if available
            if self.local_time_provider:
                current_date_str = self.local_time_provider().strftime('%Y-%m-%d')
            else:
                current_date_str = time.strftime('%Y-%m-%d')
            
            cache_data = {
                "last_date_str": current_date_str,
                "timestamp": ts,               # Wall clock (debug only)
                "monotonic_timestamp": mono_ts,# Trusted internal clock
                "boot_time": self.boot_time,   # Reboot detection ID
                "usage_today": dict(self.usage_today),
                "usage_pending": dict(self.usage_pending),
                "device_usage_today": self.device_usage_today,
                "device_usage_pending": self.device_usage_pending
            }
            with open(self._get_cache_path(), 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            self.logger.error(f"Failed to cache usage stats: {e}")
            
    def _load_usage_cache(self):
        """Load usage stats from local cache with improved persistence logic."""
        try:
            import json
            cache_path = self._get_cache_path()
            if not os.path.exists(cache_path):
                return
                
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # 1. DATE CHECK (Master Switch)
            # If the cache is from a previous day, we must reset.
            cached_date = cache_data.get("last_date_str", "")
            
            # Determine current date using trusted provider if available
            if self.local_time_provider:
                current_date = self.local_time_provider().strftime('%Y-%m-%d')
            else:
                current_date = time.strftime('%Y-%m-%d')
                
            # If cache has no date (legacy) or date mismatch -> Start Fresh
            if cached_date != current_date:
                self.logger.info(f"Cache from different day ({cached_date} vs {current_date}). Starting fresh.")
                return

            # 2. REBOOT/CRASH DETECTION
            # We want to persist daily totals (usage_today), but we might want to drop 
            # inconsistent pending usage if the system crashed/rebooted.
            
            cache_boot = cache_data.get("boot_time", 0)
            current_boot = psutil.boot_time()
            is_reboot = abs(cache_boot - current_boot) > 5
            
            # Check Monotonic Validity
            cache_mono = cache_data.get("monotonic_timestamp", 0)
            current_mono = time.monotonic()
            
            if is_reboot:
                self.logger.info("System reboot detected within same day. Restoring daily totals, clearing pending.")
                # RESTORE TOTALS
                self.usage_today = defaultdict(float, cache_data.get("usage_today", {}))
                self.device_usage_today = cache_data.get("device_usage_today", 0.0)
                
                # DISCARD PENDING
                # We can't be sure if pending was sent before the crash/reboot.
                # Safer to drop small delta than duplicate or corrupt it.
                self.usage_pending.clear()
                self.device_usage_pending = 0.0
                
            else:
                # Same session - Standard restore
                # Restore everything including pending
                self.usage_today = defaultdict(float, cache_data.get("usage_today", {}))
                self.usage_pending = defaultdict(float, cache_data.get("usage_pending", {}))
                self.device_usage_today = cache_data.get("device_usage_today", 0.0)
                self.device_usage_pending = cache_data.get("device_usage_pending", 0.0)
                
                # Check for major time gaps (e.g. hibernation > 1h) just for logging
                gap = current_mono - cache_mono
                if gap > 3600:
                    self.logger.info(f"Resuming after long sleep/gap ({gap:.0f}s). Stats preserved.")

            self.logger.info(f"Loaded usage stats (Apps: {len(self.usage_today)}, Active: {int(self.device_usage_today)}s)")
            
        except Exception as e:
            self.logger.warning(f"Failed to load cached usage: {e}")

    def _get_pids_with_visible_windows(self) -> Dict[int, str]:
        """Return a mapping of PIDs to their main window title. (Cached)"""
        try:
            from .config import config
            current_time = time.monotonic()
            
            # Check cache (default 500ms)
            cache_ms = config.get("window_enum_cache_ms", 500)
            if hasattr(self, '_window_cache_time') and (current_time - self._window_cache_time) * 1000 < cache_ms:
                return self._window_cache_data
                
            import win32gui
            import win32process
            import win32con

            pid_to_title = {}

            def enum_handler(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd):
                    # Check window style to filter out tooltips/hidden windows
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    if style & win32con.WS_VISIBLE:
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            # Only keep the first (usually main) title found for a PID
                            if pid not in pid_to_title:
                                pid_to_title[pid] = title
            
            win32gui.EnumWindows(enum_handler, None)
            
            # Update cache
            self._window_cache_time = current_time
            self._window_cache_data = pid_to_title
            
            return pid_to_title
            
        except Exception as e:
            self.logger.error(f"Error enumerating windows: {e}")
            return {}

    def _get_original_filename(self, path: str) -> Optional[str]:
        """Read 'OriginalFilename' from PE metadata of an executable."""
        if not path or not os.path.exists(path):
            return None
        
        if path in self.metadata_cache:
            return self.metadata_cache[path]
            
        try:
            import win32api
            # Try to get language and codepage
            try:
                lang, codepage = win32api.GetFileVersionInfo(path, '\\VarFileInfo\\Translation')[0]
                str_info = u'\\StringFileInfo\\%04X%04X\\OriginalFilename' % (lang, codepage)
                orig_name = win32api.GetFileVersionInfo(path, str_info)
                if orig_name:
                    if orig_name.lower().endswith('.exe'):
                        orig_name = orig_name[:-4]
                    res = orig_name.lower()
                    self.metadata_cache[path] = res
                    return res
            except Exception:
                pass
                
            # Default fallbacks or if above fails
            name = os.path.basename(path).lower()
            if name.endswith('.exe'): name = name[:-4]
            self.metadata_cache[path] = name
            return name
        except Exception:
            return None
    
    def _get_app_name(self, proc):
        """Get application name from process, consolidating helpers to main app."""
        try:
            name = proc.name()
            if name.endswith('.exe'):
                name = name[:-4]
            name = name.lower()
            
            # 1. First check explicit mapping for known apps
            if name in self.HELPER_TO_MAIN:
                return self.HELPER_TO_MAIN[name]
            
            # 2. Auto-detect helper processes by common suffixes
            # This makes the system work for ANY app, not just mapped ones
            helper_suffixes = [
                'webhelper', 'helper', 'service', 'launcher', 'crashpad',
                'webview', 'renderer', 'gpu', 'utility', 'broker',
                'updater', 'update', 'tray', 'agent', 'daemon',
                'background', 'worker', 'child', 'subprocess'
            ]
            
            for suffix in helper_suffixes:
                if name.endswith(suffix) and len(name) > len(suffix):
                    # Extract main app name: 'spotifywebhelper' -> 'spotify'
                    main_name = name[:-len(suffix)]
                    # Only use if main name is reasonable (at least 3 chars)
                    if len(main_name) >= 3:
                        return main_name
            
            # 3. Handle numbered suffixes like 'chrome32', 'discord64'
            import re
            match = re.match(r'^(.+?)(32|64|x86|x64)$', name)
            if match:
                return match.group(1)
            
            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def _get_active_window_app(self) -> Optional[str]:
        """Get application name of currently active window (Focus)."""
        try:
            import win32gui
            import win32process
            
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                app_name = self._get_app_name(proc)
                
                # Check if ignored using SystemNoiseFilter
                exe_path = None
                try:
                    exe_path = proc.exe()
                except:
                    pass
                if app_name and system_noise_filter.is_noise(app_name, exe_path):
                    return None
                    
                return app_name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None
        except Exception:
            return None

    def update(self):
        """Update monitoring data - Smart Detection Strategy."""
        current_time = time.monotonic()
        elapsed = current_time - self.last_update
        self.last_update = current_time
        if elapsed <= 0: elapsed = 0.1
        
        # 1. Identify which PID is in the Foreground (Focus) for Smart Insights Tagging
        self.focused_app = None
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _, foreground_pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    f_proc = psutil.Process(foreground_pid)
                    self.focused_app = self._get_app_name(f_proc)
                except:
                    pass
        except Exception:
            pass

        # 2. Identify which PIDs have visible windows and their titles
        self.pid_titles = self._get_pids_with_visible_windows()
        windowed_pids = set(self.pid_titles.keys())
        
        # 3. Iterate processes
        active_apps = set()
        running_user_apps = set()
        raw_process_list = []
        
        # New: Robust mapping of app IDs (name, metadata, title)
        self.current_detections = {} # app_name -> {pid, original_name, title}

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    pid = proc.pid
                    info = proc.info
                    app_name = self._get_app_name(proc)
                    if not app_name: continue
                    
                    # EARLY FILTER: Eliminate system noise immediately
                    exe_path = info.get('exe')
                    if system_noise_filter.is_noise(app_name, exe_path):
                        continue

                    original_name = self._get_original_filename(exe_path) if exe_path else app_name
                    window_title = self.pid_titles.get(pid, "")

                    # --- Detection Logic ---
                    is_user_app = False
                    
                    # Criteria A: Has a visible window?
                    if pid in windowed_pids:
                        is_user_app = True
                        
                    # Criteria B: Is a known CLI tool?
                    elif app_name in self.CLI_TOOLS:
                        is_user_app = True
                        
                    # Criteria C: Service Mode Fallback
                    elif not windowed_pids:
                        try:
                            username = proc.username().lower()
                            if 'authority' not in username and 'system' not in username and 'service' not in username:
                                is_user_app = True
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            pass

                    # Add to raw process list with more info
                    raw_process_list.append(f"{app_name} (Orig: {original_name}, PID: {pid})")

                    if is_user_app:
                        # NOTE: No secondary filter here - "Aktivní procesy" in Statistics
                        # should show ALL detected processes for advanced/technical users
                        
                        # Normalize agent name for branding - STRICT REBRANDING
                        if app_name.lower() in ["child_agent", "childagent", "agent_service", "familyeye"]:
                            app_name = "FamilyEye Agent"
                        
                        running_user_apps.add(app_name)
                        
                        # Store metadata
                        is_focused = (app_name == self.focused_app)
                        # Metadata is only as good as the last detection with a window
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
                except KeyError as e:
                    # Specific catch for dictionary errors (like IGNORED_WINDOWS)
                    # Just skip this process and continue
                    continue
                except Exception as e:
                    self.logger.debug(f"Skipping process {proc.pid}: {e}")
                    continue
        except Exception as e:
            self.logger.error(f"Error in monitor update loop: {e}")

        self.active_apps = running_user_apps
        self.raw_processes = raw_process_list
        
        # DETECT DATE CHANGE (Daily Reset)
        # Use Trusted Local Time for correct "Midnight" detection
        if self.local_time_provider:
            current_date = self.local_time_provider().strftime('%Y-%m-%d')
        else:
            current_date = time.strftime('%Y-%m-%d')
            
        if current_date != self.last_date:
            self.logger.info(f"New day detected ({current_date}), resetting daily stats.")
            self.usage_today.clear()
            self.usage_pending.clear()
            self.device_usage_today = 0.0
            self.device_usage_pending = 0.0
            self.last_date = current_date

        # CAP ELAPSED: Prevent huge jumps if PC was asleep or loop lagged
        if elapsed <= 0:
            elapsed = 0
 
        if running_user_apps:
            # Track absolute wall-clock active time (only once per tick, regardless of app count)
            self.device_usage_today += elapsed
            self.device_usage_pending += elapsed
            
            # Count time for ALL detected user applications
            # DEFENSIVE CHECK: Ensure dictionaries are still defaultdicts
            if not isinstance(self.usage_today, defaultdict):
                self.logger.error(f"CORRUPTION DETECTED: usage_today is {type(self.usage_today)}, restoring defaultdict")
                self.usage_today = defaultdict(float, self.usage_today)
                
            if not isinstance(self.usage_pending, defaultdict):
                self.logger.error(f"CORRUPTION DETECTED: usage_pending is {type(self.usage_pending)}, restoring defaultdict")
                self.usage_pending = defaultdict(float, self.usage_pending)

            try:
                for app_name in running_user_apps:
                    self.usage_today[app_name] += elapsed
                    self.usage_pending[app_name] += elapsed
                    # NEW: Track app session for duration reporting
                    self.track_app_session(app_name)
            except Exception as e:
                self.logger.error(f"Critical error in accumulation loop: {e}")
            
            # NEW: End sessions for apps that are no longer active
            previously_active = set(self.app_session_start.keys())
            for app_name in previously_active:
                if app_name not in [a.lower() for a in running_user_apps]:
                    self.end_app_session(app_name)
                
        elif self.active_apps:
            # If no user apps detected, we don't count time.
            pass
            
        # SYNCHRONIZATION SAFETY CHECK (Time Paradox Fix)
        # Ensure no individual app time exceeds total device time
        # This fixes the "Edge 5m / Active 4m" issue caused by float drift or cache accumulation
        if self.device_usage_today > 0:
            for app_name in list(self.usage_today.keys()):
                if self.usage_today[app_name] > self.device_usage_today:
                    # Allow small float epsilon, but cap significant overage
                    if self.usage_today[app_name] - self.device_usage_today > 1.0:
                        self.logger.debug(f"Time Paradox corrected for {app_name}: {self.usage_today[app_name]:.1f}s -> {self.device_usage_today:.1f}s")
                        self.usage_today[app_name] = self.device_usage_today
        
        # Periodically save cache (e.g. every minute) to minimize data loss on crash
        if current_time - self.last_cache_save > 60:
            self._save_usage_cache()
            self.last_cache_save = current_time
        
        # Debug logging
        self.debug_counter += 1
        if self.debug_counter % 12 == 0:
            total_usage = sum(self.usage_today.values())
            tracked_apps = list(self.usage_today.keys())[:10]
            self.logger.debug(f"SmartMonitor: Tracking {len(running_user_apps)} active apps. "
                            f"Focused: {self.focused_app}, Top: {tracked_apps}")
        

    
    def get_usage_stats(self) -> Dict[str, float]:
        """Return cumulative stats for today (used for local enforcement)."""
        with self.lock:
            return dict(self.usage_today)
    
    def get_pending_usage(self):
        """Return a copy of pending usage (not cleared)."""
        with self.lock:
            return self.usage_pending.copy()
            
    def snap_pending_usage(self):
        """Return pending usage and clear it (for discrete reporting)."""
        with self.lock:
            snap = self.usage_pending.copy()
            self.usage_pending = defaultdict(float)  # FIX: Use defaultdict, not {}
            self.device_usage_pending = 0.0
            self._save_usage_cache()
            return snap
            
    def clear_pending_usage(self):
        """Clear pending delta after successful report."""
        with self.lock:
            self.usage_pending.clear()
            self.device_usage_pending = 0.0
            self._save_usage_cache()

    def get_device_usage(self) -> float:
        """Return total wall-clock active time for today."""
        return self.device_usage_today

    def reset_daily_stats(self):
        """Full reset (e.g. on manual request or local day change)."""
        with self.lock:
            self.usage_today.clear()
            self.usage_pending.clear()
            self.device_usage_today = 0.0
            self.device_usage_pending = 0.0
            # Also clear cache
            try:
                cache_path = self._get_cache_path()
                if os.path.exists(cache_path):
                    os.remove(cache_path)
            except Exception:
                pass

    def get_running_processes(self):
        """Return list of currently active trackable processes (filtered)."""
        with self.lock:
            return sorted(list(self.active_apps))
    
    def get_all_running_processes(self) -> List[str]:
        """Return list of ALL running processes without any filter.
        
        Used for 'Aktivní procesy' in Statistics - gives admins/technical users
        full visibility into what's running on the system.
        """
        try:
            all_processes = set()
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info.get('name', '')
                    if name:
                        # Clean up the name (remove .exe extension for cleaner display)
                        clean_name = name.lower().replace('.exe', '').strip()
                        if clean_name and clean_name not in ('idle', 'system'):
                            all_processes.add(clean_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return sorted(list(all_processes))
        except Exception as e:
            self.logger.error(f"Error getting all processes: {e}")
            return []

    # ========== NEW: Enhanced Tracking Methods ==========
    
    def get_device_uptime(self) -> float:
        """Return device uptime in seconds since last boot."""
        return time.time() - self.boot_time
    
    def get_device_uptime_formatted(self) -> str:
        """Return device uptime as human-readable string."""
        uptime = self.get_device_uptime()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    def log_process_kill(self, app_name: str, reason: str, used_seconds: int = 0, limit_seconds: int = 0):
        """Log when a process is killed with reason and usage details."""
        from datetime import datetime
        
        timestamp = datetime.now().isoformat()
        kill_entry = {
            "app_name": app_name,
            "reason": reason,
            "timestamp": timestamp,
            "used_seconds": used_seconds,
            "limit_seconds": limit_seconds,
            "device_uptime": self.get_device_uptime_formatted()
        }
        
        with self.lock:
            self.kill_history.append(kill_entry)
            # Keep only last 100 entries to prevent memory bloat
            if len(self.kill_history) > 100:
                self.kill_history = self.kill_history[-100:]
        
        self.logger.info(f"Process killed: {app_name} (reason: {reason}, used: {used_seconds}s/{limit_seconds}s)")
    
    def get_kill_history(self) -> List[Dict]:
        """Return recent kill history for reporting."""
        with self.lock:
            return list(self.kill_history)
    
    def clear_kill_history(self):
        """Clear kill history after sending to backend."""
        with self.lock:
            self.kill_history.clear()
    
    def get_process_session_duration(self, app_name: str) -> float:
        """Return how long an app has been running in current session (seconds)."""
        app_lower = app_name.lower()
        if app_lower in self.app_session_start:
            return time.monotonic() - self.app_session_start[app_lower]
        return 0.0
    
    def get_enhanced_usage_stats(self) -> Dict:
        """
        Return enhanced usage stats for backend reporting.
        Includes uptime, process details, and session info.
        """
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
                start_time = self.process_start_times.get(app_name)
                session_duration = self.get_process_session_duration(app_name)
                
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
    
    def track_app_session(self, app_name: str):
        """Track when an app session starts (for session duration)."""
        app_lower = app_name.lower()
        current_mono = time.monotonic()
        
        # Record first seen time today
        if app_lower not in self.process_start_times:
            from datetime import datetime
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
