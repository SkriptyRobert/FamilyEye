"""Window visibility and focus detection logic."""
import time
import ctypes
import psutil
from typing import Dict, Optional, Tuple
from ..logger import get_logger

class WindowDetector:
    """Handles window enumeration, visibility checks, and focus detection."""
    
    def __init__(self, process_tracker, config):
        self.logger = get_logger("monitor.window")
        self.process_tracker = process_tracker
        self.config = config
        
        self.pid_titles: Dict[int, str] = {}
        self._window_cache_time = 0.0
        self._window_cache_data = {}
        
    def get_pids_with_visible_windows(self) -> Dict[int, str]:
        """Return a mapping of PIDs to their main window title. (Cached)"""
        try:
            current_time = time.monotonic()
            
            # Check cache (default 500ms)
            cache_ms = self.config.get("window_enum_cache_ms", 500)
            if (current_time - self._window_cache_time) * 1000 < cache_ms:
                return self._window_cache_data
                
            import win32gui
            import win32process
            import win32con

            pid_to_title = {}

            def enum_handler(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd):
                    # Check window style to filter out tooltips/hidden windows
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    if style & win32con.WS_VISIBLE:
                        # Check for 0x0 size windows (Ghosts)
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            if width * height <= 0:
                                return # Skip ghost windows
                        except Exception:
                            pass # If we can't get rect, fall back to title check

                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            # Only keep the first (usually main) title found for a PID
                            if pid not in pid_to_title:
                                pid_to_title[pid] = title
            
            win32gui.EnumWindows(enum_handler, None)
            
            # Update cache
            self._window_cache_time = current_time
            self._window_cache_data = pid_to_title
            
            return pid_to_title
            
        except Exception as e:
            self.logger.error(f"Error enumerating windows: {e}")
            return {}
            
    def is_real_window(self, hwnd) -> bool:
        """
        Validate if a window is truly a user-facing 'active' window.
        Filters out:
        - Invisible windows
        - Minimized (Iconic) windows
        - Cloaked windows (UWP background processes/suspended apps)
        """
        try:
            import win32gui
            
            # 1. Basic Visibility
            if not win32gui.IsWindowVisible(hwnd):
                return False
                
            # 2. Minimized Check (Iconic)
            if win32gui.IsIconic(hwnd):
                return False
                
            # 3. DWM Cloaked Check (Windows 8+)
            try:
                cloaked = ctypes.c_int(0)
                dwmapi = ctypes.windll.dwmapi
                # DWMWA_CLOAKED = 14
                if dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0:
                    if cloaked.value != 0:
                        return False
            except Exception:
                pass 

            return True
        except Exception:
            return False
            
    def get_active_window_app(self) -> Optional[str]:
        """Get application name of currently active window (Focus)."""
        try:
            import win32gui
            import win32process
            
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return None

            # Strict Validation
            if not self.is_real_window(hwnd):
                return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                app_name = self.process_tracker.get_app_name(proc)
                
                # Check if ignored
                if app_name and self.process_tracker.is_ignored(app_name):
                    return None
                    
                return app_name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None
        except Exception:
            return None
