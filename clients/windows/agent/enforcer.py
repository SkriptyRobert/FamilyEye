"""Rule enforcement."""
import os
import subprocess
import time
from datetime import datetime
from typing import List, Dict, Set, Optional
from .config import config
from .network_control import NetworkController
from .logger import get_logger
from .notifications import NotificationManager, ShutdownManager


class RuleEnforcer:
    """Enforce rules on device."""
    
    def __init__(self):
        self.rules: List[Dict] = []
        self.blocked_apps: Set[str] = set()
        self.daily_limits: Dict[str, int] = {}  # app_name -> seconds
        self.usage_by_app: Dict[str, int] = {}  # app_name -> total seconds today (from backend)
        self.blocked_websites: Set[str] = set()
        self.monitor = None
        self.network_controller = NetworkController()
        self.notification_manager = NotificationManager()
        self.shutdown_manager = ShutdownManager()
        self.last_vpn_check = 0
        self.vpn_check_interval = 60  # Check every 60 seconds
        self.logger = get_logger('ENFORCER')
        self.is_locked = False
        self.is_network_blocked = False
        self.lock_whitelist = {
            'explorer', 'taskmgr', 'py', 'python', 'cmd', 'powershell',
            'system', 'svchost', 'winlogon', 'csrss', 'lsass', 'services',
            'git', 'ssh', 'conhost', 'runtimebroker', 'shellexperiencehost',
            'searchhost', 'startmenuexperiencehost'
        }
        self.current_pid = os.getpid()
        self._last_fetch_rules_time = 0
        
        self.device_daily_limit: Optional[int] = None  # seconds
        self.device_today_usage: int = 0  # seconds from backend
        self._daily_limit_warning_shown = False
        self._daily_limit_shutdown_initiated = False
        
        # Time Synchronization (Monotonic)
        self.clock_offset: float = 0.0
        self.ref_monotonic: float = 0.0
        self.ref_server_ts: float = 0.0
        self.is_time_synced: bool = False
        self.last_time_sync = 0
        self._needs_immediate_fetch = False
        
        # Register for reconnection events
        from .api_client import api_client
        api_client.add_on_reconnect_callback(self.trigger_immediate_fetch)

        
        # Track apps that already exceeded limit (to avoid repeated notifications)
        self._apps_limit_exceeded_notified: Set[str] = set()
        self._apps_limit_warning_notified: Set[str] = set()
        self._last_limit_reset_date = None
        
        # Schedule tracking
        self.device_schedules: List[Dict] = []
        self.app_schedules: Dict[str, List[Dict]] = {} # app_name -> list of schedules
        self._schedule_warning_shown = False
        self._schedule_shutdown_initiated = False
    
    def set_monitor(self, monitor):
        """Set monitor instance."""
        self.monitor = monitor
        # Try to load cached rules on startup
        self._load_rules_cache()

    def set_reporter(self, reporter):
        """Set reporter instance for sync-on-fetch."""
        self.reporter = reporter
        
    def _get_cache_path(self):
        """Get path for rules cache file."""
        import sys
        if getattr(sys, 'frozen', False):
            # Use ProgramData for cache
            program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
            base_dir = os.path.join(program_data, 'FamilyEye', 'Agent')
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, 'rules_cache.json')
        else:
            return os.path.join(os.path.dirname(__file__), 'rules_cache.json')
        
    def _save_rules_cache(self):
        """Save current rules to local cache."""
        try:
            import json
            cache_data = {
                "timestamp": self.get_trusted_utc_datetime().timestamp(),
                "rules": self.rules,
                "usage_by_app": self.usage_by_app,
                "daily_usage": self.device_today_usage
            }
            with open(self._get_cache_path(), 'w') as f:
                json.dump(cache_data, f)
            self.logger.debug("Rules cached locally")
        except Exception as e:
            self.logger.error(f"Failed to cache rules: {e}")
            
    def _load_rules_cache(self):
        """Load rules from local cache."""
        try:
            import json
            cache_path = self._get_cache_path()
            if not os.path.exists(cache_path):
                return
                
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # Check cache age (optional, maybe warn if too old)
            cache_ts = cache_data.get("timestamp", 0)
            cache_age = time.time() - cache_ts
            
            self.rules = cache_data.get("rules", [])
            self.usage_by_app = cache_data.get("usage_by_app", {})
            self.device_today_usage = cache_data.get("daily_usage", 0)
            
            self._update_blocked_apps()
            self.logger.info(f"Loaded {len(self.rules)} rules from local cache (age: {int(cache_age/60)}m)")
        except Exception as e:
            self.logger.warning(f"Failed to load cached rules: {e}")

    def trigger_immediate_fetch(self):
        """Callback for reconnection - trigger immediate rule fetch."""
        self.logger.info("Reconnection detected - triggering immediate rule fetch")
        self._needs_immediate_fetch = True

    def _fetch_rules(self):
        """Fetch rules from backend using API Client."""
        try:
            from .api_client import api_client
            
            # Skip if we don't have basic config (api_client handles details, but good to check)
            if not config.is_configured():
                return

            # SYNC-ON-FETCH: Send latest usage data BEFORE asking for rules
            # This ensures backend has up-to-date counters for daily limits
            if getattr(self, 'reporter', None):
                try:
                    # self.logger.debug("Syncing usage before rule fetch...")
                    self.reporter.send_reports()
                except Exception as e:
                    self.logger.warning(f"Failed to sync usage before fetch: {e}")

            rules_data = api_client.fetch_rules()
            
            if rules_data:
                # Handle both direct list and wrapped response
                if isinstance(rules_data, list):
                    self.rules = rules_data
                elif isinstance(rules_data, dict) and "rules" in rules_data:
                    self.rules = rules_data["rules"]
                    # Store backend-reported usage
                    self.usage_by_app = rules_data.get("usage_by_app", {})
                    # Store device daily usage for daily limit enforcement
                    self.device_today_usage = rules_data.get("daily_usage", 0)
                    
                    # SERVER TIME SYNC
                    server_time_str = rules_data.get("server_time")
                    if server_time_str:
                        try:
                            # Parse server time (UTC)
                            from datetime import datetime
                            # Handle ISO format with potential Z
                            if server_time_str.endswith('Z'):
                                server_time_str = server_time_str[:-1] + '+00:00'
                            
                            server_dt = datetime.fromisoformat(server_time_str)
                            server_ts = server_dt.timestamp()
                            local_ts = time.time()
                            
                            # Calculate offset: Offset = Server - Local
                            # True Time = Local + Offset
                            new_offset = server_ts - local_ts
                            
                            # Monotonic Sync (Primary Source of Truth)
                            self.ref_server_ts = server_ts
                            self.ref_monotonic = time.monotonic()
                            self.is_time_synced = True
                            
                            self.logger.info(f"Time synced. Server: {server_dt}, Monotonic Ref: {self.ref_monotonic}")
                        except Exception as e:
                            self.logger.warning(f"Failed to sync time from rules: {e}")

                    self.logger.debug(f"Received usage stats: {len(self.usage_by_app)} apps, {self.device_today_usage}s total today")
                else:
                    self.rules = []
                
                self._update_blocked_apps()
                self._save_rules_cache()
                self.logger.debug(f"Rules updated: {len(self.rules)} rules")
            else:
                # Fetch failed (network or auth). API Client handles logging.
                # Fallback to cache for resilience (unless 401, which kills agent anyway)
                self.logger.info("Falling back to local cache")
                self._load_rules_cache()

        except Exception as e:
            self.logger.error(f"Error in rule fetch cycle: {e}")
            self._load_rules_cache()

    
    
    def get_trusted_datetime(self) -> datetime:
        """Get trusted local datetime distinct from system clock if possible."""
        # Validate sync age
        SYNC_MAX_AGE = 3600  # 1 hour
        if self.is_time_synced and (time.monotonic() - self.ref_monotonic > SYNC_MAX_AGE):
            self.logger.warning("Time sync expired (older than 1h), reverting to system time")
            self.is_time_synced = False

        if self.is_time_synced:
            # Calculate elapsed since sync
            elapsed = time.monotonic() - self.ref_monotonic
            current_server_ts = self.ref_server_ts + elapsed
            
            # Convert to local time (Server UTC TS -> Local DT)
            return datetime.fromtimestamp(current_server_ts)
        else:
            return datetime.now()

    def get_trusted_utc_datetime(self) -> datetime:
        """Get trusted UTC datetime."""
        # Re-check sync age (or rely on method above if called sequentially, but safer to check)
        SYNC_MAX_AGE = 3600
        if self.is_time_synced and (time.monotonic() - self.ref_monotonic > SYNC_MAX_AGE):
             self.is_time_synced = False
             
        if self.is_time_synced:
            elapsed = time.monotonic() - self.ref_monotonic
            current_server_ts = self.ref_server_ts + elapsed
            return datetime.utcfromtimestamp(current_server_ts)
        else:
            return datetime.utcnow()
            
    def _update_blocked_apps(self):
        """Update blocked apps list from rules and sync network blocking."""
        self.blocked_apps.clear()
        self.daily_limits.clear()
        self.device_schedules.clear()
        self.app_schedules.clear()
        
        # Keep track of what we want to block now
        new_blocked_websites = set()
        self.is_locked = False
        self.is_network_blocked = False
        self.device_daily_limit = None
        
        # Use Trusted Time for Rule Evaluation
        now = self.get_trusted_datetime()
        now_str = now.strftime("%H:%M")
        
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            rule_type = rule.get("rule_type", "")
            app_name = rule.get("app_name", "").lower() if rule.get("app_name") else None
            website_url = rule.get("website_url", "").lower() if rule.get("website_url") else None
            
            if rule_type == "app_block":
                if app_name:
                    # Support comma-separated apps (e.g., "chrome,discord,steam")
                    app_names = [a.strip().lower() for a in app_name.split(',') if a.strip()]
                    for name in app_names:
                        if name.endswith('.exe'): name = name[:-4]
                        self.blocked_apps.add(name)
            elif rule_type == "time_limit":
                if app_name and rule.get("time_limit"):
                    # Support comma-separated apps
                    app_names = [a.strip().lower() for a in app_name.split(',') if a.strip()]
                    limit_seconds = rule.get("time_limit", 0) * 60
                    for name in app_names:
                        if name.endswith('.exe'): name = name[:-4]
                        self.daily_limits[name] = limit_seconds
            elif rule_type == "daily_limit":
                # Daily device limit - total usage for the whole device
                limit_minutes = rule.get("time_limit", 0)
                if limit_minutes > 0:
                    self.device_daily_limit = limit_minutes * 60  # Convert to seconds
                    self.logger.info(f"Daily device limit set: {limit_minutes} minutes")
            elif rule_type == "schedule":
                # Schedule rule - allowed time windows
                base_schedule_info = {
                    "start_time": rule.get("schedule_start_time"),
                    "end_time": rule.get("schedule_end_time"),
                    "days": rule.get("schedule_days"),  # e.g., "0,1,2,3,4" or None for all days
                }
                if base_schedule_info["start_time"] and base_schedule_info["end_time"]:
                    if not app_name:
                        # Device-wide schedule
                        schedule_info = {**base_schedule_info, "app_name": None}
                        self.device_schedules.append(schedule_info)
                        self.logger.info(f"Device Schedule: {schedule_info['start_time']} - {schedule_info['end_time']}")
                    else:
                        # App-specific schedule - support comma-separated apps
                        app_names = [a.strip().lower() for a in app_name.split(',') if a.strip()]
                        for name in app_names:
                            if name.endswith('.exe'): name = name[:-4]
                            if name not in self.app_schedules:
                                self.app_schedules[name] = []
                            schedule_info = {**base_schedule_info, "app_name": name}
                            self.app_schedules[name].append(schedule_info)
                            self.logger.info(f"App Schedule ({name}): {schedule_info['start_time']} - {schedule_info['end_time']}")
            elif rule_type == "lock_device":
                self.is_locked = True
            elif rule_type == "network_block":
                start = rule.get("schedule_start_time")
                end = rule.get("schedule_end_time")
                if start and end:
                    # FIX: Use minute-based comparison instead of string comparison
                    try:
                        start_parts = start.split(":")
                        end_parts = end.split(":")
                        now_parts = now_str.split(":")
                        
                        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1] if len(start_parts) > 1 else 0)
                        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1] if len(end_parts) > 1 else 0)
                        now_minutes = int(now_parts[0]) * 60 + int(now_parts[1] if len(now_parts) > 1 else 0)
                        
                        if start_minutes <= now_minutes <= end_minutes:
                            self.is_network_blocked = True
                            self.logger.debug(f"Network block active: {start} <= {now_str} <= {end}")
                    except (ValueError, IndexError):
                        pass
                else:
                    self.is_network_blocked = True
            elif rule_type in ("website_block", "web_block"):
                if website_url:
                    pattern = website_url.strip().lower()
                    if '*' in pattern or '.' not in pattern:
                        keyword = pattern.replace('*', '').strip()
                        if keyword:
                            common_domains = [f"{keyword}.com", f"www.{keyword}.com", f"{keyword}.net", f"{keyword}.org", f"m.{keyword}.com"]
                            for domain in common_domains:
                                new_blocked_websites.add(domain)
                    else:
                        domain = self._extract_domain(pattern)
                        if domain:
                            new_blocked_websites.add(domain)
                            if not domain.startswith("www."):
                                new_blocked_websites.add(f"www.{domain}")

        # SYNC WEBSITES:
        # 1. Find websites that are currently blocked but NOT in the new list
        websites_to_unblock = self.blocked_websites - new_blocked_websites
        for domain in websites_to_unblock:
            self.network_controller.unblock_website(domain)
            self.logger.info("Unblocking website (rule removed)", domain=domain)
            
        # 2. Find websites that are in the new list but NOT currently blocked
        websites_to_block = new_blocked_websites - self.blocked_websites
        for domain in websites_to_block:
            self.network_controller.block_website(domain)
            self.logger.info("Blocking website (new rule)", domain=domain)
            
        # 3. Update the state
        self.blocked_websites = new_blocked_websites
        
        # 4. LOG SUMMARY of loaded rules for debugging
        self.logger.info(f"Rules loaded: {len(self.rules)} total, "
                        f"blocked_apps={len(self.blocked_apps)}, "
                        f"daily_limits={len(self.daily_limits)}, "
                        f"device_schedules={len(self.device_schedules)}, "
                        f"app_schedules={list(self.app_schedules.keys())}")
    
    def _kill_app(self, app_name: str, reason: str = "blocked", used_seconds: int = 0, limit_seconds: int = 0):
        """Kill application by name - kills ALL processes matching the name pattern."""
        try:
            import psutil
            app_lower = app_name.lower().replace('.exe', '')
            killed_count = 0
            
            # Kill all processes that match the app name (main + helpers)
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name'].lower().replace('.exe', '')
                    # Match exact name or if app_name is contained in process name
                    # e.g., "steam" matches "steam", "steamwebhelper", "steamservice"
                    if proc_name == app_lower or app_lower in proc_name or proc_name.startswith(app_lower):
                        proc.kill()
                        killed_count += 1
                        self.logger.info(f"Killed process: {proc.info['name']} (PID {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if killed_count > 0:
                self.logger.warning(f"Enforced limit: Killed {killed_count} processes for {app_name}")
                
                # NEW: Log kill to monitor for backend reporting
                if self.monitor:
                    self.monitor.log_process_kill(app_name, reason, used_seconds, limit_seconds)
            else:
                # Fallback to taskkill if psutil didn't find anything
                subprocess.run(
                    ["taskkill", "/F", "/IM", f"{app_name}.exe"],
                    capture_output=True,
                    timeout=5
                )
                # Also try with helper patterns
                for suffix in ['helper', 'webhelper', 'service', 'launcher']:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", f"{app_name}{suffix}.exe"],
                        capture_output=True,
                        timeout=5
                    )
                self.logger.info(f"Enforced block via taskkill: {app_name}")
                
                # Still log the kill attempt via taskkill
                if self.monitor:
                    self.monitor.log_process_kill(app_name, reason, used_seconds, limit_seconds)
        except Exception as e:
            self.logger.error(f"Error killing {app_name}: {e}")
    
    def _report_critical_event(self, event_type: str, app_name: str = None, 
                                used_seconds: int = None, limit_seconds: int = None,
                                message: str = None):
        """
        Report critical event to backend immediately using centralized API client.
        """
        try:
            from .api_client import api_client
            from datetime import datetime, timezone
            
            payload = {
                "event_type": event_type,
                "app_name": app_name,
                "used_seconds": used_seconds,
                "limit_seconds": limit_seconds,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Use centralized client handles retry and error logging
            api_client.report_critical_event(payload)
                
        except Exception as e:
            # Don't let reporting failures affect enforcement
            self.logger.debug(f"Critical event report error (non-blocking): {e}")

    def _enforce_blocked_apps(self):
        """Enforce blocked apps using robust identification."""
        if not self.monitor:
            return
        
        # 1. Handle Device Lock (unchanged)
        if self.is_locked:
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            except Exception:
                pass
                
            try:
                import ctypes
                WTS_CURRENT_SERVER_HANDLE = 0
                WTSActive = 0
                session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
                if session_id != 0xFFFFFFFF:
                    ctypes.windll.wtsapi32.WTSDisconnectSession(WTS_CURRENT_SERVER_HANDLE, session_id, False)
                    self.logger.warning("Enforced Lock: Disconnected active console session")
            except Exception as e:
                self.logger.error("Failed to disconnect session", error=str(e))
            return

        # 2. Handle Individual App Blocks (Robust)
        # Using detections dictionary from monitor which contains metadata/titles
        detections = getattr(self.monitor, 'current_detections', {})
        
        for app_name, info in detections.items():
            pid = info.get('pid')
            orig_name = info.get('original_name', '').lower()
            title = info.get('title', '').lower()
            clean_name = app_name.lower()
            
            # Check if this process matches any blocked rule (by name, metadata or title)
            is_blocked = False
            matching_rule = None
            
            for blocked in self.blocked_apps:
                blocked_low = blocked.lower()
                
                # A. Match by exe name
                if blocked_low == clean_name or (len(blocked_low) >= 3 and blocked_low in clean_name):
                    is_blocked = True
                # B. Match by original filename (PE metadata)
                elif orig_name and (blocked_low == orig_name or (len(blocked_low) >= 3 and blocked_low in orig_name)):
                    is_blocked = True
                # C. Match by window title
                elif title and (blocked_low in title):
                    is_blocked = True
                    
                if is_blocked:
                    matching_rule = blocked
                    break
            
            if is_blocked:
                self.logger.warning(f"BLOCKED APP DETECTED: {app_name} (Matches rule: {matching_rule})")
                self.logger.info(f"  Details: OrigName={orig_name}, Title='{title}', PID={pid}")
                self._kill_app(app_name, reason="app_blocked")
                continue

            # NEW: Check app-specific schedules
            # If there are schedules for this app, user MUST be in one of them to run it
            if clean_name in self.app_schedules or orig_name in self.app_schedules:
                target_key = clean_name if clean_name in self.app_schedules else orig_name
                app_schedules_list = self.app_schedules[target_key]
                
                # Use Trusted Time
                now = self.get_trusted_datetime()
                current_time_str = now.strftime("%H:%M")
                
                # Robust Day Check (Locale-independent)
                days_map = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                current_day = days_map[now.weekday()]
                
                is_allowed_now = False
                matched_schedule = None
                
                for sch in app_schedules_list:
                    # Check day first
                    if sch.get("days"):
                        days_list = self._parse_schedule_days(sch.get("days"))
                        if current_day not in days_list:
                            continue
                    
                    # FIX: Use datetime comparison instead of string comparison
                    try:
                        start_time = sch.get("start_time", "00:00")
                        end_time = sch.get("end_time", "23:59")
                        
                        # Parse times to minutes for accurate comparison
                        start_parts = start_time.split(":")
                        end_parts = end_time.split(":")
                        current_parts = current_time_str.split(":")
                        
                        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1] if len(start_parts) > 1 else 0)
                        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1] if len(end_parts) > 1 else 0)
                        current_minutes = int(current_parts[0]) * 60 + int(current_parts[1] if len(current_parts) > 1 else 0)
                        
                        # Check if current time is within schedule
                        if start_minutes <= current_minutes <= end_minutes:
                            is_allowed_now = True
                            matched_schedule = sch
                            break
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Schedule parse error for {app_name}: {e}")
                        continue
                
                # DEBUG: Log schedule check result
                self.logger.debug(f"Schedule check: {app_name}, Day:{current_day}, Time:{current_time_str}, "
                                f"Schedules:{len(app_schedules_list)}, Allowed:{is_allowed_now}")
                
                if not is_allowed_now:
                    self.logger.info(f"Schedule BLOCKED: {app_name}. Day:{current_day}, Time:{current_time_str}. "
                                   f"Rules: {app_schedules_list}")
                    self.logger.warning(f"APP OUTSIDE SCHEDULE: {app_name} (Killing)")
                    self._kill_app(app_name, reason="outside_app_schedule")
                else:
                    self.logger.debug(f"Schedule ALLOWED: {app_name} matched {matched_schedule}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        import re
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        # Remove path
        url = url.split('/')[0]
        # Remove port
        url = url.split(':')[0]
        return url.lower().strip()
    
    def _parse_schedule_days(self, days_raw: str) -> list:
        """Parse schedule days - supports both numeric ('0,1,2') and text ('mon,tue,wed') formats."""
        days_map = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        days_list = []
        for d in days_raw.split(","):
            d = d.strip()
            if d.isdigit():
                # Numeric format: 0=mon, 1=tue, etc.
                idx = int(d)
                if 0 <= idx <= 6:
                    days_list.append(days_map[idx])
            else:
                # Text format: 'mon', 'tue', 'monday', etc.
                days_list.append(d.lower()[:3])
        return days_list
    
    def _enforce_time_limits(self):
        """Enforce time limits - check total daily usage from backend."""
        if not self.monitor:
            return
        
        # Reset notification tracking daily
        today = self.get_trusted_datetime().date()
        if self._last_limit_reset_date != today:
            self._apps_limit_exceeded_notified.clear()
            self._apps_limit_warning_notified.clear()
            self._last_limit_reset_date = today
            self.logger.info("Daily limit notification tracking reset")
        
        # Get current session usage from monitor
        session_usage = self.monitor.get_usage_stats()
        detections = getattr(self.monitor, 'current_detections', {})
        
        # For time limits, check total daily usage
        for rule_name, limit_seconds in self.daily_limits.items():
            rule_low = rule_name.lower()
            
            # Find ALL processes that match this rule (exe name, metadata, or title)
            matched_apps = []
            for app_name, info in detections.items():
                app_low = app_name.lower()
                orig_low = info.get('original_name', '').lower()
                title_low = info.get('title', '').lower()
                
                if rule_low == app_low or (len(rule_low) >= 3 and rule_low in app_low):
                    matched_apps.append(app_name)
                elif orig_low and (rule_low == orig_low or (len(rule_low) >= 3 and rule_low in orig_low)):
                    matched_apps.append(app_name)
                elif title_low and (rule_low in title_low):
                    matched_apps.append(app_name)
            
            if not matched_apps: continue
            
            # Get backend-reported usage for this rule's app
            backend_seconds = 0
            for app_key in self.usage_by_app:
                if app_key.lower() == rule_low or (len(rule_low) >= 3 and rule_low in app_key.lower()):
                    backend_seconds = max(backend_seconds, self.usage_by_app[app_key])
            
            # NEW LOGIC: Use max(backend_seconds, local_usage_today)
            # This ensures we don't double-count when rules are fetched after a report
            local_seconds = 0
            for m_app in matched_apps:
                local_seconds = max(local_seconds, session_usage.get(m_app, 0))
            
            # Use whichever is higher: backend total or local session
            total_seconds = max(backend_seconds, int(local_seconds))
            
            remaining_seconds = limit_seconds - total_seconds
            remaining_minutes = max(0, int(remaining_seconds / 60))
            
            if total_seconds >= limit_seconds:
                # Limit exceeded - kill all matched apps
                self.logger.warning(f"TIME LIMIT EXCEEDED: {rule_name} (Matches: {matched_apps}) used {int(total_seconds/60)}m / {int(limit_seconds/60)}m")
                for m_app in matched_apps:
                    self._kill_app(m_app, reason="time_limit_exceeded", used_seconds=int(total_seconds), limit_seconds=int(limit_seconds))
                
                if rule_low not in self._apps_limit_exceeded_notified:
                    self.notification_manager.show_limit_exceeded(rule_name)
                    self._apps_limit_exceeded_notified.add(rule_low)
                    self._report_critical_event('limit_exceeded', rule_name, int(total_seconds), int(limit_seconds))
                    
            elif total_seconds >= limit_seconds * 0.7:
                if rule_low not in self._apps_limit_warning_notified:
                    self.notification_manager.show_limit_warning(rule_name, remaining_minutes)
                    self._apps_limit_warning_notified.add(rule_low)
    
    def _enforce_vpn_detection(self):
        """Detect and handle VPN/proxy usage."""
        current_time = time.monotonic()
        if current_time - self.last_vpn_check < self.vpn_check_interval:
            return
        
        self.last_vpn_check = current_time
        
        # Check for VPN
        if self.network_controller.detect_vpn():
            self.logger.warning("VPN detected - network access may be restricted")
            # Could implement network blocking here
            # For now, just log
        
        # Check for proxy
        if self.network_controller.detect_proxy():
            self.logger.warning("Proxy detected - network access may be restricted")
            # Could implement network blocking here
            # For now, just log
    
    def _enforce_network_block(self):
        """Enforce network block if active."""
        if self.is_network_blocked:
            if not getattr(self, '_network_currently_blocked', False):
                self.logger.warning("Internet access paused - blocking all outbound traffic")
                from .config import config
                
                # Use network controller's new logic to handle backend whitelist
                backend_url = config.get("backend_url", "")
                
                # Basic LAN whitelist
                whitelist = ["127.0.0.1", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
                
                self.logger.info(f"Blocking network (allowed: LAN + Backend: {backend_url})")
                
                # Pass backend_url for robust resolution and whitelisting
                result = self.network_controller.block_all_outbound(whitelist, backend_url=backend_url)
                
                if result:
                    self._network_currently_blocked = True
                    self.logger.success("Network block applied successfully")
                else:
                    self.logger.error("Failed to apply network block - will retry")
        else:
            if getattr(self, '_network_currently_blocked', False):
                self.logger.info("Internet access resumed - removing block")
                if self.network_controller.unblock_all_outbound():
                    self._network_currently_blocked = False
                    self.logger.success("Network block removed successfully")
    
    def _enforce_daily_limit(self):
        """Enforce daily device limit - total usage for the whole device."""
        if self.device_daily_limit is None:
            # No daily limit set, reset flags
            self._daily_limit_warning_shown = False
            self._daily_limit_shutdown_initiated = False
            return
        
        # Get total device usage today: max(backend_total, local_wall_clock)
        # Using the new absolute wall-clock metric from monitor
        local_total = self.monitor.get_device_usage() if self.monitor else 0
        total_usage = max(self.device_today_usage, int(local_total))
        
        remaining_seconds = self.device_daily_limit - total_usage
        remaining_minutes = max(0, int(remaining_seconds / 60))
        percentage_used = (total_usage / self.device_daily_limit * 100) if self.device_daily_limit > 0 else 0
        
        self.logger.debug(f"Daily limit check: {total_usage}s / {self.device_daily_limit}s ({percentage_used:.1f}%)")
        
        if total_usage >= self.device_daily_limit:
            # Daily limit exceeded - notify, lock and shutdown
            if not self._daily_limit_shutdown_initiated:
                self.logger.critical("DAILY DEVICE LIMIT EXCEEDED - Initiating shutdown sequence")
                self._daily_limit_shutdown_initiated = True
                
                # Show popup with countdown
                countdown = 60  # 60 seconds to save work
                self.notification_manager.show_daily_limit_exceeded(countdown)
                
                # Lock and schedule shutdown
                self.shutdown_manager.lock_and_shutdown(countdown)
                
        elif percentage_used >= 80:
            # Warning threshold (80% used) - show warning every 5 minutes
            
            # Reset warning flag if 5 minutes have passed
            last_shown = getattr(self, '_daily_limit_warning_shown_at', 0)
            if self._daily_limit_warning_shown and (time.time() - last_shown > 300):
                self._daily_limit_warning_shown = False
            
            if not self._daily_limit_warning_shown:
                self.logger.warning(f"Approaching daily device limit: {remaining_minutes} minutes remaining")
                self.notification_manager.show_daily_limit_warning(remaining_minutes)
                self._daily_limit_warning_shown = True
                self._daily_limit_warning_shown_at = time.time()
    
    def _enforce_schedule(self):
        """Enforce schedule rules - allowed time windows for the WHOLE DEVICE."""
        if not self.device_schedules:
            # No device schedule rules, reset flags
            self._schedule_warning_shown = False
            self._schedule_shutdown_initiated = False
            self.shutdown_manager.reset_shutdown_flag()
            return
        
        # Use Trusted Time
        now = self.get_trusted_datetime()
        current_time_str = now.strftime("%H:%M")
        current_day = now.strftime("%a").lower()[:3]
        
        # Check if we're within ANY allowed device schedule
        is_within_schedule = False
        minutes_until_end = None
        
        for schedule in self.device_schedules:
            start_time = schedule.get("start_time")
            end_time = schedule.get("end_time")
            allowed_days = schedule.get("days")
            
            # Check if today is an allowed day
            if allowed_days:
                allowed_days_list = self._parse_schedule_days(allowed_days)
                if current_day not in allowed_days_list:
                    continue  # Today is not in the allowed days
            
            # Check if current time is within the schedule
            if start_time and end_time:
                # FIX: Use minute-based comparison instead of string comparison
                try:
                    start_parts = start_time.split(":")
                    end_parts = end_time.split(":")
                    
                    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1] if len(start_parts) > 1 else 0)
                    end_minutes = int(end_parts[0]) * 60 + int(end_parts[1] if len(end_parts) > 1 else 0)
                    current_minutes = now.hour * 60 + now.minute
                    
                    if start_minutes <= current_minutes <= end_minutes:
                        is_within_schedule = True
                        minutes_until_end = end_minutes - current_minutes
                        break  # We found an active schedule
                except (ValueError, IndexError):
                    pass
        
        if is_within_schedule:
            # We're within allowed time
            self._schedule_shutdown_initiated = False
            self.shutdown_manager.reset_shutdown_flag()
            
            # Show warning if approaching end
            if minutes_until_end is not None and minutes_until_end <= 10:
                if not self._schedule_warning_shown:
                    self.logger.warning(f"Schedule ending soon: {minutes_until_end} minutes remaining")
                    self.notification_manager.show_schedule_warning(minutes_until_end)
                    self._schedule_warning_shown = True
            else:
                self._schedule_warning_shown = False
        else:
            # We're OUTSIDE allowed time - enforce block
            if not self._schedule_shutdown_initiated:
                self.logger.critical("OUTSIDE ALLOWED SCHEDULE - Initiating shutdown sequence")
                self._schedule_shutdown_initiated = True
                
                # Show popup
                countdown = 60  # 60 seconds
                self.notification_manager.show_outside_schedule()
                
                # Lock and schedule shutdown
                self.shutdown_manager.lock_and_shutdown(countdown)

    def update(self):
        """Update enforcement."""
        # Fetch rules periodically (every 30 seconds)
        current_time = time.monotonic()
        from .config import config
        polling_interval = config.get("polling_interval", 10)
            
        if current_time - self._last_fetch_rules_time >= polling_interval or self._needs_immediate_fetch:
            if self._needs_immediate_fetch:
                self.logger.info("Immediate rule fetch triggered (reconnection)")
                self._needs_immediate_fetch = False
                
            self._fetch_rules()
            self._last_fetch_rules_time = current_time
        
        # Enforce rules
        self._enforce_blocked_apps()
        self._enforce_time_limits()
        self._enforce_daily_limit()
        self._enforce_schedule()
        self._enforce_vpn_detection()
        self._enforce_network_block()

