"""Time limit enforcement logic."""
import time
from typing import Dict, Set, Any, Optional
from datetime import date
from ..logger import get_logger


class TimeLimitEnforcer:
    """Handles daily time limit enforcement for apps and device."""
    
    def __init__(self, notification_manager, shutdown_manager, logger=None):
        self.logger = logger or get_logger('ENFORCER.LIMITS')
        self.notification_manager = notification_manager
        self.shutdown_manager = shutdown_manager
        
        # Track apps that already exceeded limit
        self._apps_limit_exceeded_notified: Set[str] = set()
        self._apps_limit_warning_notified: Set[str] = set()
        self._last_limit_reset_date: Optional[date] = None
        
        # Daily device limit tracking
        self._daily_limit_warning_shown = False
        self._daily_limit_shutdown_initiated = False
        self._daily_limit_warning_shown_at = 0
        
    def enforce_app_time_limits(self, daily_limits: Dict[str, int],
                                 usage_by_app: Dict[str, int],
                                 detections: Dict[str, Dict],
                                 session_usage: Dict[str, float],
                                 get_trusted_datetime,
                                 kill_app_func,
                                 report_critical_event_func) -> None:
        """Enforce time limits - check total daily usage from backend.
        
        Args:
            daily_limits: Dict of rule_name -> limit in seconds
            usage_by_app: Backend-reported usage by app
            detections: Current app detections from monitor
            session_usage: Local session usage from monitor
            get_trusted_datetime: Callable for trusted time
            kill_app_func: Callable to kill an app
            report_critical_event_func: Callable to report critical events
        """
        # Reset notification tracking daily
        today = get_trusted_datetime().date()
        if self._last_limit_reset_date != today:
            self._apps_limit_exceeded_notified.clear()
            self._apps_limit_warning_notified.clear()
            self._last_limit_reset_date = today
            self.logger.info("Daily limit notification tracking reset")
        
        for rule_name, limit_seconds in daily_limits.items():
            rule_low = rule_name.lower()
            
            # Find ALL processes that match this rule
            matched_apps = self._find_matching_apps(rule_low, detections)
            
            if not matched_apps:
                continue
            
            # Get usage
            backend_seconds = self._get_backend_usage(rule_low, usage_by_app)
            local_seconds = max(session_usage.get(app, 0) for app in matched_apps)
            total_seconds = max(backend_seconds, int(local_seconds))
            
            remaining_seconds = limit_seconds - total_seconds
            remaining_minutes = max(0, int(remaining_seconds / 60))
            
            if total_seconds >= limit_seconds:
                # Limit exceeded
                self._handle_limit_exceeded(
                    rule_name, rule_low, matched_apps, total_seconds, limit_seconds,
                    kill_app_func, report_critical_event_func
                )
            elif total_seconds >= limit_seconds * 0.7:
                # Warning threshold (70%)
                self._handle_limit_warning(rule_name, rule_low, remaining_minutes)
                
    def _find_matching_apps(self, rule_low: str, detections: Dict[str, Dict]) -> list:
        """Find all running apps that match a rule."""
        matched = []
        for app_name, info in detections.items():
            app_low = app_name.lower()
            orig_low = info.get('original_name', '').lower()
            title_low = info.get('title', '').lower()
            
            if rule_low == app_low or (len(rule_low) >= 3 and rule_low in app_low):
                matched.append(app_name)
            elif orig_low and (rule_low == orig_low or (len(rule_low) >= 3 and rule_low in orig_low)):
                matched.append(app_name)
            elif title_low and (rule_low in title_low):
                matched.append(app_name)
                
        return matched
        
    def _get_backend_usage(self, rule_low: str, usage_by_app: Dict[str, int]) -> int:
        """Get backend-reported usage for a rule."""
        backend_seconds = 0
        for app_key in usage_by_app:
            if app_key.lower() == rule_low or (len(rule_low) >= 3 and rule_low in app_key.lower()):
                backend_seconds = max(backend_seconds, usage_by_app[app_key])
        return backend_seconds
        
    def _handle_limit_exceeded(self, rule_name: str, rule_low: str,
                               matched_apps: list, total_seconds: int, limit_seconds: int,
                               kill_app_func, report_critical_event_func) -> None:
        """Handle when a time limit is exceeded."""
        self.logger.warning(f"TIME LIMIT EXCEEDED: {rule_name} (Matches: {matched_apps}) "
                           f"used {int(total_seconds/60)}m / {int(limit_seconds/60)}m")
        for app in matched_apps:
            kill_app_func(app, reason="time_limit_exceeded",
                         used_seconds=int(total_seconds), limit_seconds=int(limit_seconds))
        
        if rule_low not in self._apps_limit_exceeded_notified:
            self.notification_manager.show_limit_exceeded(rule_name)
            self._apps_limit_exceeded_notified.add(rule_low)
            report_critical_event_func('limit_exceeded', rule_name, int(total_seconds), int(limit_seconds))
            
    def _handle_limit_warning(self, rule_name: str, rule_low: str, remaining_minutes: int) -> None:
        """Handle when approaching a time limit."""
        if rule_low not in self._apps_limit_warning_notified:
            self.notification_manager.show_limit_warning(rule_name, remaining_minutes)
            self._apps_limit_warning_notified.add(rule_low)
            
    def enforce_daily_device_limit(self, device_daily_limit: Optional[int],
                                    device_today_usage: int,
                                    monitor) -> None:
        """Enforce daily device limit - total usage for the whole device.
        
        Args:
            device_daily_limit: Limit in seconds, or None if no limit
            device_today_usage: Backend-reported device usage
            monitor: Monitor instance for local usage
        """
        if device_daily_limit is None:
            self._daily_limit_warning_shown = False
            self._daily_limit_shutdown_initiated = False
            return
        
        # Get total device usage today
        local_total = monitor.get_device_usage() if monitor else 0
        total_usage = max(device_today_usage, int(local_total))
        
        remaining_seconds = device_daily_limit - total_usage
        remaining_minutes = max(0, int(remaining_seconds / 60))
        percentage_used = (total_usage / device_daily_limit * 100) if device_daily_limit > 0 else 0
        
        self.logger.debug(f"Daily limit check: {total_usage}s / {device_daily_limit}s ({percentage_used:.1f}%)")
        
        if total_usage >= device_daily_limit:
            self._handle_daily_limit_exceeded()
        elif percentage_used >= 80:
            self._handle_daily_limit_warning(remaining_minutes)
            
    def _handle_daily_limit_exceeded(self) -> None:
        """Handle when daily device limit is exceeded."""
        if not self._daily_limit_shutdown_initiated:
            self.logger.critical("DAILY DEVICE LIMIT EXCEEDED - Initiating shutdown sequence")
            self._daily_limit_shutdown_initiated = True
            
            countdown = 60
            self.notification_manager.show_daily_limit_exceeded(countdown)
            self.shutdown_manager.lock_and_shutdown(countdown)
            
    def _handle_daily_limit_warning(self, remaining_minutes: int) -> None:
        """Handle when approaching daily device limit."""
        # Reset warning flag if 5 minutes have passed
        if self._daily_limit_warning_shown and (time.time() - self._daily_limit_warning_shown_at > 300):
            self._daily_limit_warning_shown = False
        
        if not self._daily_limit_warning_shown:
            self.logger.warning(f"Approaching daily device limit: {remaining_minutes} minutes remaining")
            self.notification_manager.show_daily_limit_warning(remaining_minutes)
            self._daily_limit_warning_shown = True
            self._daily_limit_warning_shown_at = time.time()
