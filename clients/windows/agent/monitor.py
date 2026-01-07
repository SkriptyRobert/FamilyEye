"""Application monitoring."""
import os
import sys
import psutil
import time
from typing import Dict, Set, Optional
from collections import defaultdict
from .logger import get_logger

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

    # Basic noise reduction for system components that NEVER have useful windows
    # Even without aggressive filtering, these just clutter logs with 0 importance
    IGNORED_PROCESSES = {
        'idle', 'system', 'registry', 'smss', 'csrss', 'wininit', 'services', 'lsass',
        'svchost', 'fontdrvhost', 'winlogon', 'spoolsv', 'dwm', 'ctfmon', 'taskhostw',
        'shellexperiencehost', 'searchhost', 'startmenuexperiencehost', 'userinit',
        'identityhost', 'backgroundtaskhost', 'mobsync', 'hxtsr', 'runonce', 'smartscreen',
        'onedrive', 'taskmgr', 'mmc', 'regedit', 'cmd', 'runtime', 'runtimebroker',
        'applicationframehost', 'textinputhost', 'lockapp', 'securityhealthsystray',
        'phoneexperiencehost', 'searchapp', 'widgets', 'audiodg', 'spoolsv'
    }
    
    # Windows that should be ignored even if they have visible windows
    IGNORED_WINDOWS = IGNORED_PROCESSES
    
    
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
        """Save current usage stats to local cache."""
        try:
            import json
            
            # Use Trusted UTC Timestamp if available
            ts = time.time()
            if self.utc_time_provider:
                ts = self.utc_time_provider().timestamp()
                
            cache_data = {
                "timestamp": ts,
                "boot_time": self.boot_time,
                "usage_today": dict(self.usage_today),
                "usage_pending": dict(self.usage_pending),
                "device_usage_today": self.device_usage_today,
                "device_usage_pending": self.device_usage_pending
            }
            with open(self._get_cache_path(), 'w') as f:
                json.dump(cache_data, f)
            # self.logger.debug("Usage stats cached locally")
        except Exception as e:
            self.logger.error(f"Failed to cache usage stats: {e}")
            
    def _load_usage_cache(self):
        """Load usage stats from local cache."""
        try:
            import json
            cache_path = self._get_cache_path()
            if not os.path.exists(cache_path):
                return
                
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # CACHE AGING & REBOOT DETECTION
            cache_ts = cache_data.get("timestamp", 0)
            cache_boot = cache_data.get("boot_time", 0)
            now = time.time()
            
            # 1. Discard if older than 1 hour (User's request to kill "time travel" bugs)
            if now - cache_ts > 3600:
                self.logger.info("Cache aged out (>1h), starting fresh.")
                return

            # 2. Discard if system rebooted since cache (reality check)
            if abs(cache_boot - self.boot_time) > 5: # 5s tolerance
                self.logger.info("System reboot detected, discarding old cache.")
                return
            
            # Load today's cumulative stats
            cached_today = cache_data.get("usage_today", cache_data.get("app_usage", {}))
            for app, duration in cached_today.items():
                self.usage_today[app] = duration
            
            self.device_usage_today = cache_data.get("device_usage_today", 0.0)
                
            # Load pending stats (delta that failed to send last time)
            cached_pending = cache_data.get("usage_pending", {})
            for app, duration in cached_pending.items():
                self.usage_pending[app] = duration
            
            self.device_usage_pending = cache_data.get("device_usage_pending", 0.0)
                
            self.logger.info(f"Loaded usage stats (Today: {len(self.usage_today)} apps, Total Active: {int(self.device_usage_today)}s)")
        except Exception as e:
            self.logger.warning(f"Failed to load cached usage: {e}")

    def _get_pids_with_visible_windows(self) -> Dict[int, str]:
        """Return a mapping of PIDs to their main window title."""
        pid_to_title = {}
        try:
            import win32gui
            import win32process
            import win32con

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
        except Exception as e:
            self.logger.error(f"Error enumerating windows: {e}")
        return pid_to_title

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
                
                # Check if ignored
                if app_name and (app_name in self.IGNORED_WINDOWS or 
                               app_name in self.IGNORED_PROCESSES):
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
                    if app_name in self.IGNORED_PROCESSES:
                        continue

                    exe_path = info.get('exe')
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
            
            # Count time for ALL detected user applications (including background ones with windows)
            # This ensures multitasking is reflected, but filtered system noise (svchost, etc) is NOT.
            for app_name in running_user_apps:
                self.usage_today[app_name] += elapsed
                self.usage_pending[app_name] += elapsed
        elif self.active_apps:
            # If no user apps detected, we don't count time.
            pass
        
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
            self.usage_pending = {}
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
        """Return list of currently active trackable processes."""
        with self.lock:
            return sorted(list(self.active_apps))
