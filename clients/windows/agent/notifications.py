"""Notification system for user alerts.

Refactored for Session 0 service architecture:
- Uses IPC (Named Pipes) to send notifications to ChildAgent
- ChildAgent runs in user session and displays actual UI
- Fallback to console logging if IPC not available

Original PowerShell WPF code kept as fallback for standalone testing.
"""
import ctypes
import datetime
import subprocess
import threading
import time
from typing import Optional
from .logger import get_logger


# =============================================================================
# Vector Icon Paths (Material Design style) - kept for reference
# =============================================================================
ICON_LOCK = "M18,8H17V6A5,5 0 0,0 7,6V8H6A2,2 0 0,0 4,10V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V10A2,2 0 0,0 18,8M12,17A2,2 0 1,1 14,15A2,2 0 0,1 12,17M15,8H9V6A3,3 0 0,1 15,6V8Z"
ICON_ALERT = "M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"
ICON_EYE = "M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"


# Try to import IPC components
try:
    from .ipc_server import get_ipc_server, IPCServer
    from .ipc_common import (
        msg_show_warning, msg_show_error, msg_show_info,
        msg_show_limit_warning, msg_show_limit_exceeded,
        msg_show_daily_limit_warning, msg_show_daily_limit_exceeded,
        msg_show_schedule_warning, msg_show_schedule_ended,
        msg_show_outside_schedule, msg_show_startup_notification,
        msg_show_lock_screen, msg_hide_lock_screen, msg_show_countdown
    )
    _ipc_available = True
except ImportError:
    _ipc_available = False


def _run_powershell(script: str, timeout: Optional[int] = None) -> bool:
    """Execute PowerShell script with common configuration. Returns True on success."""
    try:
        kwargs = {
            "capture_output": True,
            "creationflags": subprocess.CREATE_NO_WINDOW
        }
        if timeout:
            kwargs["timeout"] = timeout
        subprocess.run(["powershell", "-Command", script], **kwargs)
        return True
    except Exception:
        return False


def _escape_xaml_text(text: str) -> str:
    """Escape special characters for XAML text content."""
    return text.replace(chr(10), '&#x0a;').replace('"', '&quot;')


class NotificationManager:
    """Manage user notifications and alerts.
    
    In Session 0 (service mode), notifications are sent via IPC to ChildAgent.
    ChildAgent runs in user session and displays actual UI elements.
    """
    
    # Windows constants for MessageBox (fallback only)
    MB_OK = 0x00000000
    MB_ICONWARNING = 0x00000030
    MB_ICONERROR = 0x00000010
    MB_ICONINFORMATION = 0x00000040
    MB_SYSTEMMODAL = 0x00001000
    MB_SETFOREGROUND = 0x00010000
    
    # Notification limits per category
    _NOTIFICATION_LIMITS = {
        'limit_exceeded': 2,
        'limit_warning': 2,
        'daily_limit_warning': 3,
        'schedule_warning': 2,
        'default': 3
    }
    
    def __init__(self, ipc_server: Optional['IPCServer'] = None):
        """Initialize NotificationManager.
        
        Args:
            ipc_server: Optional IPC server instance. If not provided,
                       will try to get global instance or fall back to direct UI.
        """
        self.logger = get_logger('NOTIFY')
        self._notification_count = {}
        self._last_reset_date = None
        
        # IPC mode - send notifications to ChildAgent
        self._ipc_server = ipc_server
        self._use_ipc = _ipc_available
        
        if self._use_ipc and not self._ipc_server:
            try:
                self._ipc_server = get_ipc_server()
            except Exception as e:
                self.logger.warning(f"Failed to get IPC server: {e}")
                self._use_ipc = False
    
    def set_ipc_server(self, ipc_server: 'IPCServer'):
        """Set or update the IPC server reference."""
        self._ipc_server = ipc_server
        self._use_ipc = True
        self.logger.debug("IPC server set for notifications")
    
    def _can_show_notification(self, notification_id: str, category: str = 'default') -> bool:
        """Check if notification can be shown (count-based daily limit)."""
        today = datetime.date.today()
        if self._last_reset_date != today:
            self._notification_count.clear()
            self._last_reset_date = today
            self.logger.info("Daily notification counts reset")
        
        current = self._notification_count.get(notification_id, 0)
        limit = self._NOTIFICATION_LIMITS.get(category, self._NOTIFICATION_LIMITS['default'])
        
        if current < limit:
            self._notification_count[notification_id] = current + 1
            self.logger.debug(f"Notification {notification_id}: {current + 1}/{limit}")
            return True
        return False
    
    def _send_via_ipc(self, message) -> bool:
        """Send notification via IPC to ChildAgent."""
        if not self._use_ipc or not self._ipc_server:
            return False
        
        try:
            self._ipc_server.broadcast(message)
            self.logger.debug(f"Sent IPC notification: {message.command}")
            return True
        except Exception as e:
            self.logger.warning(f"IPC send failed: {e}")
            return False
    
    # =========================================================================
    # Public notification methods - use IPC if available
    # =========================================================================

    def show_warning(self, title: str, message: str, notification_id: Optional[str] = None):
        """Show warning toast notification."""
        if notification_id and not self._can_show_notification(notification_id):
            return
        self.logger.info(f"Showing warning: {title}")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_warning(f"⚠️ {title}", message))
        else:
            self._fallback_toast(f"⚠️ {title}", message)
    
    def show_error(self, title: str, message: str, notification_id: Optional[str] = None):
        """Show error blocking dialog."""
        if notification_id and not self._can_show_notification(notification_id):
            return
        self.logger.warning(f"Showing error: {title}")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_error(f"🚫 {title}", message))
        else:
            self._fallback_popup(f"🚫 {title}", message, is_error=True)
    
    def show_info(self, title: str, message: str, notification_id: Optional[str] = None):
        """Show info toast notification."""
        if notification_id and not self._can_show_notification(notification_id):
            return
        self.logger.info(f"Showing info: {title}")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_info(f"ℹ️ {title}", message))
        else:
            self._fallback_toast(f"ℹ️ {title}", message)
    
    def show_limit_warning(self, app_name: str, remaining_minutes: int):
        """Show warning about approaching app time limit."""
        nid = f"limit_warning_{app_name}"
        if not self._can_show_notification(nid, 'limit_warning'):
            return
        
        self.logger.info(f"Limit warning: {app_name} - {remaining_minutes}m remaining")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_limit_warning(app_name, remaining_minutes))
        else:
            self._fallback_toast(
                "⚠️ Blíží se limit aplikace",
                f"V aplikaci '{app_name}' zbývá už jen {remaining_minutes} minut."
            )
    
    def show_limit_exceeded(self, app_name: str):
        """Show notification that app time limit was exceeded."""
        nid = f"limit_exceeded_{app_name}"
        if not self._can_show_notification(nid, 'limit_exceeded'):
            return
        
        self.logger.warning(f"Limit exceeded: {app_name}")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_limit_exceeded(app_name))
        else:
            self._fallback_popup(
                "🚫 Limit vyčerpán",
                f"Čas pro aplikaci '{app_name}' vypršel. Aplikace byla ukončena.",
                is_error=True
            )
    
    def show_daily_limit_warning(self, remaining_minutes: int):
        """Show warning about approaching daily device limit."""
        if not self._can_show_notification("daily_limit_warning", 'daily_limit_warning'):
            return
        
        self.logger.info(f"Daily limit warning: {remaining_minutes}m remaining")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_daily_limit_warning(remaining_minutes))
        else:
            self._fallback_toast(
                "⚠️ Blíží se denní limit",
                f"Zbývá ti {remaining_minutes} minut času na počítači."
            )
    
    def show_daily_limit_exceeded(self, countdown_seconds: int = 60):
        """Show notification that daily limit was exceeded."""
        self.logger.warning(f"Daily limit exceeded, countdown: {countdown_seconds}s")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_daily_limit_exceeded(countdown_seconds))
        else:
            self._fallback_popup(
                "🚫 Denní limit vyčerpán",
                f"Tvůj čas na počítači pro dnešek vypršel.\n\nSystém se vypne za {countdown_seconds} sekund.",
                is_error=True
            )
    
    def show_schedule_warning(self, minutes_until_end: int):
        """Show warning that allowed time is ending."""
        if not self._can_show_notification("schedule_warning", 'schedule_warning'):
            return
        
        self.logger.info(f"Schedule warning: {minutes_until_end}m until end")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_schedule_warning(minutes_until_end))
        else:
            self._fallback_toast(
                "⚠️ Blíží se večerka",
                f"Za {minutes_until_end} minut začíná noční klid."
            )
    
    def show_schedule_ended(self, countdown_seconds: int = 60):
        """Show notification that schedule time ended."""
        self.logger.warning(f"Schedule ended, countdown: {countdown_seconds}s")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_schedule_ended(countdown_seconds))
        else:
            self._fallback_popup(
                "🌙 Noční klid",
                f"Je čas jít spát. Počítač se vypne za {countdown_seconds} sekund.",
                is_error=True
            )
    
    def show_outside_schedule(self):
        """Show notification that current time is outside allowed schedule."""
        if not self._can_show_notification("outside_schedule"):
            return
        
        self.logger.warning("Outside schedule notification")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_outside_schedule())
        else:
            self._fallback_popup(
                "🌙 Mimo povolený čas",
                "V tuto dobu není povoleno používat počítač.",
                is_error=True
            )

    def show_startup_transparent_notification(self):
        """Show branded startup notification (transparency message)."""
        self.logger.info("Showing startup transparency notification")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_startup_notification())
        else:
            self._fallback_branded_popup("Monitorování aktivní")
    
    # =========================================================================
    # Lock screen methods (IPC only - requires ChildAgent)
    # =========================================================================
    
    def show_lock_screen(self, message: str = "Zařízení bylo zamčeno rodičem."):
        """Show full-screen lock overlay via ChildAgent."""
        self.logger.warning(f"Lock screen requested: {message}")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_lock_screen(message))
        else:
            self.logger.warning("Lock screen requires ChildAgent - falling back to workstation lock")
            try:
                ctypes.windll.user32.LockWorkStation()
            except:
                pass
    
    def hide_lock_screen(self):
        """Hide the lock screen overlay."""
        self.logger.info("Hide lock screen requested")
        
        if self._use_ipc:
            self._send_via_ipc(msg_hide_lock_screen())
    
    def show_countdown(self, seconds: int, reason: str):
        """Show countdown overlay before shutdown."""
        self.logger.warning(f"Countdown: {seconds}s - {reason}")
        
        if self._use_ipc:
            self._send_via_ipc(msg_show_countdown(seconds, reason))
        else:
            # Fallback - just show popup
            self._fallback_popup(reason, f"Systém se vypne za {seconds} sekund.", is_error=True)
    
    # =========================================================================
    # Fallback methods (when IPC not available - for testing/development)
    # =========================================================================
    
    def _fallback_toast(self, title: str, message: str):
        """Fallback toast notification using PowerShell."""
        ps_script = f'''
$ErrorActionPreference = 'SilentlyContinue'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).InnerText = "{title}"
$textNodes.Item(1).InnerText = "{message}"
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("FamilyEye.Agent")
$notifier.Show([Windows.UI.Notifications.ToastNotification]::new($template))
'''
        threading.Thread(target=lambda: _run_powershell(ps_script, timeout=5), daemon=True).start()
    
    def _fallback_popup(self, title: str, message: str, is_error: bool = False):
        """Fallback popup using Windows Forms MessageBox."""
        def _show():
            ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show(
    "{message.replace('"', '`"').replace(chr(10), '`n')}",
    "{title.replace('"', '`"')}",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::{'Error' if is_error else 'Warning'}
)
'''
            _run_powershell(ps_script, timeout=30)
        threading.Thread(target=_show, daemon=True).start()
    
    def _fallback_branded_popup(self, message: str):
        """Fallback branded popup - just log for now."""
        self.logger.info(f"Branded notification (fallback): {message}")


class ShutdownManager:
    """Manage system shutdown and lock operations."""
    
    def __init__(self):
        self.logger = get_logger('SHUTDOWN')
        self._shutdown_scheduled = False
        self._shutdown_thread = None
    
    def lock_workstation(self) -> bool:
        """Lock the Windows workstation."""
        try:
            ctypes.windll.user32.LockWorkStation()
            self.logger.info("Workstation locked")
            return True
        except Exception as e:
            self.logger.error(f"Failed to lock workstation: {e}")
            return False
    
    def shutdown_computer(self, delay_seconds: int = 0, force: bool = True) -> bool:
        """Schedule computer shutdown."""
        try:
            cmd = ["shutdown", "/s", "/t", str(delay_seconds)]
            if force:
                cmd.append("/f")
            subprocess.run(cmd, capture_output=True)
            self.logger.warning(f"Shutdown scheduled in {delay_seconds} seconds")
            return True
        except Exception as e:
            self.logger.error(f"Failed to schedule shutdown: {e}")
            return False
    
    def cancel_shutdown(self) -> bool:
        """Cancel scheduled shutdown."""
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True)
            self.logger.info("Shutdown cancelled")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cancel shutdown: {e}")
            return False
    
    def lock_and_shutdown(self, countdown_seconds: int = 60):
        """Lock workstation and schedule shutdown after countdown."""
        if self._shutdown_scheduled:
            self.logger.info("Shutdown already scheduled, skipping")
            return
        
        self._shutdown_scheduled = True
        
        def _execute():
            self.lock_workstation()
            time.sleep(2)
            self.shutdown_computer(delay_seconds=countdown_seconds - 2, force=True)
            self.logger.warning(f"System will shutdown in {countdown_seconds} seconds")
        
        self._shutdown_thread = threading.Thread(target=_execute, daemon=True)
        self._shutdown_thread.start()
    
    def reset_shutdown_flag(self):
        """Reset the shutdown flag (for when rules change)."""
        self._shutdown_scheduled = False
