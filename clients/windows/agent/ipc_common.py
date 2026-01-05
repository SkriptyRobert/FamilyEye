"""IPC Common - Shared constants and message protocol.

Provides Named Pipe communication between BOSS (Service in Session 0)
and MESSENGER (ChildAgent in user session).
"""
import json
from enum import Enum
from typing import Optional, Dict, Any


# Named Pipe configuration
PIPE_NAME = r"\\.\pipe\FamilyEyeAgentIPC"
PIPE_BUFFER_SIZE = 4096
PIPE_TIMEOUT_MS = 5000


class IPCCommand(str, Enum):
    """IPC Command types."""
    # Heartbeat
    PING = "PING"
    PONG = "PONG"
    
    # Notifications
    SHOW_WARNING = "SHOW_WARNING"
    SHOW_ERROR = "SHOW_ERROR"
    SHOW_INFO = "SHOW_INFO"
    SHOW_LIMIT_WARNING = "SHOW_LIMIT_WARNING"
    SHOW_LIMIT_EXCEEDED = "SHOW_LIMIT_EXCEEDED"
    SHOW_DAILY_LIMIT_WARNING = "SHOW_DAILY_LIMIT_WARNING"
    SHOW_DAILY_LIMIT_EXCEEDED = "SHOW_DAILY_LIMIT_EXCEEDED"
    SHOW_SCHEDULE_WARNING = "SHOW_SCHEDULE_WARNING"
    SHOW_SCHEDULE_ENDED = "SHOW_SCHEDULE_ENDED"
    SHOW_OUTSIDE_SCHEDULE = "SHOW_OUTSIDE_SCHEDULE"
    SHOW_STARTUP_NOTIFICATION = "SHOW_STARTUP_NOTIFICATION"
    
    # Lock screen
    SHOW_LOCK_SCREEN = "SHOW_LOCK_SCREEN"
    HIDE_LOCK_SCREEN = "HIDE_LOCK_SCREEN"
    SHOW_COUNTDOWN = "SHOW_COUNTDOWN"
    
    # Status
    STATUS_REQUEST = "STATUS_REQUEST"
    STATUS_RESPONSE = "STATUS_RESPONSE"
    
    # Heartbeat from ChildAgent to Service
    HEARTBEAT = "HEARTBEAT"
    
    # Child agent control
    SHUTDOWN = "SHUTDOWN"
    
    # Screenshots
    TAKE_SCREENSHOT = "TAKE_SCREENSHOT"
    SCREENSHOT_DATA = "SCREENSHOT_DATA"
    SCREENSHOT_READY = "SCREENSHOT_READY"  # ChildAgent saved screenshot to file


class IPCMessage:
    """IPC Message container."""
    
    def __init__(self, command: IPCCommand, data: Optional[Dict[str, Any]] = None):
        self.command = command if isinstance(command, str) else command.value
        self.data = data or {}
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "command": self.command,
            "data": self.data
        })
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for pipe transmission."""
        return self.to_json().encode('utf-8')
    
    @classmethod
    def from_json(cls, json_str: str) -> 'IPCMessage':
        """Deserialize from JSON string."""
        try:
            obj = json.loads(json_str)
            return cls(
                command=obj.get("command", ""),
                data=obj.get("data", {})
            )
        except json.JSONDecodeError:
            raise ValueError(f"Invalid IPC message format: {json_str[:100]}")
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'IPCMessage':
        """Deserialize from bytes."""
        return cls.from_json(data.decode('utf-8'))
    
    def __repr__(self):
        return f"IPCMessage({self.command}, {self.data})"


# Message factory functions for convenience
def msg_ping() -> IPCMessage:
    return IPCMessage(IPCCommand.PING)

def msg_pong() -> IPCMessage:
    return IPCMessage(IPCCommand.PONG)

def msg_show_warning(title: str, message: str) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_WARNING, {"title": title, "message": message})

def msg_show_error(title: str, message: str) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_ERROR, {"title": title, "message": message})

def msg_show_info(title: str, message: str) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_INFO, {"title": title, "message": message})

def msg_show_limit_warning(app_name: str, remaining_minutes: int) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_LIMIT_WARNING, {
        "app_name": app_name,
        "remaining_minutes": remaining_minutes
    })

def msg_show_limit_exceeded(app_name: str) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_LIMIT_EXCEEDED, {"app_name": app_name})

def msg_show_daily_limit_warning(remaining_minutes: int) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_DAILY_LIMIT_WARNING, {
        "remaining_minutes": remaining_minutes
    })

def msg_show_daily_limit_exceeded(countdown_seconds: int) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_DAILY_LIMIT_EXCEEDED, {
        "countdown_seconds": countdown_seconds
    })

def msg_show_schedule_warning(minutes_until_end: int) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_SCHEDULE_WARNING, {
        "minutes_until_end": minutes_until_end
    })

def msg_show_schedule_ended(countdown_seconds: int) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_SCHEDULE_ENDED, {
        "countdown_seconds": countdown_seconds
    })

def msg_show_outside_schedule() -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_OUTSIDE_SCHEDULE)

def msg_show_startup_notification() -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_STARTUP_NOTIFICATION)

def msg_show_lock_screen(message: str) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_LOCK_SCREEN, {"message": message})

def msg_hide_lock_screen() -> IPCMessage:
    return IPCMessage(IPCCommand.HIDE_LOCK_SCREEN)

def msg_show_countdown(seconds: int, reason: str) -> IPCMessage:
    return IPCMessage(IPCCommand.SHOW_COUNTDOWN, {
        "seconds": seconds,
        "reason": reason
    })

def msg_shutdown() -> IPCMessage:
    return IPCMessage(IPCCommand.SHUTDOWN)
