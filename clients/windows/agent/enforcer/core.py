"""Core rule enforcement orchestrator.

This module provides the main RuleEnforcer class that orchestrates all
enforcement sub-modules. Refactored from monolithic enforcer.py for maintainability.
"""
import os
import time
from datetime import datetime
from typing import List, Dict, Set, Optional

from ..config import config
from ..network_control import NetworkController
from ..logger import get_logger
from ..notifications import NotificationManager, ShutdownManager

from .cache import RuleCache
from .time_utils import TimeSync
from .app_blocking import AppBlockingEnforcer
from .time_limits import TimeLimitEnforcer
from .schedule import ScheduleEnforcer
from .network import NetworkEnforcer


class RuleEnforcer:
    """Enforce rules on device.
    
    Orchestrates sub-modules for:
    - Rule caching (offline resilience)
    - Time synchronization (anti-tampering)
    - App blocking (blocked apps, app schedules)
    - Time limits (app limits, daily device limit)
    - Schedule enforcement (device-wide time windows)
    - Network enforcement (VPN, websites, full block)
    """
    
    def __init__(self):
        self.logger = get_logger('ENFORCER')
        
        # Core data
        self.rules: List[Dict] = []
        self.blocked_apps: Set[str] = set()
        self.daily_limits: Dict[str, int] = {}  # app_name -> seconds
        self.usage_by_app: Dict[str, int] = {}  # app_name -> total seconds today (from backend)
        self.blocked_websites: Set[str] = set()
        
        # External references
        self.monitor = None
        self.reporter = None
        
        # Core components
        self.network_controller = NetworkController()
        self.notification_manager = NotificationManager()
        self.shutdown_manager = ShutdownManager()
        
        # Sub-modules
        self._cache = RuleCache()
        self._time_sync = TimeSync()
        self._app_blocker = AppBlockingEnforcer()
        self._time_limiter = TimeLimitEnforcer(self.notification_manager, self.shutdown_manager)
        self._schedule_enforcer = ScheduleEnforcer(self.notification_manager, self.shutdown_manager)
        self._network_enforcer = NetworkEnforcer(self.network_controller)
        
        # State
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
        self._needs_immediate_fetch = False
        
        # Device limits
        self.device_daily_limit: Optional[int] = None  # seconds
        self.device_today_usage: int = 0  # seconds from backend
        
        # Schedules
        self.device_schedules: List[Dict] = []
        self.app_schedules: Dict[str, List[Dict]] = {}  # app_name -> list of schedules
        
        # Register for reconnection events
        from ..api_client import api_client
        api_client.add_on_reconnect_callback(self.trigger_immediate_fetch)
    
    def set_monitor(self, monitor):
        """Set monitor instance."""
        self.monitor = monitor
        # Try to load cached rules on startup
        self._load_rules_cache()

    def set_reporter(self, reporter):
        """Set reporter instance for sync-on-fetch."""
        self.reporter = reporter
        
    # ========== Time Sync Wrappers ==========
    
    def get_trusted_datetime(self) -> datetime:
        """Get trusted local datetime distinct from system clock if possible."""
        return self._time_sync.get_trusted_datetime()

    def get_trusted_utc_datetime(self) -> datetime:
        """Get trusted UTC datetime."""
        return self._time_sync.get_trusted_utc_datetime()
        
    # ========== Cache Wrappers ==========
    
    def _save_rules_cache(self):
        """Save current rules to local cache."""
        self._cache.save(
            self.rules, 
            self.usage_by_app, 
            self.device_today_usage,
            lambda: self.get_trusted_utc_datetime().timestamp()
        )
            
    def _load_rules_cache(self):
        """Load rules from local cache."""
        cached = self._cache.load()
        if cached:
            self.rules = cached["rules"]
            self.usage_by_app = cached["usage_by_app"]
            self.device_today_usage = cached["daily_usage"]
            self._update_blocked_apps()

    def trigger_immediate_fetch(self):
        """Callback for reconnection - trigger immediate rule fetch."""
        self.logger.info("Reconnection detected - triggering immediate rule fetch")
        self._needs_immediate_fetch = True

    def _fetch_rules(self):
        """Fetch rules from backend using API Client."""
        try:
            from ..api_client import api_client
            
            if not config.is_configured():
                return

            # SYNC-ON-FETCH: Send latest usage data BEFORE asking for rules
            if self.reporter:
                try:
                    self.reporter.send_reports()
                except Exception as e:
                    self.logger.warning(f"Failed to sync usage before fetch: {e}")

            rules_data = api_client.fetch_rules()
            
            if rules_data:
                self._process_rules_response(rules_data)
                self._update_blocked_apps()
                self._save_rules_cache()
                self.logger.debug(f"Rules updated: {len(self.rules)} rules")
            else:
                self.logger.info("Falling back to local cache")
                self._load_rules_cache()

        except Exception as e:
            self.logger.error(f"Error in rule fetch cycle: {e}")
            self._load_rules_cache()
            
    def _process_rules_response(self, rules_data):
        """Process rules response from backend."""
        if isinstance(rules_data, list):
            self.rules = rules_data
        elif isinstance(rules_data, dict) and "rules" in rules_data:
            self.rules = rules_data["rules"]
            self.usage_by_app = rules_data.get("usage_by_app", {})
            self.device_today_usage = rules_data.get("daily_usage", 0)
            
            # SERVER TIME SYNC
            server_time_str = rules_data.get("server_time")
            if server_time_str:
                self._time_sync.sync_from_server(server_time_str)

            self.logger.debug(f"Received usage stats: {len(self.usage_by_app)} apps, "
                            f"{self.device_today_usage}s total today")
        else:
            self.rules = []
            
    def _update_blocked_apps(self):
        """Update blocked apps list from rules and sync network blocking."""
        self.blocked_apps.clear()
        self.daily_limits.clear()
        self.device_schedules.clear()
        self.app_schedules.clear()
        
        new_blocked_websites = set()
        self.is_locked = False
        self.is_network_blocked = False
        self.device_daily_limit = None
        
        now = self.get_trusted_datetime()
        now_str = now.strftime("%H:%M")
        
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            
            rule_type = rule.get("rule_type", "")
            app_name = rule.get("app_name", "").lower() if rule.get("app_name") else None
            website_url = rule.get("website_url", "").lower() if rule.get("website_url") else None
            
            self._process_rule(rule_type, rule, app_name, website_url, now_str, new_blocked_websites)
        
        # Sync websites
        self.blocked_websites = self._network_enforcer.sync_blocked_websites(
            new_blocked_websites, self.blocked_websites
        )
        
        # Log summary
        self.logger.info(f"Rules loaded: {len(self.rules)} total, "
                        f"blocked_apps={len(self.blocked_apps)}, "
                        f"daily_limits={len(self.daily_limits)}, "
                        f"device_schedules={len(self.device_schedules)}, "
                        f"app_schedules={list(self.app_schedules.keys())}")
                        
    def _process_rule(self, rule_type: str, rule: Dict, app_name: Optional[str],
                      website_url: Optional[str], now_str: str, 
                      new_blocked_websites: Set[str]):
        """Process a single rule."""
        if rule_type == "app_block":
            self._process_app_block_rule(app_name)
        elif rule_type == "time_limit":
            self._process_time_limit_rule(app_name, rule)
        elif rule_type == "daily_limit":
            limit_minutes = rule.get("time_limit", 0)
            if limit_minutes > 0:
                self.device_daily_limit = limit_minutes * 60
                self.logger.info(f"Daily device limit set: {limit_minutes} minutes")
        elif rule_type == "schedule":
            self._process_schedule_rule(app_name, rule)
        elif rule_type == "lock_device":
            self.is_locked = True
        elif rule_type == "network_block":
            self._process_network_block_rule(rule, now_str)
        elif rule_type in ("website_block", "web_block"):
            self._process_website_block_rule(website_url, new_blocked_websites)
            
    def _process_app_block_rule(self, app_name: Optional[str]):
        """Process app_block rule."""
        if app_name:
            app_names = [a.strip().lower() for a in app_name.split(',') if a.strip()]
            for name in app_names:
                if name.endswith('.exe'):
                    name = name[:-4]
                self.blocked_apps.add(name)
                
    def _process_time_limit_rule(self, app_name: Optional[str], rule: Dict):
        """Process time_limit rule."""
        if app_name and rule.get("time_limit"):
            app_names = [a.strip().lower() for a in app_name.split(',') if a.strip()]
            limit_seconds = rule.get("time_limit", 0) * 60
            for name in app_names:
                if name.endswith('.exe'):
                    name = name[:-4]
                self.daily_limits[name] = limit_seconds
                
    def _process_schedule_rule(self, app_name: Optional[str], rule: Dict):
        """Process schedule rule."""
        base_schedule_info = {
            "start_time": rule.get("schedule_start_time"),
            "end_time": rule.get("schedule_end_time"),
            "days": rule.get("schedule_days"),
        }
        if base_schedule_info["start_time"] and base_schedule_info["end_time"]:
            if not app_name:
                # Device-wide schedule
                schedule_info = {**base_schedule_info, "app_name": None}
                self.device_schedules.append(schedule_info)
                self.logger.info(f"Device Schedule: {schedule_info['start_time']} - {schedule_info['end_time']}")
            else:
                # App-specific schedule
                app_names = [a.strip().lower() for a in app_name.split(',') if a.strip()]
                for name in app_names:
                    if name.endswith('.exe'):
                        name = name[:-4]
                    if name not in self.app_schedules:
                        self.app_schedules[name] = []
                    schedule_info = {**base_schedule_info, "app_name": name}
                    self.app_schedules[name].append(schedule_info)
                    self.logger.info(f"App Schedule ({name}): {schedule_info['start_time']} - {schedule_info['end_time']}")
                    
    def _process_network_block_rule(self, rule: Dict, now_str: str):
        """Process network_block rule."""
        start = rule.get("schedule_start_time")
        end = rule.get("schedule_end_time")
        if start and end:
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
            
    def _process_website_block_rule(self, website_url: Optional[str], 
                                     new_blocked_websites: Set[str]):
        """Process website_block rule."""
        if website_url:
            pattern = website_url.strip().lower()
            if '*' in pattern or '.' not in pattern:
                keyword = pattern.replace('*', '').strip()
                if keyword:
                    common_domains = [f"{keyword}.com", f"www.{keyword}.com", 
                                     f"{keyword}.net", f"{keyword}.org", f"m.{keyword}.com"]
                    for domain in common_domains:
                        new_blocked_websites.add(domain)
            else:
                domain = NetworkEnforcer.extract_domain(pattern)
                if domain:
                    new_blocked_websites.add(domain)
                    if not domain.startswith("www."):
                        new_blocked_websites.add(f"www.{domain}")
    
    def _report_critical_event(self, event_type: str, app_name: str = None, 
                                used_seconds: int = None, limit_seconds: int = None,
                                message: str = None):
        """Report critical event to backend immediately using centralized API client."""
        try:
            from ..api_client import api_client
            from datetime import timezone
            
            payload = {
                "event_type": event_type,
                "app_name": app_name,
                "used_seconds": used_seconds,
                "limit_seconds": limit_seconds,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            api_client.report_critical_event(payload)
                
        except Exception as e:
            self.logger.debug(f"Critical event report error (non-blocking): {e}")

    def set_ws_client(self, ws_client):
        """Set WebSocket client for connection status checks."""
        self.ws_client = ws_client

    def update(self):
        """Update enforcement - main loop entry point."""
        # Fetch rules periodically
        current_time = time.monotonic()
        
        # Dynamic Polling Strategy
        # If WS connected -> 5 min (300s) interval
        # If WS disconnected -> 10s interval (fallback)
        is_ws_connected = getattr(self, 'ws_client', None) and self.ws_client.is_connected
        
        if is_ws_connected:
            polling_interval = config.get("polling_interval_ws", 300)
        else:
            polling_interval = config.get("polling_interval", 10)
            
        if current_time - self._last_fetch_rules_time >= polling_interval or self._needs_immediate_fetch:
            if self._needs_immediate_fetch:
                self.logger.info("Immediate rule fetch triggered (reconnection/command)")
                self._needs_immediate_fetch = False
                
            self._fetch_rules()
            self._last_fetch_rules_time = current_time
        
        # Get detections from monitor
        detections = getattr(self.monitor, 'current_detections', {})
        session_usage = self.monitor.get_usage_stats() if self.monitor else {}
        
        # Enforce blocked apps and app schedules
        self._app_blocker.enforce_blocked_apps(
            blocked_apps=self.blocked_apps,
            app_schedules=self.app_schedules,
            detections=detections,
            is_locked=self.is_locked,
            get_trusted_datetime=self.get_trusted_datetime,
            parse_schedule_days=ScheduleEnforcer.parse_schedule_days,
            monitor=self.monitor
        )
        
        # Enforce app time limits
        self._time_limiter.enforce_app_time_limits(
            daily_limits=self.daily_limits,
            usage_by_app=self.usage_by_app,
            detections=detections,
            session_usage=session_usage,
            get_trusted_datetime=self.get_trusted_datetime,
            kill_app_func=lambda app, **kw: self._app_blocker.kill_app(app, monitor=self.monitor, **kw),
            report_critical_event_func=self._report_critical_event
        )
        
        # Enforce daily device limit
        self._time_limiter.enforce_daily_device_limit(
            device_daily_limit=self.device_daily_limit,
            device_today_usage=self.device_today_usage,
            monitor=self.monitor
        )
        
        # Enforce device schedule
        self._schedule_enforcer.enforce_device_schedule(
            device_schedules=self.device_schedules,
            get_trusted_datetime=self.get_trusted_datetime
        )
        
        # Enforce network
        self._network_enforcer.enforce_vpn_detection()
        self._network_enforcer.enforce_network_block(
            is_network_blocked=self.is_network_blocked,
            backend_url=config.get("backend_url", "")
        )
