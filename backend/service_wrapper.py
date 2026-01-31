"""Windows Service wrapper for FastAPI backend."""
import sys
import os
import time
import threading
import uvicorn
from pathlib import Path

# Fix for PyInstaller
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    _script_dir = os.path.dirname(sys.executable)
    sys.path.insert(0, _script_dir)
else:
    # Running as script
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    if _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)
    # Add parent for imports
    _parent = os.path.dirname(_script_dir)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    
    # Add venv site-packages if running from source
    _venv_site = os.path.join(_script_dir, "venv", "Lib", "site-packages")
    if os.path.exists(_venv_site) and _venv_site not in sys.path:
        sys.path.insert(0, _venv_site)

# Import app setup
try:
    from app.main import app
except ImportError:
    # Fallback/Debug
    app = None

class BackendService:
    """Windows Service wrapper for backend."""
    
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.running = False
        self.log_file = os.path.join(_script_dir, "service.log")
        
    def log(self, msg):
        try:
            with open(self.log_file, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except:
            pass
            
    def run_uvicorn(self):
        """Run uvicorn server in this thread."""
        try:
            self.log("Starting Uvicorn...")
            config = uvicorn.Config(
                app, 
                host="0.0.0.0", 
                port=8000, 
                log_level="info",
                workers=1,
                loop="asyncio"
            )
            self.server = uvicorn.Server(config)
            self.server.run()
            self.log("Uvicorn stopped.")
        except Exception as e:
            self.log(f"Uvicorn error: {e}")
            import traceback
            self.log(traceback.format_exc())

    def start(self):
        """Start backend server."""
        self.log("Service Start requested")
        if self.running:
            return True
        
        if not app:
            self.log("FATAL: Could not import app.main")
            return False

        self.server_thread = threading.Thread(target=self.run_uvicorn, daemon=True)
        self.server_thread.start()
        self.running = True
        return True
    
    def stop(self):
        """Stop backend server."""
        self.log("Service Stop requested")
        if self.server:
            self.server.should_exit = True
        self.running = False

# Import win32service modules
try:
    import win32serviceutil
    import win32service
    import servicemanager
    _win32_available = True
except ImportError as e:
    # Log the failure
    try:
        with open(os.path.join(_script_dir, "boot_error.log"), "w") as f:
            f.write(f"ImportError: {e}\n")
    except:
        pass
    _win32_available = False

if _win32_available:
    class BackendServiceWrapper(win32serviceutil.ServiceFramework):
        _svc_name_ = "ParentalControlBackend"
        _svc_display_name_ = "Parental Control Backend Service"
        _svc_description_ = "Backend API server for Parental Control System"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.service = BackendService()
            self.stop_event = threading.Event()
        
        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.service.stop()
            self.stop_event.set()
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        
        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.service.start()
            # Wait for stop signal
            while not self.stop_event.is_set():
                # Check if thread is alive
                if self.service.server_thread and not self.service.server_thread.is_alive():
                    self.service.log("Thread died unexpectedly")
                    break
                self.stop_event.wait(1)

if __name__ == "__main__":
    if not _win32_available:
        print("pywin32 is required")
        sys.exit(1)
    
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(BackendServiceWrapper)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(BackendServiceWrapper)


