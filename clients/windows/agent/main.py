"""Main agent module.

Session 0 Service Architecture:
- This agent runs as Windows Service in Session 0
- All UI notifications are sent via IPC to ChildAgent
- ChildAgent runs in user session and displays actual UI
- HeartbeatMonitor tracks ChildAgent activity for kill protection
"""
import os
import sys
import time
import threading
import subprocess
import psutil
from .config import config
from .monitor import AppMonitor
from .enforcer import RuleEnforcer
from .reporter import UsageReporter
from .logger import get_logger

# Import boot protection
try:
    from .boot_protection import BootProtection
    _boot_protection_available = True
except ImportError:
    _boot_protection_available = False
    BootProtection = None

# Import IPC server
try:
    from .ipc_server import IPCServer, get_ipc_server
    _ipc_available = True
except ImportError:
    _ipc_available = False
    IPCServer = None

# Windows API for LockWorkStation
try:
    import ctypes
    _win32_available = True
except ImportError:
    _win32_available = False


from .process_monitor import ProcessMonitor


class ParentalControlAgent:
    """Main agent class.
    
    Runs in Session 0 as Windows Service. Handles:
    - Process monitoring
    - Rule enforcement  
    - Usage reporting
    - IPC server for ChildAgent communication
    - Heartbeat monitoring for ChildAgent (started by Scheduled Task)
    """
    
    def __init__(self):
        self.running = False
        self.logger = get_logger('MAIN')
        self.monitor = AppMonitor()
        self.enforcer = RuleEnforcer()
        self.reporter = UsageReporter(self.monitor)
        
        # Set monitor in enforcer
        self.enforcer.set_monitor(self.monitor)
        
        # Set agent reference in monitor and reporter
        self.monitor.agent = self
        self.reporter.monitor = self.monitor
        
        # Link Trusted Time from Enforcer to Reporter (Anti-Cheat)
        # Reporter needs UTC for database timestamps
        self.reporter.set_time_provider(self.enforcer.get_trusted_utc_datetime)
        
        # Monitor needs Local for daily reset, UTC for cache
        self.monitor.set_time_providers(
            self.enforcer.get_trusted_datetime,
            self.enforcer.get_trusted_utc_datetime
        )
        
        self.monitor_thread = None
        self.enforcer_thread = None
        self.reporter_thread = None
        self.boot_protection = None
        
        # IPC server for Session 0 -> User Session communication
        self.ipc_server = None
        
        # Process monitor for ChildAgent (replaces old watchdog)
        self.process_monitor = None
    
    def start(self):
        """Start agent."""
        self.logger.section("Parental Control Agent - Starting")
        
        if not config.is_configured():
            self.logger.error("Agent not configured")
            self.logger.info("Configuration check", 
                           backend_url=config.get('backend_url'),
                           device_id=config.get('device_id'),
                           api_key_set=bool(config.get('api_key')))
            return False
        
        # Initialize API Client and register auth failure callback
        from .api_client import api_client
        
        self.auth_failed = False
        def on_auth_fail():
            self.auth_failed = True
            self.logger.critical("Auth failure detected - stopping agent")
            self.stop()
            
        api_client.set_auth_failure_callback(on_auth_fail)

        # Validate credentials with backend before starting
        if not self._validate_credentials():
            self.logger.critical("Credentials validation failed - agent will not start")
            self.logger.error("Possible causes:")
            self.logger.error("  1. device_id or api_key are incorrect")
            self.logger.error("  2. Device was deleted from backend")
            self.logger.error("  3. Backend is not available")
            self.logger.error("  4. device_id in config.json does not match database")
            self.logger.info("Solution: Re-pair device using: python windows_agent/pair_device.py")
            return False
        
        self.running = True
        
        # Start IPC server for communication with ChildAgent
        if _ipc_available:
            try:
                self.ipc_server = get_ipc_server()
                self.ipc_server.start()
                self.logger.info("IPC Server started for ChildAgent communication")
                
                # Update notification manager with IPC server
                self.enforcer.notification_manager.set_ipc_server(self.ipc_server)
            except Exception as e:
                self.logger.warning(f"Failed to start IPC server: {e}")
        else:
            self.logger.warning("IPC not available - notifications will use fallback")
        
        # Perform initial monitor update to populate data immediately
        self.logger.info("Performing initial system scan...")
        try:
            self.monitor.update()
        except Exception as e:
            self.logger.warning(f"Initial scan failed: {e}")

        # Start threads
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.enforcer_thread = threading.Thread(target=self._enforcer_loop, daemon=True)
        self.reporter_thread = threading.Thread(target=self._reporter_loop, daemon=True)
        
        self.monitor_thread.start()
        self.enforcer_thread.start()
        self.reporter_thread.start()
        
        # Start boot protection monitor
        if _boot_protection_available and BootProtection:
            try:
                self.boot_protection = BootProtection(
                    backend_url=config.get("backend_url"),
                    device_id=config.get("device_id"),
                    api_key=config.get("api_key")
                )
                self.boot_protection.start()
                self.logger.info("Boot Protection Monitor started")
            except Exception as e:
                self.logger.warning(f"Failed to start Boot Protection: {e}")
        
        # Start ProcessMonitor for ChildAgent (active recovery)
        try:
            self.process_monitor = ProcessMonitor()
            self.process_monitor.start()
            
            # Connect components
            # self.ipc_server.set_heartbeat_callback(self.process_monitor.receive_heartbeat) # ProcessMonitor uses psutil, not heartbeats
            self.ipc_server.set_screenshot_callback(self.reporter.upload_screenshot_from_file)  # Legacy
            self.ipc_server.set_screenshot_ready_callback(self.reporter.handle_screenshot_ready)  # File-based
            self.reporter.set_ipc_server(self.ipc_server)
            
            # Start loops
            self.logger.info("ProcessMonitor started (Active Recovery enabled)")
        except Exception as e:
            self.logger.warning(f"Failed to start ProcessMonitor: {e}")
        
        self.logger.success("Agent started successfully",
                          backend=config.get('backend_url'),
                          device_id=config.get('device_id')[:20] + "...",
                          polling_interval=config.get("polling_interval", 5),
                          reporting_interval=config.get("reporting_interval", 60),
                          ipc_enabled=_ipc_available)
        
        # ETHICAL TRANSPARENCY: Notify user that monitoring is active
        # This message goes via IPC to ChildAgent in user session
        try:
            threading.Timer(8.0, lambda: self.enforcer.notification_manager.show_startup_transparent_notification()).start()
        except Exception as e:
            self.logger.warning(f"Failed to queue startup notification: {e}")

        return True
    
    def _validate_credentials(self) -> bool:
        """Validate device_id and api_key with backend."""
        validate_logger = get_logger('VALIDATE')
        try:
            backend_url = config.get("backend_url")
            device_id = config.get("device_id")
            api_key = config.get("api_key")
            
            if not backend_url or not device_id or not api_key:
                validate_logger.error("Missing credentials in configuration")
                return False
            
            validate_logger.info("Validating credentials with backend", backend=backend_url)
            
            # Use API Client to validate
            from .api_client import api_client
            
            # Check if we triggered 401 during the fetch
            # Note: The callback registered in start() sets self.auth_failed = True
            api_client.fetch_rules()
            
            if hasattr(self, 'auth_failed') and self.auth_failed:
                validate_logger.critical("Invalid credentials - authentication failed")
                return False
                
            validate_logger.success("Credentials check complete (or offline mode)")
            return True

        except Exception as e:
            validate_logger.warning("Error validating credentials - will start anyway",
                                  error_type=type(e).__name__,
                                  error_message=str(e)[:50],
                                  note="May be temporary issue")
            return True
    
    def stop(self):
        """Stop agent."""
        self.logger.info("Stopping agent...")
        self.running = False
        
        # Stop process monitor
        if self.process_monitor:
            try:
                self.process_monitor.stop()
            except:
                pass
            self.process_monitor = None
        
        # Stop IPC server
        if self.ipc_server:
            try:
                self.ipc_server.stop()
            except:
                pass
            self.ipc_server = None
        
        # Stop boot protection
        if self.boot_protection:
            try:
                self.boot_protection.stop()
            except:
                pass
            self.boot_protection = None
        
        self.reporter.stop()
        self.logger.success("Agent stopped")
    
    def run(self):
        """Run agent (blocking)."""
        if not self.start():
            return
        
        try:
            self.logger.info("Agent running - Press Ctrl+C to stop")
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.warning("Interrupted by user")
            self.stop()
    
    def _monitor_loop(self):
        """Monitor loop."""
        monitor_logger = get_logger('MONITOR')
        monitor_logger.info("Monitor loop started")
        while self.running:
            try:
                self.monitor.update()
                interval = config.get("polling_interval", 5)
                time.sleep(interval)
            except Exception as e:
                monitor_logger.error("Monitor error", error_type=type(e).__name__, error_message=str(e)[:50])
                import traceback
                traceback.print_exc()
                time.sleep(5)
    
    def _enforcer_loop(self):
        """Enforcer loop."""
        enforcer_logger = get_logger('ENFORCER')
        enforcer_logger.info("Enforcer loop started")
        while self.running:
            try:
                self.enforcer.update()
                time.sleep(2)  # Check every 2 seconds for faster response
            except Exception as e:
                enforcer_logger.error("Enforcer error", error_type=type(e).__name__, error_message=str(e)[:50])
                import traceback
                traceback.print_exc()
                time.sleep(5)
    
    def _reporter_loop(self):
        """Reporter loop."""
        reporter_logger = get_logger('REPORTER')
        reporter_logger.info("Reporter loop started")
        while self.running:
            try:
                self.reporter.send_reports()
                interval = config.get("reporting_interval", 60)
                reporter_logger.debug("Next report scheduled", interval_seconds=interval)
                time.sleep(interval)
            except Exception as e:
                reporter_logger.error("Reporter error", error_type=type(e).__name__, error_message=str(e)[:50])
                import traceback
                traceback.print_exc()
                time.sleep(60)
