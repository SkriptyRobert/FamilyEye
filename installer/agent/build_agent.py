"""
PyInstaller build script for Parental Control Agent.
Creates a standalone Windows executable with all dependencies.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CLIENTS_DIR = PROJECT_ROOT / "clients" / "windows"
AGENT_DIR = CLIENTS_DIR / "agent"
INSTALLER_DIR = PROJECT_ROOT / "installer" / "agent"
OUTPUT_DIR = INSTALLER_DIR / "dist"

def clean_build():
    """Clean previous build artifacts and stop running processes."""
    print("Stopping running agent processes...")
    try:
        # Try to stop service if it exists/runs
        subprocess.run(["net", "stop", "FamilyEyeAgent"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # Kill any zombie processes
        subprocess.run(["taskkill", "/F", "/IM", "agent_service.exe", "/IM", "FamilyEyeAgent.exe", "/T"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass

    for folder in ["build", "dist", "dist_debug", "__pycache__"]:
        path = INSTALLER_DIR / folder
        if path.exists():
            try:
                shutil.rmtree(path)
            except Exception as e:
                print(f"Warning: Could not remove {folder}: {e}")
    
    for spec in ["agent_service.spec", "FamilyEyeAgent.spec", "ChildAgent.spec"]:
        spec_file = INSTALLER_DIR / spec
        if spec_file.exists():
            spec_file.unlink()

def create_service_wrapper():
    """Create the service wrapper script that will be compiled."""
    wrapper_content = '''"""
Windows Service wrapper for Parental Control Agent.
This file gets compiled to agent_service.exe by PyInstaller.
"""
import sys
import os
import time
import logging

# Add agent directory to path
if getattr(sys, 'frozen', False):
    bundle_dir = os.path.dirname(sys.executable)
    agent_path = os.path.join(bundle_dir, 'agent')
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    agent_path = os.path.join(bundle_dir, 'agent')

if agent_path not in sys.path:
    sys.path.insert(0, agent_path)
if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

# Setup logging to ProgramData
program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
log_dir = os.path.join(program_data, 'FamilyEye', 'Agent', 'Logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir, exist_ok=True)
    except:
        pass
        
log_file = os.path.join(log_dir, 'service_wrapper.log')

# Fallback to local dir if ProgramData fails
try:
    with open(log_file, 'a') as f: pass
except:
    log_file = os.path.join(script_dir, 'service_wrapper.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentService')

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("win32service not available, running in console mode")

class ParentalControlAgentService:
    """Windows Service for Parental Control Agent."""
    
    _svc_name_ = 'FamilyEyeAgent'
    _svc_display_name_ = 'FamilyEye Agent'
    _svc_description_ = 'Monitorování a ochrana FamilyEye'
    
    def __init__(self):
        self.is_running = False
        self.agent = None
    
    def start(self):
        """Start the agent."""
        logger.info("Starting Parental Control Agent Service...")
        self.is_running = True
        
        try:
            from agent.main import FamilyEyeAgent
            self.agent = FamilyEyeAgent()
            self.agent.start()
            
            # Run main loop
            while self.is_running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in agent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def stop(self):
        """Stop the agent."""
        logger.info("Stopping Parental Control Agent Service...")
        self.is_running = False
        if self.agent:
            self.agent.stop()

if HAS_WIN32:
    class WindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = ParentalControlAgentService._svc_name_
        _svc_display_name_ = ParentalControlAgentService._svc_display_name_
        _svc_description_ = ParentalControlAgentService._svc_description_
        
        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.service = ParentalControlAgentService()
        
        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.service.stop()
            win32event.SetEvent(self.stop_event)
        
        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.service.start()

def run_console():
    """Run agent in console mode (for testing)."""
    print("Starting Parental Control Agent in console mode...")
    print("Press Ctrl+C to stop")
    
    service = ParentalControlAgentService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\\nStopping...")
        service.stop()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--console':
            run_console()
        elif HAS_WIN32:
            win32serviceutil.HandleCommandLine(WindowsService)
        else:
            print("Windows service support not available")
            run_console()
    else:
        if HAS_WIN32:
            try:
                servicemanager.Initialize()
                servicemanager.PrepareToHostSingle(WindowsService)
                servicemanager.StartServiceCtrlDispatcher()
            except Exception as e:
                # Not running as service, run in console mode
                run_console()
        else:
            run_console()

if __name__ == '__main__':
    main()
'''
    wrapper_path = INSTALLER_DIR / "agent_service_src.py"
    with open(wrapper_path, 'w', encoding='utf-8') as f:
        f.write(wrapper_content)
    return wrapper_path

def build_executable():
    """Build the executable using PyInstaller."""
    wrapper_path = create_service_wrapper()
    
    # Check for icon
    icon_path = INSTALLER_DIR / 'assets' / 'agent_icon.ico'
    
    # PyInstaller command - build arguments list properly
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--onefile',
        '--name', 'agent_service',
        '--distpath', str(OUTPUT_DIR),
        '--workpath', str(INSTALLER_DIR / 'build'),
        '--specpath', str(INSTALLER_DIR),
        # Win32 service modules
        '--hidden-import', 'win32timezone',
        '--hidden-import', 'win32serviceutil',
        '--hidden-import', 'win32service',
        '--hidden-import', 'win32event',
        '--hidden-import', 'servicemanager',
        # Core modules
        '--hidden-import', 'psutil',
        '--hidden-import', 'requests',
        '--hidden-import', 'urllib3',
        '--hidden-import', 'colorama',
        '--hidden-import', 'websockets',
        # Win32 API for process/session management
        '--hidden-import', 'win32gui',
        '--hidden-import', 'win32process',
        '--hidden-import', 'win32con',
        '--hidden-import', 'win32api',
        '--hidden-import', 'win32security',
        '--hidden-import', 'win32ts',
        # IPC modules (Named Pipes)
        '--hidden-import', 'win32pipe',
        '--hidden-import', 'win32file',
        '--hidden-import', 'pywintypes',
        '--hidden-import', 'winerror',
        '--hidden-import', 'ntsecuritycon',
        # Search paths
        '--paths', str(CLIENTS_DIR),
        # Agent IPC modules
        '--hidden-import', 'agent',
        '--hidden-import', 'agent.main',
        '--hidden-import', 'agent.ipc_common',
        '--hidden-import', 'agent.ipc_server',
        '--hidden-import', 'agent.ipc_client',
        '--hidden-import', 'agent.ui_overlay',
        '--hidden-import', 'agent.notifications',
        '--hidden-import', 'agent.logger',
        '--hidden-import', 'agent.config',
        '--add-data', f'{AGENT_DIR}{os.pathsep}agent',
        '--uac-admin',
    ]
    
    # Add icon only if exists
    if icon_path.exists():
        cmd.extend(['--icon', str(icon_path)])
    
    # Add source file
    cmd.append(str(wrapper_path))
    
    print("Building agent_service.exe with PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=str(INSTALLER_DIR))
    
    if result.returncode == 0:
        print(f"\n[SUCCESS] agent_service.exe build successful!")
        print(f"Output: {OUTPUT_DIR / 'agent_service.exe'}")
    else:
        print(f"\n[ERROR] Build failed with code {result.returncode}")
        sys.exit(1)


def build_child_agent():
    """Build FamilyEyeAgent executable for user session (formerly ChildAgent)."""
    child_agent_path = CLIENTS_DIR / "child_agent.py"
    
    if not child_agent_path.exists():
        print(f"[WARNING] ChildAgent source not found at {child_agent_path}, skipping...")
        return
    
    # Check for icon - prefer eye icon for user-facing agent
    icon_path = INSTALLER_DIR / 'assets' / 'setup_icon.ico'
    agent_icon_path = INSTALLER_DIR / 'assets' / 'agent_icon.ico'
    
    # Use agent_icon if available, otherwise setup_icon
    if agent_icon_path.exists():
        icon_path = agent_icon_path
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', 'FamilyEyeAgent',  # Renamed from ChildAgent
        '--distpath', str(OUTPUT_DIR),
        '--workpath', str(INSTALLER_DIR / 'build'),
        '--specpath', str(INSTALLER_DIR),
        '--noconsole',  # No console window for child agent
        # Core modules
        '--hidden-import', 'psutil',
        # Win32 API for Named Pipes
        '--hidden-import', 'win32pipe',
        '--hidden-import', 'win32file',
        '--hidden-import', 'pywintypes',
        '--hidden-import', 'winerror',
        # Search paths
        '--paths', str(CLIENTS_DIR),
        # Agent IPC modules
        '--hidden-import', 'agent',
        '--hidden-import', 'agent.ipc_common',
        '--hidden-import', 'agent.ipc_client',
        '--hidden-import', 'agent.ui_overlay',
        '--add-data', f'{AGENT_DIR}{os.pathsep}agent',
    ]
    
    # Add icon only if exists
    if icon_path.exists():
        cmd.extend(['--icon', str(icon_path)])
        print(f"Using icon: {icon_path}")
    
    # Add source file
    cmd.append(str(child_agent_path))
    
    print("\nBuilding FamilyEyeAgent.exe with PyInstaller...")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=str(INSTALLER_DIR))
    
    if result.returncode == 0:
        print(f"\n[SUCCESS] FamilyEyeAgent.exe build successful!")
        print(f"Output: {OUTPUT_DIR / 'FamilyEyeAgent.exe'}")
    else:
        print(f"\n[ERROR] ChildAgent build failed with code {result.returncode}")
        sys.exit(1)


def main():
    print("=" * 60)
    print("Parental Control Agent - Build Script v2.0 (IPC Edition)")
    print("=" * 60)
    
    # Check requirements
    try:
        import PyInstaller
        print(f"[OK] PyInstaller found: {PyInstaller.__version__}")
    except ImportError:
        print("[ERROR] PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
    
    try:
        import pywin32_bootstrap
    except ImportError:
        print("Installing pywin32...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pywin32'])
    
    # Clean and build
    print("\nCleaning previous build...")
    clean_build()
    
    print("\n[1/2] Building agent_service.exe (Windows Service)...")
    build_executable()
    
    print("\n[2/2] Building ChildAgent.exe (User Session UI)...")
    build_child_agent()
    
    print("\n" + "=" * 60)
    print("Build complete!")
    print("Outputs:")
    print(f"  - {OUTPUT_DIR / 'agent_service.exe'}")
    print(f"  - {OUTPUT_DIR / 'FamilyEyeAgent.exe'}")
    print("=" * 60)

if __name__ == '__main__':
    main()

