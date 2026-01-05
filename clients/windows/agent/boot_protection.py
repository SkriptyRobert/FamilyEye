"""Ochrana proti boot do Safe Mode a WinRE."""
import os
import sys
import time
import threading
import subprocess
import winreg
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
        # Log file in parent directory (clients/windows/)
        if getattr(sys, 'frozen', False):
            log_dir = os.path.dirname(sys.executable)
        else:
            log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_file = os.path.join(log_dir, "boot_protection.log")
        
    def log(self, msg, level="INFO"):
        """Zaznamenat událost do logu."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{level}] {msg}\n")
        except:
            pass
    
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
        if not self.backend_url or not self.device_id or not self.api_key:
            self.log(f"Boot event detekován, ale backend není nakonfigurován: {event_type}", "WARNING")
            return
        
        try:
            import requests
            # Zkusit různé možné endpointy
            endpoints = [
                f"{self.backend_url}/api/devices/boot-event",
                f"{self.backend_url}/api/devices/security-event",
                f"{self.backend_url}/api/reports/security"
            ]
            
            event_data = {
                "device_id": self.device_id,
                "api_key": self.api_key,
                "event_type": event_type,
                "timestamp": time.time(),
                "message": f"Boot event detected: {event_type}"
            }
            
            reported = False
            for endpoint in endpoints:
                try:
                    response = requests.post(
                        endpoint,
                        json=event_data,
                        timeout=5
                    )
                    if response.status_code in [200, 201]:
                        self.log(f"Boot event nahlášen na {endpoint}: {event_type}", "INFO")
                        reported = True
                        break
                except:
                    continue
            
            if not reported:
                # Pokud žádný endpoint nefunguje, zkusit použít standardní reporting endpoint
                try:
                    requests.post(
                        f"{self.backend_url}/api/reports/agent/report",
                        json={
                            "device_id": self.device_id,
                            "api_key": self.api_key,
                            "usage_logs": [],
                            "security_events": [{
                                "type": event_type,
                                "timestamp": time.time()
                            }]
                        },
                        timeout=5
                    )
                    self.log(f"Boot event nahlášen přes reporting endpoint: {event_type}", "INFO")
                except Exception as e:
                    self.log(f"Chyba při nahlášení boot eventu: {e}", "ERROR")
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

