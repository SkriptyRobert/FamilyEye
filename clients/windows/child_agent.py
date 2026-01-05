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

# Fix imports when running as standalone
# Fix paths when running as standalone or frozen
if getattr(sys, 'frozen', False):
    _script_dir = os.path.dirname(sys.executable)
    # Inside _MEIPASS when frozen
    _bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    _agent_dir = os.path.join(_bundle_dir, "agent")
else:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _bundle_dir = _script_dir
    _agent_dir = os.path.join(_script_dir, "agent")

if _bundle_dir not in sys.path:
    sys.path.insert(0, _bundle_dir)

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
        # Log to user-writable directory
        # Note: When spawned by Watchdog from SYSTEM context, env vars may point to wrong paths
        # Use %TEMP% as the most reliable writable location across all contexts
        log_dir = None
        for path in [
            os.environ.get('TEMP'),
            os.environ.get('TMP'),
            os.path.expanduser('~'),
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
        ]:
            if path:
                try:
                    test_dir = os.path.join(path, 'FamilyEye')
                    os.makedirs(test_dir, exist_ok=True)
                    # Test write access
                    test_file = os.path.join(test_dir, '.write_test')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    log_dir = test_dir
                    break
                except (PermissionError, OSError):
                    continue
        
        if log_dir:
            self.log_file = os.path.join(log_dir, "child_agent.log")
        else:
            # Absolute fallback - just don't log to file
            self.log_file = None
        
        # Command handlers
        self._handlers = {}
        self._setup_handlers()
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message to file and optionally console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        
        if self.debug:
            print(log_line)
        
        if not self.log_file:
            return
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except:
            pass
    
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
        
        # Start heartbeat sender thread
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._log("Interrupted by user", "WARNING")
        finally:
            self.stop()
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat to service."""
        HEARTBEAT_INTERVAL = 10  # seconds
        
        while self.running:
            try:
                if self.ipc_client and self.ipc_client.connected:
                    msg = IPCMessage(IPCCommand.HEARTBEAT, {"timestamp": time.time()})
                    self.ipc_client.send_message(msg)
                    self._log("Heartbeat sent", "DEBUG") if self.debug else None
            except Exception as e:
                self._log(f"Heartbeat error: {e}", "ERROR")
            
            time.sleep(HEARTBEAT_INTERVAL)


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
