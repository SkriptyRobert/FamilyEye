"""Centralized API Client for FamilyEye Agent.

Handles all HTTP communication with the backend, including:
- Connection pooling (Session)
- Authentication headers
- SSL verification
- Error handling
- Retry logic with exponential backoff
"""
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import time
from typing import Optional, Any, Dict, List
from .config import config
from .logger import get_logger

# Suppress insecure request warnings if SSL verify is False
import urllib3
if not config.get_ssl_verify():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BackendAPIClient:
    """Thread-safe API client for backend communication."""
    
    def __init__(self):
        self.logger = get_logger('NETWORK')
        self.session = self._create_session()
        self._update_headers()
        self._auth_failure_callback = None
        self._on_reconnect_callbacks = []
        self.is_online = True  # Assume online initially
        
    def set_auth_failure_callback(self, callback):
        """Set callback to be called on 401 Unauthorized (Critical)."""
        self._auth_failure_callback = callback

    def add_on_reconnect_callback(self, callback):
        """Add a callback to be called when connection is restored."""
        if callback not in self._on_reconnect_callbacks:
            self._on_reconnect_callbacks.append(callback)

    def _trigger_reconnect(self):
        """Trigger all registered reconnection callbacks."""
        self.logger.info(f"Triggering {len(self._on_reconnect_callbacks)} reconnection callbacks")
        for callback in self._on_reconnect_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in reconnection callback: {e}")

    def _handle_401(self):
        """Handle 401 Unauthorized response."""
        self.logger.error("Unauthorized: Invalid credentials or device deleted")
        if self._auth_failure_callback:
            try:
                self._auth_failure_callback()
            except Exception as e:
                self.logger.error(f"Error in auth failure callback: {e}")

    def _create_session(self):
        """Create a session with retry logic and connection pooling."""
        session = requests.Session()
        
        # Retry strategy: 3 retries, backoff factor 1 (1s, 2s, 4s...)
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Global SSL setting
        session.verify = config.get_ssl_verify()
        return session
        
    def _update_headers(self):
        """Update session headers with current credentials."""
        device_id = config.get("device_id")
        api_key = config.get("api_key")
        
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "FamilyEye-Agent/2.0.1",
            "X-Device-ID": device_id if device_id else "",
            "X-API-Key": api_key if api_key else ""
        })

    def _get_base_url(self) -> str:
        """Get current backend URL from config."""
        url = config.get("backend_url", "https://localhost:8000")
        return url.rstrip('/')

    def fetch_rules(self) -> Optional[Dict]:
        """Fetch latest rules from backend."""
        try:
            url = f"{self._get_base_url()}/api/rules/agent/fetch"
            # Payload is redundant if headers are used, but keeping for compatibility
            payload = {
                "device_id": config.get("device_id"),
                "api_key": config.get("api_key")
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.debug("Rules fetched successfully")
                if not self.is_online:
                    self.logger.info("Connection restored (fetch_rules)")
                    self.is_online = True
                    self._trigger_reconnect()
                return response.json()
            elif response.status_code == 401:
                self._handle_401()
                return None
            else:
                self.logger.warning(f"Failed to fetch rules: HTTP {response.status_code}")
                # We don't set is_online=False for non-200 if it's not a connection error
                return None
                
        except requests.exceptions.RequestException as e:
            if self.is_online:
                self.logger.warning(f"Connection error fetching rules: {e}")
                self.is_online = False
            return None
            
    def send_reports(self, usage_logs: List[Dict], running_processes: List[str] = None, **kwargs) -> Optional[Dict]:
        """
        Send usage logs to backend.
        
        Args:
            usage_logs: List of activity logs
            running_processes: List of active PIDs/Apps
            **kwargs: Additional metrics (device_uptime_seconds, device_usage_today_seconds)
        """
        """Send usage logs to backend. Returns response JSON on success."""
        if not usage_logs and not running_processes:
            return {}
            
        try:
            url = f"{self._get_base_url()}/api/reports/agent/report"
            from datetime import datetime
            payload = {
                "device_id": config.get("device_id"),
                "api_key": config.get("api_key"),
                "usage_logs": usage_logs,
                "client_timestamp": datetime.now().isoformat(),
                "running_processes": running_processes,
                "device_uptime_seconds": kwargs.get("device_uptime_seconds"),
                "device_usage_today_seconds": kwargs.get("device_usage_today_seconds")
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Sent {len(usage_logs)} activity logs")
                if not self.is_online:
                    self.logger.info("Connection restored (send_reports)")
                    self.is_online = True
                    self._trigger_reconnect()
                return response.json()
            elif response.status_code == 401:
                self._handle_401()
                return None
            else:
                self.logger.warning(f"Failed to send reports: HTTP {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            if self.is_online:
                self.logger.error(f"Network error sending reports: {e}")
                self.is_online = False
            return None
                


    def upload_screenshot_multipart(self, image_data: bytes, filename: str = "screenshot.jpg") -> bool:
        """Upload screenshot using multipart/form-data (Optimized)."""
        try:
            url = f"{self._get_base_url()}/api/screenshots/upload"
            
            # Multipart: requests sets Content-Type+boundary when 'files' present. Auth via headers (X-Device-ID).
            files = {
                'file': (filename, image_data, 'image/jpeg')
            }
            data = {
                'device_id': config.get("device_id"),
                'timestamp': str(time.time())
            }
            
            response = self.session.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                self.logger.info("Screenshot uploaded successfully")
                return True
            else:
                self.logger.warning(f"Screenshot upload failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error uploading screenshot: {e}")
            return False

    def upload_screenshot_base64(self, base64_image: str) -> bool:
        """Upload screenshot using base64 (Legacy/Current Backend)."""
        try:
            url = f"{self._get_base_url()}/api/reports/agent/screenshot"
            
            payload = {
                "device_id": config.get("device_id"),
                "api_key": config.get("api_key"),
                "image": base64_image
            }
            
            # Use a longer timeout for large payloads
            response = self.session.post(url, json=payload, timeout=60)
            
            if response.status_code in [200, 201]:
                self.logger.info("Screenshot uploaded successfully (Base64)")
                return True
            else:
                self.logger.warning(f"Screenshot upload failed: {response.status_code} - {response.text[:100]}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error uploading screenshot (Base64): {e}")
            return False

    def report_critical_event(self, event_data: Dict) -> bool:
        """Report critical event (e.g., limit exceeded) to backend. 
        
        Using this method ensures centralizedauth handling and retries.
        """
        try:
            url = f"{self._get_base_url()}/api/reports/agent/critical-event"
            # Ensure auth data is present if caller didn't supply it
            if "device_id" not in event_data:
                event_data["device_id"] = config.get("device_id")
            if "api_key" not in event_data:
                event_data["api_key"] = config.get("api_key")
                
            response = self.session.post(url, json=event_data, timeout=5)
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Critical event reported: {event_data.get('event_type')}")
                return True
            elif response.status_code == 401:
                self._handle_401()
                return False
            else:
                self.logger.warning(f"Failed to report critical event: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error reporting critical event: {e}")
            return False

    def report_security_event(self, event_data: Dict) -> bool:
        """Report security event (e.g., boot detection) to backend.
        
        This replaces the custom retry logic in boot_protection.py with
        standardized client retry mechanisms.
        """
        try:
            url = f"{self._get_base_url()}/api/security/events"
            # Ensure auth data
            if "device_id" not in event_data:
                event_data["device_id"] = config.get("device_id")
            
            response = self.session.post(url, json=event_data, timeout=5)
            
            if response.status_code in [200, 201]:
                self.logger.info(f"Security event reported: {event_data.get('event_type')}")
                return True
            elif response.status_code == 401:
                self._handle_401()
                return False
            else:
                self.logger.warning(f"Failed to report security event: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error reporting security event: {e}")
            return False

    def check_credentials(self) -> bool:
        """Validate credentials by performing a lightweight fetch."""
        # Using fetch_rules as a probe
        result = self.fetch_rules()
        return result is not None

# Global instance
api_client = BackendAPIClient()
