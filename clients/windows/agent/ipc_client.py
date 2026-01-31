"""IPC Client - Named Pipe client for ChildAgent (MESSENGER).

Runs in user session and receives UI commands from Windows Service (BOSS).
"""
import os
import sys
import time
import threading
from typing import Optional, Callable, Dict, Any

# Handle pywin32 imports
try:
    import pywintypes
    import win32pipe
    import win32file
    import winerror
    _win32_available = True
except ImportError:
    _win32_available = False

from .ipc_common import (
    PIPE_NAME, PIPE_BUFFER_SIZE, PIPE_TIMEOUT_MS,
    IPCMessage, IPCCommand, msg_pong
)


class IPCClient:
    """Named Pipe client for child agent communication.
    
    Connects to the service's Named Pipe and:
    - Receives UI commands (show notifications, lock screen, etc.)
    - Sends heartbeat responses (PONG)
    """
    
    def __init__(self, message_handler: Optional[Callable[[IPCMessage], None]] = None):
        """Initialize IPC client.
        
        Args:
            message_handler: Callback function to handle received messages.
                            Called with IPCMessage as argument.
        """
        self.message_handler = message_handler
        self.running = False
        self._client_thread: Optional[threading.Thread] = None
        self._pipe_handle = None
        self._reconnect_delay = 2.0  # Seconds between reconnection attempts
        self._log_callback: Optional[Callable[[str], None]] = None
    
    @property
    def connected(self) -> bool:
        """Check if client is connected to service pipe."""
        return self._pipe_handle is not None
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Set logging callback function."""
        self._log_callback = callback
    
    def _log(self, message: str):
        """Log message using callback or print."""
        if self._log_callback:
            self._log_callback(message)
        else:
            print(f"[IPC_CLIENT] {message}")
    
    def _connect(self) -> bool:
        """Connect to the service's Named Pipe."""
        if not _win32_available:
            self._log("pywin32 not available")
            return False
        
        try:
            # Try to open the pipe directly
            # WaitNamedPipe can be unreliable, so we'll just attempt CreateFile
            try:
                self._pipe_handle = win32file.CreateFile(
                    PIPE_NAME,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,  # No sharing
                    None,  # Default security
                    win32file.OPEN_EXISTING,
                    0,  # Normal attributes
                    None  # No template
                )
            except pywintypes.error as e:
                if e.winerror == winerror.ERROR_PIPE_BUSY:
                    # Pipe exists but is busy, wait and retry
                    self._log("Pipe busy - waiting...")
                    try:
                        win32pipe.WaitNamedPipe(PIPE_NAME, PIPE_TIMEOUT_MS)
                        self._pipe_handle = win32file.CreateFile(
                            PIPE_NAME,
                            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                            0, None, win32file.OPEN_EXISTING, 0, None
                        )
                    except pywintypes.error:
                        raise
                else:
                    raise
            
            # Set pipe to message mode
            win32pipe.SetNamedPipeHandleState(
                self._pipe_handle,
                win32pipe.PIPE_READMODE_MESSAGE,
                None,
                None
            )
            
            self._log("Connected to service pipe")
            return True
            
        except pywintypes.error as e:
            if e.winerror == winerror.ERROR_FILE_NOT_FOUND:
                self._log("Service pipe not found - service may not be running")
            elif e.winerror == winerror.ERROR_PIPE_BUSY:
                self._log("Pipe busy - will retry")
            else:
                self._log(f"Connection error [{e.winerror}]: {e}")
            return False
        except Exception as e:
            self._log(f"Unexpected error connecting: {e}")
            return False
    
    def _disconnect(self):
        """Disconnect from pipe."""
        if self._pipe_handle:
            try:
                win32file.CloseHandle(self._pipe_handle)
            except:
                pass
            self._pipe_handle = None
    
    def _client_loop(self):
        """Main client loop - connect and receive messages."""
        self._log("IPC Client starting...")
        
        while self.running:
            # Try to connect if not connected
            if not self._pipe_handle:
                if not self._connect():
                    time.sleep(self._reconnect_delay)
                    continue
            
            # Read messages
            try:
                hr, data = win32file.ReadFile(self._pipe_handle, PIPE_BUFFER_SIZE)
                
                if data:
                    self._handle_message(data)
                    
            except pywintypes.error as e:
                if e.winerror in [winerror.ERROR_BROKEN_PIPE, 
                                  winerror.ERROR_NO_DATA,
                                  winerror.ERROR_PIPE_NOT_CONNECTED]:
                    self._log("Disconnected from service")
                    self._disconnect()
                    time.sleep(self._reconnect_delay)
                else:
                    self._log(f"Read error: {e}")
                    time.sleep(0.1)
            except Exception as e:
                self._log(f"Error in client loop: {e}")
                time.sleep(1)
        
        self._disconnect()
        self._log("IPC Client stopped")
    
    def _handle_message(self, data: bytes):
        """Handle received message."""
        try:
            message = IPCMessage.from_bytes(data)
            self._log(f"Received: {message.command}")
            
            # Handle PING automatically
            if message.command == IPCCommand.PING.value:
                self.send_message(msg_pong())
                return
            
            # Pass to handler
            if self.message_handler:
                try:
                    self.message_handler(message)
                except Exception as e:
                    self._log(f"Error in message handler: {e}")
                    
        except Exception as e:
            self._log(f"Error parsing message: {e}")
    
    def send_message(self, message: IPCMessage) -> bool:
        """Send message to service."""
        if not self._pipe_handle:
            self._log("Cannot send - not connected")
            return False
        
        try:
            win32file.WriteFile(self._pipe_handle, message.to_bytes())
            return True
        except pywintypes.error as e:
            self._log(f"Send error: {e}")
            return False
    
    def start(self):
        """Start the IPC client."""
        if not _win32_available:
            self._log("Cannot start - pywin32 not available")
            return False
        
        if self.running:
            return True
        
        self.running = True
        self._client_thread = threading.Thread(target=self._client_loop, daemon=True)
        self._client_thread.start()
        
        self._log("IPC Client started")
        return True
    
    def stop(self):
        """Stop the IPC client."""
        if not self.running:
            return
        
        self.running = False
        self._disconnect()
        
        if self._client_thread:
            self._client_thread.join(timeout=5)
        
        self._log("IPC Client stopped")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to service."""
        return self._pipe_handle is not None
