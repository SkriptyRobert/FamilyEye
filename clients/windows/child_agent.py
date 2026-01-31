"""ChildAgent (MESSENGER) - User-space agent for UI display.

This agent runs in the user's session (Session 1+) and receives
commands from the Windows Service (BOSS in Session 0) via Named Pipes.

It handles:
- Displaying notifications (toasts, popups)
- Showing lock screens
- Countdown timers before shutdown
- Responding to heartbeat pings

Start this agent:
- Via Registry Run key (auto-start on login)
- Manually: python child_agent.py
"""
import os
import sys
import time
import threading
import argparse
from datetime import datetime
from pathlib import Path

# Fix imports when running as standalone
# Fix paths when running as standalone or frozen
if getattr(sys, 'frozen', False):
    # Inside _MEIPASS when frozen
    _bundle_dir = Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
    _agent_dir = _bundle_dir / "agent"
else:
    _bundle_dir = Path(__file__).parent
    _agent_dir = _bundle_dir / "agent"

if str(_bundle_dir) not in sys.path:
    sys.path.insert(0, str(_bundle_dir))

# Imports from agent package
try:
    from agent.ipc_client import IPCClient
    from agent.ipc_common import IPCCommand, IPCMessage
    from agent.ui_overlay import UIOverlay
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Script dir: {_script_dir}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)


def _pluralize_minutes(n: int) -> str:
    """Czech declension for minutes: 1 minuta, 2-4 minuty, 5+ minut."""
    if n == 1:
        return "1 minuta"
    elif 2 <= n <= 4:
        return f"{n} minuty"
    else:
        return f"{n} minut"


class ChildAgent:
    """User-space agent that displays UI elements.
    
    Connects to the Windows Service via Named Pipe and handles
    UI commands like notifications, lock screens, etc.
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.running = False
        self.ipc_client: IPCClient = None
        self.ui_overlay: UIOverlay = None
        
        # Setup logging with rotation
        import logging
        import logging.handlers
        self.logger = logging.getLogger('FamilyEye.ChildAgent')
        
        # Get log level from config or use INFO
        log_level = logging.INFO
        try:
            from agent.config import config
            level_str = config.get('log_level', 'INFO')
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
            }
            log_level = level_map.get(level_str.upper(), logging.INFO)
        except Exception:
            pass
        
        self.logger.setLevel(log_level)
        
        # Only setup handlers if not already set
        if not self.logger.handlers:
            # Console handler (only if debug mode)
            if self.debug:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(log_level)
                console_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
                console_handler.setFormatter(console_formatter)
                self.logger.addHandler(console_handler)
            
            # File handler with rotation
            log_dir = None
            try:
                if getattr(sys, 'frozen', False):
                    program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
                    target_dir = os.path.join(program_data, 'FamilyEye', 'Agent', 'Logs')
                    os.makedirs(target_dir, exist_ok=True)
                    # Test write
                    test_file = os.path.join(target_dir, '.write_test')
                    with open(test_file, 'w') as f: f.write('test')
                    os.remove(test_file)
                    log_dir = target_dir
                else:
                    # Dev mode - current dir
                    log_dir = os.path.dirname(os.path.abspath(__file__))
            except Exception as e:
                # Fallback to Temp if ProgramData is not writable
                print(f"Log path fallback due to: {e}")
                log_dir = os.path.join(os.environ.get('TEMP', '.'), 'FamilyEye')
                os.makedirs(log_dir, exist_ok=True)
            
            if log_dir:
                log_path = os.path.join(log_dir, "ui_agent.log")
                
                # Get rotation settings from config
                try:
                    from agent.config import config
                    rotation_enabled = config.get('log_rotation_enabled', True)
                    rotation_when = config.get('log_rotation_when', 'midnight')
                    rotation_backup_count = config.get('log_rotation_backup_count', 5)
                except Exception:
                    rotation_enabled = True
                    rotation_when = 'midnight'
                    rotation_backup_count = 5
                
                # Use TimedRotatingFileHandler if rotation enabled
                if rotation_enabled:
                    file_handler = logging.handlers.TimedRotatingFileHandler(
                        log_path,
                        when=rotation_when,
                        backupCount=rotation_backup_count,
                        encoding='utf-8'
                    )
                else:
                    file_handler = logging.FileHandler(log_path, encoding='utf-8')
                
                file_handler.setLevel(log_level)
                file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
        
        # Command handlers
        self._handlers = {}
        self._setup_handlers()
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message to file and optionally console."""
        level_map = {
            'DEBUG': self.logger.debug,
            'INFO': self.logger.info,
            'WARNING': self.logger.warning,
            'ERROR': self.logger.error,
            'CRITICAL': self.logger.critical,
        }
        log_func = level_map.get(level.upper(), self.logger.info)
        log_func(message)
    
    def _setup_handlers(self):
        """Setup command handlers mapping."""
        self._handlers = {
            IPCCommand.SHOW_WARNING.value: self._handle_show_warning,
            IPCCommand.SHOW_ERROR.value: self._handle_show_error,
            IPCCommand.SHOW_INFO.value: self._handle_show_info,
            IPCCommand.SHOW_LIMIT_WARNING.value: self._handle_limit_warning,
            IPCCommand.SHOW_LIMIT_EXCEEDED.value: self._handle_limit_exceeded,
            IPCCommand.SHOW_DAILY_LIMIT_WARNING.value: self._handle_daily_limit_warning,
            IPCCommand.SHOW_DAILY_LIMIT_EXCEEDED.value: self._handle_daily_limit_exceeded,
            IPCCommand.SHOW_SCHEDULE_WARNING.value: self._handle_schedule_warning,
            IPCCommand.SHOW_SCHEDULE_ENDED.value: self._handle_schedule_ended,
            IPCCommand.SHOW_OUTSIDE_SCHEDULE.value: self._handle_outside_schedule,
            IPCCommand.SHOW_STARTUP_NOTIFICATION.value: self._handle_startup_notification,
            IPCCommand.SHOW_LOCK_SCREEN.value: self._handle_lock_screen,
            IPCCommand.HIDE_LOCK_SCREEN.value: self._handle_hide_lock_screen,
            IPCCommand.SHOW_COUNTDOWN.value: self._handle_countdown,
            IPCCommand.SHUTDOWN.value: self._handle_shutdown,
            IPCCommand.TAKE_SCREENSHOT.value: self._handle_take_screenshot,
        }
    
    def _handle_message(self, message: IPCMessage):
        """Handle incoming IPC message."""
        handler = self._handlers.get(message.command)
        if handler:
            try:
                handler(message.data)
            except Exception as e:
                self._log(f"Error handling {message.command}: {e}", "ERROR")
        else:
            self._log(f"Unknown command: {message.command}", "WARNING")
    
    # --- Message Handlers ---
    
    def _handle_show_warning(self, data: dict):
        title = data.get("title", "Varování")
        message = data.get("message", "")
        self.ui_overlay.show_toast(title, message, "⚠️")
    
    def _handle_show_error(self, data: dict):
        title = data.get("title", "Chyba")
        message = data.get("message", "")
        self.ui_overlay.show_popup(title, message, is_error=True)
    
    def _handle_show_info(self, data: dict):
        title = data.get("title", "Info")
        message = data.get("message", "")
        self.ui_overlay.show_toast(title, message, "ℹ️")
    
    def _handle_limit_warning(self, data: dict):
        app_name = data.get("app_name", "Aplikace")
        remaining = data.get("remaining_minutes", 0)
        time_text = _pluralize_minutes(remaining)
        # Use WPF popup with button for limit warnings
        self.ui_overlay.show_popup(
            "Blíží se limit aplikace",
            f"V aplikaci '{app_name}' zbývá už jen {time_text}.",
            is_error=False
        )
    
    def _handle_limit_exceeded(self, data: dict):
        app_name = data.get("app_name", "Aplikace")
        # Use WPF popup with button for limit exceeded
        self.ui_overlay.show_popup(
            "Limit vyčerpán",
            f"Čas pro aplikaci '{app_name}' vypršel.\nAplikace byla ukončena.",
            is_error=True
        )

    
    def _handle_daily_limit_warning(self, data: dict):
        remaining = data.get("remaining_minutes", 0)
        time_text = _pluralize_minutes(remaining)
        self.ui_overlay.show_toast(
            "Blíží se denní limit",
            f"Zbývá ti {time_text} času na počítači.",
            "⚠️"
        )
    
    def _handle_daily_limit_exceeded(self, data: dict):
        countdown = data.get("countdown_seconds", 60)
        self.ui_overlay.show_popup(
            "Denní limit vyčerpán",
            f"Tvůj čas na počítači pro dnešek vypršel.\n\nSystém se vypne za {countdown} sekund.",
            is_error=True
        )
    
    def _handle_schedule_warning(self, data: dict):
        minutes = data.get("minutes_until_end", 0)
        time_text = _pluralize_minutes(minutes)
        self.ui_overlay.show_toast(
            "Blíží se večerka",
            f"Za {time_text} začíná noční klid.",
            "⚠️"
        )
    
    def _handle_schedule_ended(self, data: dict):
        countdown = data.get("countdown_seconds", 60)
        self.ui_overlay.show_countdown(countdown, "Noční klid")
    
    def _handle_outside_schedule(self, data: dict):
        self.ui_overlay.show_popup(
            "Mimo povolený čas",
            "V tuto dobu není povoleno používat počítač.",
            is_error=True
        )
    
    def _handle_startup_notification(self, data: dict):
        self.ui_overlay.show_branded_notification("Monitorování aktivní")
    
    def _handle_take_screenshot(self, data: dict):
        """Take screenshot and save to temp file for service to upload."""
        try:
            self._log("Taking screenshot as requested by backend")
            
            # Create temp directory for screenshots (user-writable)
            import tempfile
            temp_dir = os.path.join(tempfile.gettempdir(), "FamilyEye")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate unique filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            screenshot_path = os.path.join(temp_dir, f"screenshot_{timestamp}.jpg")
            
            # Use PowerShell to capture screen and save directly to file
            # This avoids loading huge base64 into Python memory
            ps_cmd = f'''
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$Screen = [Windows.Forms.Screen]::PrimaryScreen
$Bitmap = New-Object Drawing.Bitmap $Screen.Bounds.Width, $Screen.Bounds.Height
$Graphics = [Drawing.Graphics]::FromImage($Bitmap)
$Graphics.CopyFromScreen($Screen.Bounds.X, $Screen.Bounds.Y, 0, 0, $Bitmap.Size)
$Encoder = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object {{ $_.MimeType -eq 'image/jpeg' }}
$EncoderParams = New-Object Drawing.Imaging.EncoderParameters(1)
$EncoderParams.Param[0] = New-Object Drawing.Imaging.EncoderParameter([Drawing.Imaging.Encoder]::Quality, 75)
$Bitmap.Save('{screenshot_path}', $Encoder, $EncoderParams)
$Graphics.Dispose()
$Bitmap.Dispose()
Write-Output 'OK'
'''
            
            import subprocess
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode == 0 and os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                self._log(f"Screenshot saved to {screenshot_path} ({file_size} bytes)")
                
                # Notify service that screenshot is ready (small IPC message)
                self.ipc_client.send_message(IPCMessage(
                    IPCCommand.SCREENSHOT_READY,
                    {"path": screenshot_path}
                ))
            else:
                self._log(f"Screenshot capture failed: {stderr}", "ERROR")
                
        except subprocess.TimeoutExpired:
            self._log("Screenshot capture timed out", "ERROR")
        except Exception as e:
            self._log(f"Error taking screenshot: {e}", "ERROR")
    
    def _handle_lock_screen(self, data: dict):
        message = data.get("message", "Zařízení bylo zamčeno rodičem.")
        self.ui_overlay.show_lock_screen(message)
    
    def _handle_hide_lock_screen(self, data: dict):
        self.ui_overlay.hide_lock_screen()
    
    def _handle_countdown(self, data: dict):
        seconds = data.get("seconds", 60)
        reason = data.get("reason", "Vypnutí systému")
        self.ui_overlay.show_countdown(seconds, reason)
    
    def _handle_shutdown(self, data: dict):
        self._log("Received shutdown command", "INFO")
        self.stop()
    
    # --- Lifecycle ---
    
    def start(self):
        """Start the child agent."""
        self._log("ChildAgent starting...", "INFO")
        
        if self.running:
            return True
        
        # Initialize UI overlay
        self.ui_overlay = UIOverlay()
        self.ui_overlay.set_log_callback(lambda msg: self._log(msg, "UI"))
        
        # Initialize IPC client
        self.ipc_client = IPCClient(message_handler=self._handle_message)
        self.ipc_client.set_log_callback(lambda msg: self._log(msg, "IPC"))
        
        # Start IPC client
        if not self.ipc_client.start():
            self._log("Failed to start IPC client", "ERROR")
            return False
        
        self.running = True
        self._log("ChildAgent started successfully", "INFO")
        
        # Show startup notification directly (don't wait for service)
        # This ensures notification is always shown when user logs in
        threading.Timer(3.0, self._show_startup_notification).start()
        
        return True
    
    def _show_startup_notification(self):
        """Show branded FamilyEye startup notification."""
        if self.ui_overlay:
            self.ui_overlay.show_branded_notification("Monitorování aktivní")
    
    def stop(self):
        """Stop the child agent."""
        self._log("ChildAgent stopping...", "INFO")
        
        self.running = False
        
        if self.ipc_client:
            self.ipc_client.stop()
        
        if self.ui_overlay:
            self.ui_overlay.hide_lock_screen()
        
        self._log("ChildAgent stopped", "INFO")
    
    def run(self):
        """Run the agent (blocking)."""
        if not self.start():
            return
        
        self._log("ChildAgent running - waiting for commands...", "INFO")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._log("Interrupted by user", "WARNING")
        finally:
            self.stop()


def setup_autostart():
    """Setup auto-start via Registry Run key."""
    import winreg
    
    # Get path to this script or executable
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
    else:
        exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "FamilyEyeAgent", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        print(f"Auto-start enabled: {exe_path}")
        return True
    except Exception as e:
        print(f"Failed to setup auto-start: {e}")
        return False


def remove_autostart():
    """Remove auto-start from Registry."""
    import winreg
    
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "FamilyEyeAgent")
        winreg.CloseKey(key)
        print("Auto-start disabled")
        return True
    except FileNotFoundError:
        print("Auto-start was not enabled")
        return True
    except Exception as e:
        print(f"Failed to remove auto-start: {e}")
        return False


def main():
    try:
        # Single Instance Protection
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            # Create a session-unique mutex name
            import getpass
            username = getpass.getuser()
            mutex_name = f"Global\\FamilyEyeChildAgent_{username}"
            
            mutex = kernel32.CreateMutexW(None, False, mutex_name)
            if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
                print("ChildAgent is already running for this user.")
                return
        except Exception:
            pass

        parser = argparse.ArgumentParser(description="FamilyEye Child Agent")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")
        parser.add_argument("--install", action="store_true", help="Setup auto-start")
        parser.add_argument("--uninstall", action="store_true", help="Remove auto-start")
        
        args = parser.parse_args()
        
        if args.install:
            setup_autostart()
            return
        
        if args.uninstall:
            remove_autostart()
            return
        
        # Run agent
        agent = ChildAgent(debug=args.debug)
        agent.run()
    except Exception as e:
        # Final safety net - show a message box if everything fails
        try:
            import ctypes
            import traceback
            error_msg = f"ChildAgent failed to start:\n\n{str(e)}\n\n{traceback.format_exc()}"
            ctypes.windll.user32.MessageBoxW(0, error_msg, "FamilyEye Agent Error", 0x10)
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
