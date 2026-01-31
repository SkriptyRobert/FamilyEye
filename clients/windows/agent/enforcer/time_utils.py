"""Trusted time utilities for tamper-resistant time checking."""
import time
from datetime import datetime
from ..logger import get_logger


class TimeSync:
    """Provides trusted time based on server sync with monotonic clock."""
    
    SYNC_MAX_AGE = 3600  # 1 hour
    
    def __init__(self):
        self.logger = get_logger('ENFORCER.TIME')
        # Time Synchronization (Monotonic)
        self.clock_offset: float = 0.0
        self.ref_monotonic: float = 0.0
        self.ref_server_ts: float = 0.0
        self.is_synced: bool = False
        self.last_sync = 0
        
    def sync_from_server(self, server_time_str: str) -> bool:
        """Sync local time from server timestamp.
        
        Args:
            server_time_str: ISO format datetime string (UTC)
            
        Returns:
            True if sync successful
        """
        try:
            # Handle ISO format with potential Z
            if server_time_str.endswith('Z'):
                server_time_str = server_time_str[:-1] + '+00:00'
            
            server_dt = datetime.fromisoformat(server_time_str)
            server_ts = server_dt.timestamp()
            
            # Monotonic Sync (Primary Source of Truth)
            self.ref_server_ts = server_ts
            self.ref_monotonic = time.monotonic()
            self.is_synced = True
            self.last_sync = time.time()
            
            self.logger.info(f"Time synced. Server: {server_dt}, Monotonic Ref: {self.ref_monotonic}")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to sync time: {e}")
            return False
    
    def _check_sync_validity(self) -> None:
        """Check if sync is still valid (not expired)."""
        if self.is_synced and (time.monotonic() - self.ref_monotonic > self.SYNC_MAX_AGE):
            self.logger.warning("Time sync expired (older than 1h), reverting to system time")
            self.is_synced = False
            
    def get_trusted_datetime(self) -> datetime:
        """Get trusted local datetime distinct from system clock if possible."""
        self._check_sync_validity()
        
        if self.is_synced:
            # Calculate elapsed since sync
            elapsed = time.monotonic() - self.ref_monotonic
            current_server_ts = self.ref_server_ts + elapsed
            
            # Convert to local time (Server UTC TS -> Local DT)
            return datetime.fromtimestamp(current_server_ts)
        else:
            return datetime.now()

    def get_trusted_utc_datetime(self) -> datetime:
        """Get trusted UTC datetime."""
        self._check_sync_validity()
        
        if self.is_synced:
            elapsed = time.monotonic() - self.ref_monotonic
            current_server_ts = self.ref_server_ts + elapsed
            return datetime.utcfromtimestamp(current_server_ts)
        else:
            return datetime.utcnow()
