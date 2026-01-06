"""Usage reporting (batch)."""
import time
import requests
from typing import List, Dict
from .config import config
from .monitor import AppMonitor
from .logger import get_logger


class UsageReporter:
    """Batch usage reporter."""
    
    def __init__(self, monitor: AppMonitor = None):
        self.monitor = monitor
        self.last_report = time.time()
        self.logger = get_logger('REPORTER')
        self.ipc_server = None
    
    def set_ipc_server(self, ipc_server):
        """Set IPC server for sending commands to ChildAgent."""
        self.ipc_server = ipc_server
    
    def stop(self):
        """Stop reporting."""
        self.send_reports()
    
    def send_reports(self):
        """Send usage reports to backend (batch)."""
        if not self.monitor:
            self.logger.warning("Monitor not available")
            return
        
        try:
            backend_url = config.get("backend_url")
            device_id = config.get("device_id")
            api_key = config.get("api_key")
            
            if not device_id or not api_key:
                self.logger.error("Missing configuration", device_id=bool(device_id), api_key=bool(api_key))
                return
            
            self.logger.info("Initiating usage report", backend=backend_url, device_id=device_id[:20] + "...")
            
            # Get pending usage (delta since last success)
            usage_logs = []
            usage_stats = self.monitor.get_pending_usage()
            total_apps = len(usage_stats)
            
            # Convert to log format
            from datetime import datetime
            batch_timestamp = datetime.utcnow().isoformat()
            
            for app_name, duration in usage_stats.items():
                duration_seconds = int(round(duration))
                if duration_seconds >= 1:
                    meta = self.monitor.app_metadata.get(app_name, {})
                    usage_logs.append({
                        "app_name": app_name,
                        "window_title": meta.get("title", ""),
                        "exe_path": meta.get("exe", ""),
                        "duration": duration_seconds,
                        "is_focused": meta.get("is_focused", False),
                        "device_id": 0,
                        "timestamp": batch_timestamp
                    })
            
            # Send to backend
            # ... (heartbeat logic or prep info) ...
            
            # Send to backend using centralized client
            from .api_client import api_client
            
            response_data = api_client.send_reports(usage_logs)
            
            if response_data is not None:
                self.logger.success("Usage report sent successfully", logs_sent=len(usage_logs))
                # CRITICAL: Clear ONLY the pending delta after success
                self.monitor.clear_pending_usage()
                
                # Check for commands in response
                if "commands" in response_data:
                    self._handle_backend_commands(response_data["commands"])
            else:
                 # API Client handled logging
                 pass

        
        except Exception as e:
            self.logger.error("Unexpected error during reporting", error=str(e)[:100])

    def _handle_backend_commands(self, commands: List[Dict]):
        """Handle commands from backend response."""
        for cmd in commands:
            cmd_type = cmd.get("type")
            if cmd_type == "screenshot":
                self.logger.info("Backend requested screenshot")
                self._trigger_screenshot()
            elif cmd_type == "message":
                msg = cmd.get("message", "")
                self.logger.info(f"Backend sent message: {msg}")
                if self.ipc_server:
                    from .ipc_common import msg_show_info
                    self.ipc_server.broadcast(msg_show_info("Zpráva od rodiče", msg))

    def _trigger_screenshot(self):
        """Send screenshot request to ChildAgent via IPC."""
        if not self.ipc_server:
            self.logger.error("IPC server not available for screenshot")
            return
        
        from .ipc_common import IPCMessage, IPCCommand
        
        self.logger.debug("Broadcasting TAKE_SCREENSHOT command")
        self.ipc_server.broadcast(IPCMessage(IPCCommand.TAKE_SCREENSHOT))
    
    def handle_screenshot_ready(self, file_path: str):
        """Handle SCREENSHOT_READY from ChildAgent - move to cache and upload."""
        import os
        import shutil
        from datetime import datetime
        
        if not file_path or not os.path.exists(file_path):
            self.logger.error(f"Screenshot file not found: {file_path}")
            return
        
        try:
            # Create local cache directory
            cache_dir = r"C:\ProgramData\FamilyEye\screenshots"
            os.makedirs(cache_dir, exist_ok=True)
            
            # Copy to cache with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            cache_filename = f"screenshot_{timestamp}.jpg"
            cache_path = os.path.join(cache_dir, cache_filename)
            
            shutil.copy2(file_path, cache_path)
            self.logger.info(f"Screenshot cached: {cache_path}")
            
            # Upload to backend
            self.upload_screenshot_from_file(cache_path)
            
            # Cleanup: delete original from temp
            try:
                os.remove(file_path)
            except:
                pass
            
            # Rotate cache: keep last 20 files
            self._rotate_screenshot_cache(cache_dir, max_files=20)
            
        except Exception as e:
            self.logger.error(f"Error handling screenshot: {e}")
    
    def _rotate_screenshot_cache(self, cache_dir: str, max_files: int = 20):
        """Keep only the last N screenshots in cache directory."""
        import os
        import glob
        
        try:
            files = glob.glob(os.path.join(cache_dir, "screenshot_*.jpg"))
            files.sort(key=os.path.getmtime, reverse=True)
            
            # Delete older files beyondmax_files
            for old_file in files[max_files:]:
                try:
                    os.remove(old_file)
                    self.logger.debug(f"Rotated old screenshot: {old_file}")
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Screenshot cache rotation error: {e}")
    
    def upload_screenshot_from_file(self, file_path: str):
        """Upload screenshot from file to backend."""
        import os
        import base64
        
        try:
            backend_url = config.get("backend_url")
            device_id = config.get("device_id")
            api_key = config.get("api_key")
            
            # Read file and encode to base64
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            file_size = os.path.getsize(file_path)
            self.logger.info(f"Uploading screenshot to backend ({file_size} bytes)")
            
            from .api_client import api_client
            success = api_client.upload_screenshot_base64(image_data)
            
            if success:
                self.logger.success("Screenshot uploaded successfully")
            else:
                self.logger.error("Failed to upload screenshot (see network logs)")

        except Exception as e:
            self.logger.error(f"Upload screenshot error: {e}")



