"""Ochrana proti boot do Safe Mode a WinRE."""
import os
import sys
import time
import threading
import subprocess
import winreg
import logging
import logging.handlers
from pathlib import Path

# Fix for PyInstaller
if getattr(sys, 'frozen', False):
    _script_dir = os.path.dirname(sys.executable)
    sys.path.insert(0, _script_dir)
else:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _agent_dir = os.path.dirname(_script_dir)  # agent/
    _windows_dir = os.path.dirname(_agent_dir)  # clients/windows/
    if _windows_dir not in sys.path:
        sys.path.insert(0, _windows_dir)
    if _agent_dir not in sys.path:
        sys.path.insert(0, _agent_dir)

try:
    import win32api
    import win32security
    import win32con
    _win32_available = True
except ImportError:
    _win32_available = False

class BootProtection:
    """Monitoruje a chrání proti boot do Safe Mode a WinRE."""
    
    def __init__(self, backend_url=None, device_id=None, api_key=None):
        self.backend_url = backend_url
        self.device_id = device_id
        self.api_key = api_key
        self.running = False
        self.monitor_thread = None
        
        # Setup logging with rotation
        self.logger = logging.getLogger('FamilyEye.BootProtection')
        
        # Get log level from config or use INFO
        log_level = logging.INFO
        try:
            from .config import config
            level_str = config.get('log_level', 'INFO')
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
            }
            log_level = level_map.get(level_str.upper(), logging.INFO)
        except Exception:
            pass
        
        self.logger.setLevel(log_level)
        
        # Only setup handlers if not already set
        if not self.logger.handlers:
            # Determine log directory
            if getattr(sys, 'frozen', False):
                # Running as compiled exe - use ProgramData
                program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
                log_dir = os.path.join(program_data, 'FamilyEye', 'Agent', 'Logs')
            else:
                # Dev mode
                log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "boot_protection.log")
            
            # Get rotation settings from config
            try:
                from .config import config
                rotation_enabled = config.get('log_rotation_enabled', True)
                rotation_when = config.get('log_rotation_when', 'midnight')
                rotation_backup_count = config.get('log_rotation_backup_count', 5)
            except Exception:
                rotation_enabled = True
                rotation_when = 'midnight'
                rotation_backup_count = 5
            
            # Use TimedRotatingFileHandler if rotation enabled
            if rotation_enabled:
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    log_path,
                    when=rotation_when,
                    backupCount=rotation_backup_count,
                    encoding='utf-8'
                )
            else:
                file_handler = logging.FileHandler(log_path, encoding='utf-8')
            
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
    def log(self, msg, level="INFO"):
        """Zaznamenat událost do logu."""
        level_map = {
            'DEBUG': self.logger.debug,
            'INFO': self.logger.info,
            'WARNING': self.logger.warning,
            'ERROR': self.logger.error,
            'CRITICAL': self.logger.critical,
        }
        log_func = level_map.get(level.upper(), self.logger.info)
        log_func(msg)
    
    def check_safe_mode(self):
        """Zkontrolovat, zda systém běží v Safe Mode."""
        try:
            # Metoda 1: Registry
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\SafeBoot\Option"
                )
                try:
                    value, _ = winreg.QueryValueEx(key, "OptionValue")
                    if value == 1:
                        self.log("KRITICKÉ: Systém běží v Safe Mode!", "CRITICAL")
                        self._report_boot_event("safe_mode")
                        return True
                finally:
                    winreg.CloseKey(key)
            except FileNotFoundError:
                pass
            
            # Metoda 2: Kontrola spuštěných služeb (v Safe Mode je méně služeb)
            try:
                result = subprocess.run(
                    ["sc", "query", "Themes"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # V Safe Mode není služba Themes
                if "STOPPED" in result.stdout or result.returncode != 0:
                    # Může být Safe Mode, ale není to jisté
                    pass
            except:
                pass
            
        except Exception as e:
            self.log(f"Chyba při kontrole Safe Mode: {e}", "ERROR")
        return False
    
    def check_winre(self):
        """Zkontrolovat, zda systém běží v WinRE (Windows Recovery Environment)."""
        try:
            # WinRE má jiný systémový adresář
            system_root = os.environ.get("SystemRoot", "C:\\Windows")
            winre_path = os.path.join(system_root, "System32", "Recovery")
            
            # Pokud běžíme z WinRE, některé soubory budou chybět
            if not os.path.exists(os.path.join(system_root, "System32", "winlogon.exe")):
                self.log("VAROVÁNÍ: Možný boot do WinRE detekován", "WARNING")
                self._report_boot_event("winre")
                return True
        except Exception as e:
            self.log(f"Chyba při kontrole WinRE: {e}", "ERROR")
        return False
    
    def _report_boot_event(self, event_type):
        """Nahlásit boot event na backend."""
        if not self.backend_url:
            # Try to get from config context if possible, or fallback
            from .config import config
            if config.is_configured():
                self.backend_url = config.get("backend_url")
        
        try:
            from .api_client import api_client
            
            event_data = {
                "event_type": event_type,
                "timestamp": time.time(),
                "message": f"Boot event detected: {event_type}"
            }
            
            # Use centralized client
            if api_client.report_security_event(event_data):
                self.log(f"Boot event nahlášen: {event_type}", "INFO")
            else:
                self.log(f"Nepodařilo se nahlásit boot event: {event_type}", "WARNING")
                
        except Exception as e:
            self.log(f"Chyba při nahlášení boot eventu: {e}", "ERROR")
    
    def monitor_loop(self):
        """Hlavní monitorovací smyčka."""
        self.log("Boot Protection Monitor spuštěn", "INFO")
        
        last_safe_mode_check = 0
        last_winre_check = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Kontrola Safe Mode každých 30 sekund
                if current_time - last_safe_mode_check >= 30:
                    self.check_safe_mode()
                    last_safe_mode_check = current_time
                
                # Kontrola WinRE každých 60 sekund
                if current_time - last_winre_check >= 60:
                    self.check_winre()
                    last_winre_check = current_time
                
                time.sleep(10)
                
            except Exception as e:
                self.log(f"Chyba v monitorovací smyčce: {e}", "ERROR")
                time.sleep(30)
    
    def start(self):
        """Spustit monitor."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.log("Boot Protection Monitor spuštěn", "INFO")
    
    def stop(self):
        """Zastavit monitor."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.log("Boot Protection Monitor zastaven", "INFO")

