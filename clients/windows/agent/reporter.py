"""Usage reporting (batch)."""
import time
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
        self.time_provider = None
        # Offline tracking
        self.offline_since = None  # Timestamp when network went down
        self.cumulative_offline = 0  # Total offline seconds today
        self._needs_immediate_sync = False  # Flag to trigger immediate retry after reconnect
        
        # Report Queue for offline persistence
        self.report_queue: List[Dict] = []
        import threading
        self._queue_lock = threading.Lock()
        self._load_queue_cache()
        
        # Register for reconnection events
        from .api_client import api_client
        api_client.add_on_reconnect_callback(self.trigger_immediate_sync)
        
    def set_time_provider(self, provider):
        """Set trusted time provider function."""
        self.time_provider = provider

    def set_ipc_server(self, ipc_server):
        """Set IPC server for sending commands to ChildAgent."""
        self.ipc_server = ipc_server
    
    def stop(self):
        """Stop reporting."""
        self.send_reports()
    
    def trigger_immediate_sync(self):
        """Callback for reconnection - trigger immediate report."""
        self.logger.info("Reconnection detected - triggering immediate sync")
        self._needs_immediate_sync = True
    
    def send_reports(self):
        """Send usage reports to backend (batch with queue)."""
        if not self.monitor:
            return
        
        # Prevent concurrent access to queue
        if not self._queue_lock.acquire(blocking=False):
            return  # Another send is in progress
            
        try:
            # 1. SNAP current usage from monitor into a new report hunk
            usage_stats = self.monitor.snap_pending_usage()
            running_processes = self.monitor.get_running_processes()
            
            if usage_stats or running_processes:
                from datetime import datetime
                if self.time_provider:
                    batch_timestamp = self.time_provider().isoformat()
                else:
                    batch_timestamp = datetime.utcnow().isoformat()
                
                usage_logs = []
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
                            "timestamp": batch_timestamp
                        })
                
                if usage_logs or running_processes:
                    self.report_queue.append({
                        "usage_logs": usage_logs,
                        "running_processes": running_processes,
                        "timestamp": batch_timestamp
                    })
                    self._save_queue_cache()

            if not self.report_queue:
                return

            self.logger.info(f"Processing report queue: {len(self.report_queue)} hunks pending")
            
            # 2. TRY TO SEND all hunks in queue
            from .api_client import api_client
            
            # Process queue safely - collect indices of successfully sent hunks
            sent_indices = []
            for idx, report_hunk in enumerate(self.report_queue):
                response_data = api_client.send_reports(
                    report_hunk["usage_logs"], 
                    running_processes=report_hunk.get("running_processes")
                )
                
                if response_data is not None:
                    # SUCCESS - mark for removal
                    sent_indices.append(idx)
                    
                    # Track reconnection
                    if self.offline_since:
                        offline_duration = time.time() - self.offline_since
                        self.cumulative_offline += offline_duration
                        self.logger.info(f"Back online after {offline_duration:.0f}s (cached reports sent)")
                        self.offline_since = None
                        self._needs_immediate_sync = True
                    
                    if "commands" in response_data:
                        self._handle_backend_commands(response_data["commands"])
                else:
                    # FAILED - stop processing queue for now
                    if self.offline_since is None:
                        self.offline_since = time.time()
                        self.logger.warning("Network connection lost - reports queued")
                    break
            
            # Remove sent hunks (in reverse order to preserve indices)
            for idx in reversed(sent_indices):
                del self.report_queue[idx]
            
            if sent_indices:
                self._save_queue_cache()

        except Exception as e:
            self.logger.error(f"Unexpected error in reporting flow: {e}")
        finally:
            self._queue_lock.release()


    def _get_queue_path(self):
        import sys
        import os
        if getattr(sys, 'frozen', False):
            program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
            base_dir = os.path.join(program_data, 'FamilyEye', 'Agent')
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, 'report_queue.json')
        else:
            return os.path.join(os.path.dirname(__file__), 'report_queue.json')

    def _save_queue_cache(self):
        try:
            import json
            with open(self._get_queue_path(), 'w') as f:
                json.dump(self.report_queue, f)
        except Exception as e:
            self.logger.error(f"Failed to save report queue: {e}")

    def _load_queue_cache(self):
        try:
            import json
            import os
            cache_path = self._get_queue_path()
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    self.report_queue = json.load(f)
                if self.report_queue:
                    self.logger.info(f"Loaded {len(self.report_queue)} pending reports from cache")
        except Exception as e:
            self.logger.error(f"Failed to load report queue: {e}")

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
            
            # Delete older files beyond max_files
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
