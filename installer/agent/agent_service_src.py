"""
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

# Setup minimal file logging for critical startup errors
# This logger captures errors BEFORE agent logger is initialized.
# After agent starts successfully, all logging goes to service_core.log.
def _setup_wrapper_logging():
    """Setup minimal file logging for critical startup errors.
    
    This logger captures errors BEFORE agent logger is initialized.
    After agent starts successfully, all logging goes to service_core.log.
    """
    program_data = os.environ.get('ProgramData', 'C:\ProgramData')
    log_dir = os.path.join(program_data, 'FamilyEye', 'Agent', 'Logs')
    
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'service_wrapper.log')
        
        # Simple file handler for critical errors only
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)  # Only ERROR and CRITICAL
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        # Setup logger
        logger = logging.getLogger('AgentService')
        logger.setLevel(logging.ERROR)
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    except Exception:
        # If logging setup fails, return None (fallback to Windows Event Log)
        return None

# Setup wrapper logging BEFORE any agent imports
_wrapper_logger = _setup_wrapper_logging()

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    # Don't log - this is expected in dev mode

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
        self.is_running = True
        
        try:
            from agent.main import FamilyEyeAgent
            self.agent = FamilyEyeAgent()
            self.agent.start()
            
            # Agent started successfully - wrapper logging no longer needed
            # All further logging goes to service_core.log via agent logger
            
            # Run main loop
            while self.is_running:
                time.sleep(1)
                
        except Exception as e:
            # Log critical errors that prevent agent from starting
            if _wrapper_logger:
                _wrapper_logger.error(f"CRITICAL: Failed to start agent: {e}")
                import traceback
                _wrapper_logger.error(traceback.format_exc())
            
            # Also log to Windows Event Log
            # (servicemanager.LogMsg will be called in SvcDoRun)
            raise
    
    def stop(self):
        """Stop the agent."""
        # Don't log here - agent has its own logger (service_core.log)
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
            # Log to Windows Event Log (not to file)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            try:
                self.service.start()
            except Exception as e:
                # Log critical errors to Windows Event Log
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_ERROR_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (f"CRITICAL: Failed to start agent: {e}",)
                )
                raise

def run_console():
    """Run agent in console mode (for testing)."""
    print("Starting Parental Control Agent in console mode...")
    print("Press Ctrl+C to stop")
    
    service = ParentalControlAgentService()
    try:
        service.start()
    except KeyboardInterrupt:
        print("\nStopping...")
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
