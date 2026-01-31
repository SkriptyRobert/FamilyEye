"""Device schedule enforcement logic."""
from typing import List, Dict, Optional, Callable
from ..logger import get_logger


class ScheduleEnforcer:
    """Handles device-wide schedule enforcement."""
    
    def __init__(self, notification_manager, shutdown_manager, logger=None):
        self.logger = logger or get_logger('ENFORCER.SCHEDULE')
        self.notification_manager = notification_manager
        self.shutdown_manager = shutdown_manager
        
        self._schedule_warning_shown = False
        self._schedule_shutdown_initiated = False
        
    @staticmethod
    def parse_schedule_days(days_raw: str) -> list:
        """Parse schedule days - supports both numeric ('0,1,2') and text ('mon,tue,wed') formats.
        
        Args:
            days_raw: Comma-separated days string
            
        Returns:
            List of day abbreviations (e.g., ['mon', 'tue', 'wed'])
        """
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
        
    def enforce_device_schedule(self, device_schedules: List[Dict],
                                 get_trusted_datetime: Callable) -> None:
        """Enforce schedule rules - allowed time windows for the WHOLE DEVICE.
        
        Args:
            device_schedules: List of schedule dicts with start_time, end_time, days
            get_trusted_datetime: Callable returning trusted datetime
        """
        if not device_schedules:
            self._schedule_warning_shown = False
            self._schedule_shutdown_initiated = False
            self.shutdown_manager.reset_shutdown_flag()
            return
        
        now = get_trusted_datetime()
        current_time_str = now.strftime("%H:%M")
        current_day = now.strftime("%a").lower()[:3]
        
        # First check if TODAY is covered by ANY schedule rule
        today_has_schedule = self._check_today_has_schedule(device_schedules, current_day)
        
        if not today_has_schedule:
            # Today is NOT covered by any schedule - no enforcement, PC is allowed
            self._schedule_warning_shown = False
            self._schedule_shutdown_initiated = False
            self.shutdown_manager.reset_shutdown_flag()
            return
        
        # Today HAS a schedule - check if we're within ANY allowed time window
        is_within_schedule, minutes_until_end = self._check_within_schedule(
            device_schedules, current_day, now
        )
        
        if is_within_schedule:
            self._handle_within_schedule(minutes_until_end, now)
        else:
            self._handle_outside_schedule()
            
    def _check_today_has_schedule(self, schedules: List[Dict], current_day: str) -> bool:
        """Check if today is covered by any schedule rule."""
        for schedule in schedules:
            allowed_days = schedule.get("days")
            if not allowed_days:
                # No days specified = applies to all days
                return True
            allowed_days_list = self.parse_schedule_days(allowed_days)
            if current_day in allowed_days_list:
                return True
        return False
        
    def _check_within_schedule(self, schedules: List[Dict], current_day: str,
                               now) -> tuple:
        """Check if current time is within any allowed schedule.
        
        Returns:
            Tuple of (is_within: bool, minutes_until_end: int or None)
        """
        for schedule in schedules:
            start_time = schedule.get("start_time")
            end_time = schedule.get("end_time")
            allowed_days = schedule.get("days")
            
            # Check if today is an allowed day
            if allowed_days:
                allowed_days_list = self.parse_schedule_days(allowed_days)
                if current_day not in allowed_days_list:
                    continue
            
            # Check if current time is within the schedule
            if start_time and end_time:
                try:
                    start_parts = start_time.split(":")
                    end_parts = end_time.split(":")
                    
                    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1] if len(start_parts) > 1 else 0)
                    end_minutes = int(end_parts[0]) * 60 + int(end_parts[1] if len(end_parts) > 1 else 0)
                    current_minutes = now.hour * 60 + now.minute
                    
                    if start_minutes <= current_minutes <= end_minutes:
                        return True, end_minutes - current_minutes
                except (ValueError, IndexError):
                    pass
                    
        return False, None
        
    def _handle_within_schedule(self, minutes_until_end: Optional[int], now) -> None:
        """Handle when we're within allowed time."""
        self._schedule_shutdown_initiated = False
        self.shutdown_manager.reset_shutdown_flag()
        
        # Show warning if approaching end
        if minutes_until_end is not None and minutes_until_end <= 10:
            # Bedtime (Večerka) is now 21:00 - 06:00
            is_night_hours = now.hour >= 21 or now.hour < 6
            
            if not self._schedule_warning_shown:
                if is_night_hours:
                    # Specific "Bedtime" branding
                    self.logger.warning(f"Bedtime approaching: {minutes_until_end} minutes remaining")
                    self.notification_manager.show_schedule_warning(minutes_until_end)
                else:
                    # Daytime - show generic schedule warning
                    self.logger.warning(f"Schedule ending soon: {minutes_until_end} minutes remaining")
                    self.notification_manager.show_warning(
                        "Konec povoleného času",
                        f"Váš vymezený čas brzy vyprší (zbývá {minutes_until_end} min)."
                    )
                self._schedule_warning_shown = True
        else:
            self._schedule_warning_shown = False
            
    def _handle_outside_schedule(self) -> None:
        """Handle when we're outside allowed time."""
        if not self._schedule_shutdown_initiated:
            self.logger.critical("OUTSIDE ALLOWED SCHEDULE - Initiating shutdown sequence")
            self._schedule_shutdown_initiated = True
            
            countdown = 60
            self.notification_manager.show_outside_schedule()
            self.shutdown_manager.lock_and_shutdown(countdown)
