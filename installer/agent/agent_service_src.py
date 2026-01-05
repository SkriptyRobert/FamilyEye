"""
Windows Service wrapper for Parental Control Agent.
This file gets compiled to agent_service.exe by PyInstaller.
"""
import sys
import os
import time
import logging

# Add agent directory to path
script_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
agent_path = os.path.join(script_dir, 'agent')
if agent_path not in sys.path:
    sys.path.insert(0, agent_path)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Setup logging
log_file = os.path.join(script_dir, 'agent_service.log')
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
            from agent.main import ParentalControlAgent
            self.agent = ParentalControlAgent()
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
