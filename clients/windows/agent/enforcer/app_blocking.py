"""App blocking enforcement logic."""
import subprocess
from typing import Dict, Set, Any, Optional
from ..logger import get_logger


class AppBlockingEnforcer:
    """Handles blocked app detection and termination."""
    
    def __init__(self, logger=None):
        self.logger = logger or get_logger('ENFORCER.APPS')
        
    def kill_app(self, app_name: str, reason: str = "blocked", 
                 used_seconds: int = 0, limit_seconds: int = 0,
                 monitor: Any = None) -> int:
        """Kill application by name - kills ALL processes matching the name pattern.
        
        Args:
            app_name: Name of the app to kill
            reason: Reason for killing (for logging)
            used_seconds: Usage time before kill
            limit_seconds: Time limit that was exceeded
            monitor: Optional monitor instance for logging kills
            
        Returns:
            Number of processes killed
        """
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
                
                # Log kill to monitor for backend reporting
                if monitor:
                    monitor.log_process_kill(app_name, reason, used_seconds, limit_seconds)
            else:
                # Fallback to taskkill if psutil didn't find anything
                self._taskkill_fallback(app_name)
                    
                # Still log the kill attempt via taskkill
                if monitor:
                    monitor.log_process_kill(app_name, reason, used_seconds, limit_seconds)
                    
            return killed_count
        except Exception as e:
            self.logger.error(f"Error killing {app_name}: {e}")
            return 0
            
    def _taskkill_fallback(self, app_name: str) -> None:
        """Use Windows taskkill as fallback."""
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
            
    def enforce_blocked_apps(self, blocked_apps: Set[str], 
                             app_schedules: Dict[str, list],
                             detections: Dict[str, Dict],
                             is_locked: bool,
                             get_trusted_datetime,
                             parse_schedule_days,
                             monitor: Any = None) -> None:
        """Enforce blocked apps using robust identification.
        
        Args:
            blocked_apps: Set of blocked app names
            app_schedules: Dict of app name to list of schedule dicts
            detections: Current app detections from monitor
            is_locked: Whether device is locked
            get_trusted_datetime: Callable for trusted time
            parse_schedule_days: Callable to parse schedule days
            monitor: Optional monitor instance
        """
        # 1. Handle Device Lock
        if is_locked:
            self._handle_device_lock()
            return

        # 2. Handle Individual App Blocks (Robust)
        for app_name, info in detections.items():
            pid = info.get('pid')
            orig_name = info.get('original_name', '').lower()
            title = info.get('title', '').lower()
            clean_name = app_name.lower()
            
            # Check if this process matches any blocked rule
            is_blocked, matching_rule = self._check_if_blocked(
                clean_name, orig_name, title, blocked_apps
            )
            
            if is_blocked:
                self.logger.warning(f"BLOCKED APP DETECTED: {app_name} (Matches rule: {matching_rule})")
                self.logger.info(f"  Details: OrigName={orig_name}, Title='{title}', PID={pid}")
                self.kill_app(app_name, reason="app_blocked", monitor=monitor)
                continue

            # Check app-specific schedules
            if clean_name in app_schedules or orig_name in app_schedules:
                self._enforce_app_schedule(
                    app_name, clean_name, orig_name,
                    app_schedules, get_trusted_datetime, parse_schedule_days, monitor
                )
                
    def _handle_device_lock(self) -> None:
        """Handle device lock via Windows API."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        except Exception:
            pass
            
        try:
            import ctypes
            WTS_CURRENT_SERVER_HANDLE = 0
            session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
            if session_id != 0xFFFFFFFF:
                ctypes.windll.wtsapi32.WTSDisconnectSession(WTS_CURRENT_SERVER_HANDLE, session_id, False)
                self.logger.warning("Enforced Lock: Disconnected active console session")
        except Exception as e:
            self.logger.error("Failed to disconnect session", error=str(e))
                
    def _check_if_blocked(self, clean_name: str, orig_name: str, title: str,
                          blocked_apps: Set[str]) -> tuple:
        """Check if app matches any blocked rule.
        
        Returns:
            Tuple of (is_blocked: bool, matching_rule: str or None)
        """
        for blocked in blocked_apps:
            blocked_low = blocked.lower()
            
            # A. Match by exe name
            if blocked_low == clean_name or (len(blocked_low) >= 3 and blocked_low in clean_name):
                return True, blocked
            # B. Match by original filename (PE metadata)
            if orig_name and (blocked_low == orig_name or (len(blocked_low) >= 3 and blocked_low in orig_name)):
                return True, blocked
            # C. Match by window title
            if title and (blocked_low in title):
                return True, blocked
                
        return False, None
        
    def _enforce_app_schedule(self, app_name: str, clean_name: str, orig_name: str,
                              app_schedules: Dict[str, list],
                              get_trusted_datetime, parse_schedule_days,
                              monitor: Any = None) -> None:
        """Check and enforce app-specific schedule."""
        target_key = clean_name if clean_name in app_schedules else orig_name
        app_schedules_list = app_schedules[target_key]
        
        now = get_trusted_datetime()
        current_time_str = now.strftime("%H:%M")
        
        # Robust Day Check (Locale-independent)
        days_map = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        current_day = days_map[now.weekday()]
        
        is_allowed_now = False
        matched_schedule = None
        
        for sch in app_schedules_list:
            # Check day first
            if sch.get("days"):
                days_list = parse_schedule_days(sch.get("days"))
                if current_day not in days_list:
                    continue
            
            # Use minute-based comparison
            try:
                start_time = sch.get("start_time", "00:00")
                end_time = sch.get("end_time", "23:59")
                
                start_parts = start_time.split(":")
                end_parts = end_time.split(":")
                current_parts = current_time_str.split(":")
                
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1] if len(start_parts) > 1 else 0)
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1] if len(end_parts) > 1 else 0)
                current_minutes = int(current_parts[0]) * 60 + int(current_parts[1] if len(current_parts) > 1 else 0)
                
                if start_minutes <= current_minutes <= end_minutes:
                    is_allowed_now = True
                    matched_schedule = sch
                    break
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Schedule parse error for {app_name}: {e}")
                continue
        
        self.logger.debug(f"Schedule check: {app_name}, Day:{current_day}, Time:{current_time_str}, "
                         f"Schedules:{len(app_schedules_list)}, Allowed:{is_allowed_now}")
        
        if not is_allowed_now:
            self.logger.info(f"Schedule BLOCKED: {app_name}. Day:{current_day}, Time:{current_time_str}.")
            self.logger.warning(f"APP OUTSIDE SCHEDULE: {app_name} (Killing)")
            self.kill_app(app_name, reason="outside_app_schedule", monitor=monitor)
        else:
            self.logger.debug(f"Schedule ALLOWED: {app_name} matched {matched_schedule}")
