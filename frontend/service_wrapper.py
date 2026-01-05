"""Windows Service wrapper for Frontend Dashboard (serves built files)."""
import sys
import os
import threading
import time
from pathlib import Path

# Get the directory where this script is located
_script_dir = os.path.dirname(os.path.abspath(__file__))

# Add current directory to path - CRITICAL for pythonservice.exe
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# Add parent directory
_parent_dir = os.path.dirname(_script_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Try to find backend venv and use it if system one lacks modules
# Path from frontend/ to backend/venv: ../backend/venv
_backend_venv_site = os.path.normpath(os.path.join(_script_dir, "..", "backend", "venv", "Lib", "site-packages"))
if os.path.exists(_backend_venv_site) and _backend_venv_site not in sys.path:
    # Append to end to prefer system packages if present, or insert 0? 
    # Usually we want the venv to override if we are running from it, but here we run from system python.
    # Let's insert at 1 (after script dir) to prioritize it if system lacks stuff.
    sys.path.insert(1, _backend_venv_site)

# Include current directory (frontend) venv if it exists (future proofing)
_local_venv_site = os.path.join(_script_dir, "venv", "Lib", "site-packages")
if os.path.exists(_local_venv_site) and _local_venv_site not in sys.path:
    sys.path.insert(0, _local_venv_site)

# Try to use http.server (Python 3.x built-in)
try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler
except ImportError:
    # Fallback for older Python
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler as SimpleHTTPRequestHandler

class FrontendService:
    """Windows Service wrapper for frontend (serves built files)."""
    
    def __init__(self, port=3000):
        self.port = port
        self.server = None
        self.running = False
        self.script_dir = Path(_script_dir) # Use absolute path
        self.dist_dir = self.script_dir / "dist"
        
    def log(self, msg):
        try:
            with open(self.script_dir / "service_frontend.log", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except:
            pass

    def start(self):
        """Start frontend server."""
        self.log("Starting frontend service...")
        if self.running:
            self.log("Already running.")
            return True
        
        # Check if dist directory exists
        if not self.dist_dir.exists():
            self.log(f"ERROR: Frontend build not found at {self.dist_dir}")
            return False
        
        try:
            # Change to dist directory
            os.chdir(str(self.dist_dir))
            
            # Create HTTP server
            handler = SimpleHTTPRequestHandler
            self.server = HTTPServer(("0.0.0.0", self.port), handler)
            
            # Start server in separate thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.running = True
            
            self.log(f"Frontend server started on port {self.port}")
            self.log(f"Serving directory: {self.dist_dir}")
            return True
        except Exception as e:
            self.log(f"Error starting frontend server: {e}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def stop(self):
        """Stop frontend server."""
        self.log("Stopping frontend service...")
        if self.server:
            self.server.shutdown()
            self.server = None
        self.running = False

# Import win32service modules
try:
    import win32serviceutil
    import win32service
    import servicemanager
    _win32_available = True
except ImportError as e:
    # Log failure
    try:
        with open(os.path.join(_script_dir, "boot_error_frontend.log"), "w") as f:
            f.write(f"ImportError during boot: {e}\n")
            f.write(f"sys.path: {sys.path}\n")
    except:
        pass
    win32serviceutil = None
    win32service = None
    servicemanager = None
    _win32_available = False

if _win32_available:
    class FrontendServiceWrapper(win32serviceutil.ServiceFramework):
        _svc_name_ = "ParentalControlFrontend"
        _svc_display_name_ = "Parental Control Frontend Service"
        _svc_description_ = "Web dashboard server for Parental Control System"
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.service = FrontendService(port=3000)
            self.stop_event = threading.Event()
        
        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.service.stop()
            self.stop_event.set()
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        
        def SvcDoRun(self):
            self.service.log("SvcDoRun called")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            if self.service.start():
                self.stop_event.wait()
                self.service.log("Stop event received")
            else:
                self.service.log("Service start returned False")
                servicemanager.LogErrorMsg("Failed to start frontend service")

if __name__ == "__main__":
    if not _win32_available:
        print("pywin32 is required for Windows Service support")
        print("Install with: pip install pywin32")
        sys.exit(1)
    
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FrontendServiceWrapper)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FrontendServiceWrapper)
