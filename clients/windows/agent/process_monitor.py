"""Process Monitor Module.

Handles active monitoring and recovery of the child agent process in the user session.
Part of the Session 0 isolation strategy.
"""
import os
import sys
import time
import threading
import ctypes
import psutil
from ctypes import wintypes

from .logger import get_logger

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
