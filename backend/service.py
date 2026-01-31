"""
Windows Service Wrapper for FamilyEye Server.
Allows the backend to run as a native Windows Service (SYSTEM account).
"""
import sys
import os
import socket

# --- Path Setup for Frozen Environment ---
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    sys.path.insert(0, base_dir)
    sys.path.insert(0, os.path.join(base_dir, "backend"))
    config_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_dir)
    config_dir = base_dir

# --- LOAD ENV (needed for port in --launch-browser-only) ---
from dotenv import load_dotenv
env_path = os.path.join(config_dir, '.env')
load_dotenv(env_path)


def _launch_browser_only():
    """Open dashboard in default browser without loading app. Used by installer/shortcuts."""
    import webbrowser
    import time
    port = os.getenv("BACKEND_PORT", os.getenv("PORT", "8443"))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    if ip.startswith("127."):
        ip = "localhost"
    url = f"https://{ip}:{port}"
    # Short delay so server (if just started by installer) is listening
    time.sleep(1.5)
    try:
        webbrowser.open(url)
    except Exception:
        if os.name == "nt":
            try:
                os.startfile(url)
            except Exception:
                pass
    sys.exit(0)


# --- Handle --launch-browser-only BEFORE any app/win32 imports ---
if len(sys.argv) > 1 and sys.argv[1] == "--launch-browser-only":
    _launch_browser_only()


import time
import threading
import uvicorn
import traceback
import webbrowser
from pathlib import Path

def _load_app(service_mode: bool):
    """
    Import FastAPI app with correct mode flag.
    IMPORTANT: must happen AFTER argv handling so Standalone doesn't inherit service paths.
    """
    if service_mode:
        os.environ["FAMILYEYE_SERVICE_MODE"] = "1"
    else:
        os.environ.pop("FAMILYEYE_SERVICE_MODE", None)

    try:
        from app.main import app as _app
        return _app, None
    except ImportError as e:
        return None, str(e)


# Default: when running as a Windows Service / SCM command, we want service_mode=True.
app, import_error = _load_app(service_mode=True)

# --- Service Logic ---
try:
    import win32serviceutil
    import win32service
    import servicemanager
except ImportError:
    win32serviceutil = None

class FamilyEyeService(win32serviceutil.ServiceFramework if win32serviceutil else object):
    _svc_name_ = "FamilyEyeServer"
    _svc_display_name_ = "FamilyEye Server"
    _svc_description_ = "Backend service for FamilyEye Parental Control."

    def __init__(self, args):
        if not win32serviceutil:
            raise ImportError("pywin32 is required")
        
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = threading.Event()
        self.server = None
        self.server_thread = None
        self.log_file = self._get_log_path()

    def _get_log_path(self):
        """Determine secure log location."""
        # Try ProgramData/FamilyEye/Server/logs (System-wide)
        program_data = os.getenv('ProgramData', 'C:\\ProgramData')
        log_dir = os.path.join(program_data, 'FamilyEye', 'Server', 'logs')
        
        # If directory doesn't exist, we can't create it reliably as SYSTEM without permissions.
        # But installer should have created it. Fallback to temp if needed.
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except:
                log_dir = os.path.join(os.getenv('TEMP', 'C:\\Windows\\Temp'))
        
        return os.path.join(log_dir, 'service.log')

    def log(self, msg):
        """Simple file logger."""
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, "a") as f:
                f.write(f"[{timestamp}] {msg}\n")
        except:
            pass # Last resort: fail silently

    def SvcStop(self):
        """Service Stop Handler."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.log("Service STOP signal received.")
        self.stop_event.set()
        
        if self.server:
            self.server.should_exit = True
            
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        self.log("Service stopped.")

    def SvcDoRun(self):
        """Service Start Handler."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        self.log("Service STARTING...")
        
        if not app:
            self.log(f"FATAL: Could not load application. Error: {import_error}")
            return

        # Start Uvicorn in a thread
        self.server_thread = threading.Thread(target=self.run_uvicorn)
        self.server_thread.start()
        
        self.log("Service started successfully.")
        
        # Keep main thread alive until stop signal
        while not self.stop_event.is_set():
            if not self.server_thread.is_alive():
                self.log("CRITICAL: Uvicorn thread died unexpectedly.")
                self.stop_event.set()
                break
            self.stop_event.wait(1)

    def run_uvicorn(self):
        """Run Uvicorn Server."""
        try:
            # Env is already loaded at module level
            
            # Read config from environment (set by installer or .env)
            host = os.getenv('BACKEND_HOST', '0.0.0.0')
            port = int(os.getenv('BACKEND_PORT', '8000'))
            
            self.log(f"Configuring Uvicorn on {host}:{port} (Env: {env_path})")
            
            # --- SSL CONFIGURATION ---
            ssl_keyfile = None
            ssl_certfile = None
            try:
                # Import ssl_manager relative to our position
                from app import ssl_manager
                
                # Check/Generate certs
                if not ssl_manager.certificates_exist():
                    self.log("Certificates missing, generating...")
                    ssl_manager.generate_certificates()
                
                if ssl_manager.certificates_exist():
                     ssl_certfile = str(ssl_manager.SERVER_CERT_FILE)
                     ssl_keyfile = str(ssl_manager.SERVER_KEY_FILE)
                     self.log(f"SSL Enabled. Cert: {ssl_certfile}")
                else:
                     self.log("SSL Failed to initialize. Falling back to HTTP.")
            except Exception as e:
                self.log(f"SSL Setup Error: {e}")
            
            # Use Config object to control lifecycle
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_level="info",
                loop="asyncio",
                # SSL
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
                # Disable standard Uvicorn loggers that might try to print to stdout/stderr
                # We rely on our own file logger for wrapper, and file logging for app
                use_colors=False, # Disable colors (prevents isatty check)
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            self.log(f"Uvicorn Exception: {e}")
            self.log(traceback.format_exc())

if __name__ == '__main__':
    # Ensure certs exist (used by installer before certutil)
    if len(sys.argv) > 1 and sys.argv[1] == "--ensure-certs":
        try:
            app, import_error = _load_app(service_mode=True)
            from app import ssl_manager
            ssl_manager.ensure_certs_dir()
            if not ssl_manager.certificates_exist():
                ssl_manager.generate_certificates()
            sys.exit(0 if ssl_manager.certificates_exist() else 2)
        except Exception:
            sys.exit(2)

    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FamilyEyeService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FamilyEyeService)
