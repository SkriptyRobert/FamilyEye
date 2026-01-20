"""WebSocket client for real-time communication with backend.

Features:
- Thread-safe background execution
- Auto-reconnection with exponential backoff
- Heartbeat (Ping/Pong) with timeout detection
- Push command handling
- Secure authentication via X-API-Key header
"""
import asyncio
import json
import ssl
import threading
import time
import socket
from typing import Callable, Optional, List, Dict
import websockets
from websockets.exceptions import ConnectionClosed

from ..config import config
from ..logger import get_logger
from .messages import WebSocketCommand, WebSocketMessage

class WebSocketClient:
    """Thread-safe WebSocket client with auto-reconnection and resilience."""
    
    HEARTBEAT_INTERVAL = 30  # seconds
    HEARTBEAT_TIMEOUT = 90   # 3x interval
    RETRY_INTERVAL_BASE = 5  # seconds
    RETRY_INTERVAL_MAX = 300 # 5 minutes
    MAX_FAILURES = 3         # before HTTP fallback recommendation (internal state)
    
    def __init__(self):
        self.logger = get_logger('WEBSOCKET')
        self._ws = None
        self._is_connected = False
        self._is_running = False
        self._loop = None
        self._thread = None
        self._command_callbacks: List[Callable[[WebSocketCommand], None]] = []
        self._consecutive_failures = 0
        self._last_pong_time = 0
        self._connection_lock = threading.Lock()
        
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._is_connected
        
    def add_command_callback(self, callback: Callable[[WebSocketCommand], None]):
        """Register callback for incoming commands."""
        self._command_callbacks.append(callback)
        
    def start(self):
        """Start WebSocket client in a background thread."""
        if self._is_running:
            return
            
        self.logger.info("Starting WebSocket client...")
        self._is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop WebSocket client."""
        self.logger.info("Stopping WebSocket client...")
        self._is_running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)
            
    def _run_loop(self):
        """Internal threaded loop logic."""
        # Create a new event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            self.logger.error(f"WebSocket loop crash: {e}")
        finally:
            self._loop.close()
            self.logger.info("WebSocket loop closed")

    async def _connect_loop(self):
        """Persistent connection loop with backoff."""
        while self._is_running:
            # 1. Config Check
            if not config.is_configured():
                await asyncio.sleep(5)
                continue
                
            # 2. Network Check (skip if offline)
            if not self._is_network_available():
                self.logger.debug("Network unavailable, waiting...")
                await asyncio.sleep(10)
                continue

            # 3. Prepare Connection
            backend_url = config.get('backend_url', '')
            device_id = config.get('device_id', '')
            api_key = config.get('api_key', '')
            
            if not backend_url or not device_id or not api_key:
                self.logger.warning("Missing config for WebSocket, waiting...")
                await asyncio.sleep(10)
                continue

            # Convert HTTP URL to WS URL
            # e.g. https://api.example.com -> wss://api.example.com/ws/device/{id}
            ws_url = backend_url.replace("https://", "wss://").replace("http://", "ws://")
            ws_url = f"{ws_url}/ws/device/{device_id}"
            
            headers = {
                "X-API-Key": api_key,
                "X-Device-ID": device_id,
                "User-Agent": "FamilyEye-WindowsAgent/2.0"
            }

            try:
                self.logger.info(f"Connecting to {ws_url}...")
                
                # SSL Context (mimic api_client behavior)
                ssl_context = None
                if ws_url.startswith("wss://"):
                    ssl_context = ssl.create_default_context()
                    # Disable hostname check if needed (e.g. self-signed dev) or standard check
                    if "localhost" in ws_url or "127.0.0.1" in ws_url:
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE

                async with websockets.connect(
                    ws_url, 
                    extra_headers=headers, 
                    ssl=ssl_context,
                    ping_interval=None, # We enforce our own heartbeat
                    ping_timeout=None
                ) as websocket:
                    
                    self._ws = websocket
                    self._is_connected = True
                    self._consecutive_failures = 0
                    self._last_pong_time = time.time()
                    self.logger.success("WebSocket Connected")
                    
                    # Notify reconnection (optional, could trigger rule fetch here directly)
                    # But simpler to let the Ping/Message loop handle it via commands
                    
                    # Start Heartbeat Task
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    
                    try:
                        while self._is_running:
                            # Listen for messages
                            message_data = await websocket.recv()
                            await self._handle_message(message_data)
                    except ConnectionClosed:
                        self.logger.warning("WebSocket Connection Closed")
                    except Exception as e:
                        self.logger.error(f"WebSocket Verification Error: {e}")
                    finally:
                        self._is_connected = False
                        self._ws = None
                        heartbeat_task.cancel()
                        try:
                            await heartbeat_task
                        except asyncio.CancelledError:
                            pass
                            
            except (OSError, socket.error, websockets.exceptions.WebSocketException) as e:
                self._is_connected = False
                self._consecutive_failures += 1
                self.logger.error(f"Connection failed: {e}")
            except Exception as e:
                self._is_connected = False
                self._consecutive_failures += 1
                self.logger.error(f"Unexpected error: {e}")
            
            # Backoff before retry
            delay = self._calculate_backoff()
            self.logger.info(f"Reconnecting in {delay:.1f}s (Attempt {self._consecutive_failures})")
            await asyncio.sleep(delay)

    async def _handle_message(self, raw_data: str):
        """Process incoming raw message."""
        try:
            msg = WebSocketMessage.from_json(raw_data)
            
            if msg.type == 'pong':
                self._last_pong_time = time.time()
                # self.logger.debug("Pong received")
                return
                
            if msg.type == 'command':
                self.logger.info(f"Received Command: {msg.cmd}")
                cmd_obj = WebSocketCommand(command=msg.cmd, payload=msg.payload)
                
                # Dispatch to callbacks
                for callback in self._command_callbacks:
                    try:
                        # Callbacks might be sync or expected to run quickly
                        # For safety, we can run them in thread pool if they block,
                        # but agent logic assumes quick non-blocking triggers usually.
                        if asyncio.iscoroutinefunction(callback):
                            await callback(cmd_obj)
                        else:
                            callback(cmd_obj) 
                    except Exception as e:
                        self.logger.error(f"Error in command callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error handling message: {e} | Raw: {raw_data[:50]}")

    async def _heartbeat_loop(self):
        """Send periodic pings and check for timeouts."""
        while self._is_running and self._is_connected:
            try:
                # Sleep interval
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                if not self._ws:
                    break

                # 1. Check Timeout (Zombie Connection)
                time_since_last_pong = time.time() - self._last_pong_time
                if time_since_last_pong > self.HEARTBEAT_TIMEOUT:
                    self.logger.error(f"Heartbeat timeout ({time_since_last_pong:.1f}s > {self.HEARTBEAT_TIMEOUT}s) - resetting connection")
                    await self._ws.close()
                    break

                # 2. Send Ping
                ping_msg = json.dumps({"type": "ping"})
                await self._ws.send(ping_msg)
                # self.logger.debug("Ping sent")
                
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                if self._ws:
                    await self._ws.close()
                break

    def _calculate_backoff(self) -> float:
        """Calculate retry delay with exponential backoff."""
        # 5, 10, 20, 40, ..., 300
        backoff = self.RETRY_INTERVAL_BASE * (2 ** min(self._consecutive_failures, 6))
        return min(backoff, self.RETRY_INTERVAL_MAX)

    def _is_network_available(self) -> bool:
        """Check if network is available (simple DNS check)."""
        try:
            # Try resolving Google DNS or Backend Host
            # Fast check
            socket.create_connection(("8.8.8.8", 53), timeout=3).close()
            return True
        except (socket.timeout, socket.error, OSError):
            return False

    def should_use_http_fallback(self) -> bool:
        """Return True if WebSocket is unstable and HTTP should be active."""
        return not self._is_connected or self._consecutive_failures >= self.MAX_FAILURES
