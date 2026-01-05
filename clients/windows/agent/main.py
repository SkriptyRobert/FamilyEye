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
import requests
import psutil
from .config import config
from .monitor import AppMonitor
from .enforcer import RuleEnforcer
from .reporter import UsageReporter
from .logger import get_logger
import urllib3

# Suppress SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


class ProcessMonitor:
    """Monitors FamilyEyeAgent.exe in user session using psutil.
    
    Active polling every 5s.
    If User Session is active AND Agent IS NOT running -> Restart it.
    """
    
    CHECK_INTERVAL = 5  # seconds
    KILL_COUNT_WINDOW = 3600  # 1 hour
    MAX_KILLS_BEFORE_ACTION = 3
    RESPAWN_COOLDOWN = 5
    
    def __init__(self):
        self.logger = get_logger('PROCESS_MON')
        self.running = False
        self._thread = None
        self.kill_count = 0
        self.kill_timestamps = []
        self.last_respawn_time = 0
        
    def _check_process_state(self):
        """Active check if FamilyEyeAgent is running in the active user session."""
        try:
            current_time = time.time()
            
            # Clean old kill timestamps
            self.kill_timestamps = [t for t in self.kill_timestamps 
                                    if current_time - t < self.KILL_COUNT_WINDOW]
            
            # 1. Get Active Console Session
            # We need ctypes for this as psutil doesn't give "Active Console" easily
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            session_id = kernel32.WTSGetActiveConsoleSessionId()
            
            if session_id == 0xFFFFFFFF or session_id == 0:
                # No active user session (0 is Service Session)
                return
            
            # 2. Check if FamilyEyeAgent.exe is running in that session
            agent_running = False
            # 2. Check if FamilyEyeAgent.exe is running in that session
            agent_running = False
            
            # Use ctypes for session ID check as psutil can be unreliable for this attr
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            
            for proc in psutil.process_iter():
                try:
                    if proc.name() in ('FamilyEyeAgent.exe', 'ChildAgent.exe'):
                        pid = proc.pid
                        proc_session_id = ctypes.c_ulong()
                        if kernel32.ProcessIdToSessionId(pid, ctypes.byref(proc_session_id)):
                            if proc_session_id.value == session_id:
                                agent_running = True
                                break
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            if not agent_running:
                # Agent is missing in active user session!
                self.logger.warning(f"FamilyEyeAgent missing in Session {session_id} - attempting restart")
                self._handle_agent_missing(session_id)
                
        except Exception as e:
            self.logger.error(f"Process check error: {e}")

    def _handle_agent_missing(self, session_id):
        """Handle missing agent - restart and track kills."""
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_respawn_time < self.RESPAWN_COOLDOWN:
            return
            
        self.last_respawn_time = current_time
        
        # Count this as a kill/crash
        self.kill_timestamps.append(current_time)
        self.kill_count = len(self.kill_timestamps)
        
        self.logger.warning(f"Restoring Agent... (Event #{self.kill_count}/{self.MAX_KILLS_BEFORE_ACTION})")
        
        # Restart
        if self._restart_child_agent():
            self.logger.info("Restart successful")
        else:
            self.logger.error("Restart failed")

        # Discipline if too many kills
        if self.kill_count >= self.MAX_KILLS_BEFORE_ACTION:
            self.logger.critical("Max kill limits reached - Locking Workstation")
            self._take_disciplinary_action()
            
    def _restart_child_agent(self) -> bool:
        """Restart FamilyEyeAgent using CreateProcessAsUser."""
        try:
            # Find executable
            if getattr(sys, 'frozen', False):
                install_dir = os.path.dirname(sys.executable)
            else:
                install_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            agent_exe = None
            for name in ["FamilyEyeAgent.exe", "ChildAgent.exe"]:
                path = os.path.join(install_dir, name)
                if os.path.exists(path):
                    agent_exe = path
                    break
            
            if not agent_exe:
                self.logger.error("FamilyEyeAgent.exe not found")
                return False

            return self._create_process_in_user_session(agent_exe)
            
        except Exception as e:
            self.logger.error(f"Restart exception: {e}")
            return False

    def _create_process_in_user_session(self, exe_path: str) -> bool:
        """Launch process in active user session using WinAPI."""
        try:
            from ctypes import wintypes
            
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
            wtsapi32 = ctypes.WinDLL('wtsapi32', use_last_error=True)
            userenv = ctypes.WinDLL('userenv', use_last_error=True)
            
            # Constants
            TOKEN_DUPLICATE = 0x0002
            TOKEN_QUERY = 0x0008
            TOKEN_ASSIGN_PRIMARY = 0x0001
            TOKEN_ALL_ACCESS = 0xF01FF
            SecurityIdentification = 2
            TokenPrimary = 1
            CREATE_UNICODE_ENVIRONMENT = 0x00000400
            
            # 1. Get Session
            session_id = kernel32.WTSGetActiveConsoleSessionId()
            if session_id == 0xFFFFFFFF: return False
            
            # 2. Get User Token
            user_token = wintypes.HANDLE()
            if not wtsapi32.WTSQueryUserToken(session_id, ctypes.byref(user_token)):
                self.logger.error(f"WTSQueryUserToken failed: {ctypes.get_last_error()}")
                return False
                
            try:
                # 3. Duplicate Token
                duplicated_token = wintypes.HANDLE()
                if not advapi32.DuplicateTokenEx(
                    user_token, TOKEN_ALL_ACCESS, None, SecurityIdentification, 
                    TokenPrimary, ctypes.byref(duplicated_token)
                ):
                    self.logger.error(f"DuplicateTokenEx failed: {ctypes.get_last_error()}")
                    return False
                
                try:
                    # 4. Create Environment
                    env_block = ctypes.c_void_p()
                    if not userenv.CreateEnvironmentBlock(ctypes.byref(env_block), duplicated_token, False):
                        self.logger.warning("CreateEnvironmentBlock failed, using NULL")
                        env_block = None
                    
                    try:
                        # 5. Startup Info
                        class STARTUPINFOW(ctypes.Structure):
                            _fields_ = [
                                ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                                ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                                ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                                ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
                                ("hStdError", wintypes.HANDLE),
                            ]
                        
                        startup_info = STARTUPINFOW()
                        startup_info.cb = ctypes.sizeof(STARTUPINFOW)
                        startup_info.lpDesktop = "winsta0\\default"
                        
                        class PROCESS_INFORMATION(ctypes.Structure):
                            _fields_ = [
                                ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
                            ]
                        process_info = PROCESS_INFORMATION()
                        
                        # 6. CreateProcessAsUser
                        # IMPORTANT: env_block is already a pointer (c_void_p), pass it directly
                        success = advapi32.CreateProcessAsUserW(
                            duplicated_token, exe_path, None, None, None, False,
                            CREATE_UNICODE_ENVIRONMENT, env_block,
                            os.path.dirname(exe_path),
                            ctypes.byref(startup_info), ctypes.byref(process_info)
                        )
                        
                        if success:
                            self.logger.info(f"Process launched! PID: {process_info.dwProcessId}")
                            kernel32.CloseHandle(process_info.hProcess)
                            kernel32.CloseHandle(process_info.hThread)
                            return True
                        else:
                            self.logger.error(f"CreateProcessAsUserW failed: {ctypes.get_last_error()}")
                            return False
                            
                    finally:
                        if env_block:
                            userenv.DestroyEnvironmentBlock(env_block)
                finally:
                    kernel32.CloseHandle(duplicated_token)
            finally:
                kernel32.CloseHandle(user_token)
                
        except Exception as e:
            self.logger.error(f"Detailed launch error: {e}")
            return False

    def _take_disciplinary_action(self):
        try:
            ctypes.windll.user32.LockWorkStation()
        except:
            pass
        self.kill_timestamps = []
        self.kill_count = 0
    
    def _monitor_loop(self):
        self.logger.info("ProcessMonitor started")
        while self.running:
            try:
                self._check_process_state()
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
            time.sleep(self.CHECK_INTERVAL)
        self.logger.info("ProcessMonitor stopped")
    
    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)


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
        
        # Set agent reference in monitor and reporter for stopping on 401
        self.monitor.agent = self
        self.reporter.monitor = self.monitor
        
        self.monitor_thread = None
        self.enforcer_thread = None
        self.reporter_thread = None
        self.boot_protection = None
        
        # IPC server for Session 0 -> User Session communication
        self.ipc_server = None
        
        # Heartbeat monitor for ChildAgent (replaces old watchdog)
        self.heartbeat_monitor = None
    
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
            self.heartbeat_monitor = ProcessMonitor()
            self.heartbeat_monitor.start()
            
            # Connect components
            # self.ipc_server.set_heartbeat_callback(self.heartbeat_monitor.receive_heartbeat) # ProcessMonitor uses psutil, not heartbeats
            self.ipc_server.set_screenshot_callback(self.reporter.upload_screenshot_from_file)  # Legacy
            self.ipc_server.set_screenshot_ready_callback(self.reporter.handle_screenshot_ready)  # File-based
            self.reporter.set_ipc_server(self.ipc_server)
            
            # Start loops
            self.logger.info("ProcessMonitor started (Active Recovery enabled)")
        except Exception as e:
            self.logger.warning(f"Failed to start HeartbeatMonitor: {e}")
        
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
            
            # Try to fetch rules - this will validate credentials
            start_time = time.time()
            response = requests.post(
                f"{backend_url}/api/rules/agent/fetch",
                json={"device_id": device_id, "api_key": api_key},
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000  # ms
            
            if response.status_code == 200:
                validate_logger.success("Credentials validated successfully",
                                      device_id=device_id[:20] + "...",
                                      response_time_ms=f"{response_time:.0f}ms")
                return True
            elif response.status_code == 401:
                validate_logger.critical("Invalid credentials - authentication failed",
                                       device_id=device_id[:20] + "...",
                                       status_code=401)
                return False
            else:
                validate_logger.warning("Backend returned unexpected status",
                                      status_code=response.status_code,
                                      response_preview=response.text[:100])
                # Don't fail on other errors - might be temporary network issue
                return True
                
        except requests.exceptions.ConnectionError:
            validate_logger.warning("Cannot connect to backend - will start anyway",
                                  backend=backend_url,
                                  note="May be temporary network issue")
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
        
        # Stop watchdog
        if self.watchdog:
            try:
                self.watchdog.stop()
            except:
                pass
            self.watchdog = None
        
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
