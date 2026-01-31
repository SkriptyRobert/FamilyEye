"""IPC Server - Named Pipe server for Windows Service (BOSS).

Runs in Session 0 and sends UI commands to ChildAgent (MESSENGER)
running in user session.
"""
import os
import sys
import time
import threading
import queue
from typing import Optional, Callable, Dict, Any, List

# Handle pywin32 imports
try:
    import pywintypes
    import win32pipe
    import win32file
    import win32security
    import win32con
    import win32event
    import winerror
    from ntsecuritycon import (
        SECURITY_WORLD_SID_AUTHORITY, SECURITY_WORLD_RID,
        SECURITY_CREATOR_SID_AUTHORITY, SECURITY_CREATOR_OWNER_RID,
        FILE_GENERIC_READ, FILE_GENERIC_WRITE, FILE_ALL_ACCESS
    )
    _win32_available = True
except ImportError:
    _win32_available = False

from .ipc_common import (
    PIPE_NAME, PIPE_BUFFER_SIZE, PIPE_TIMEOUT_MS,
    IPCMessage, IPCCommand
)
from .logger import get_logger


class IPCServer:
    """Named Pipe server for service-to-child-agent communication.
    
    Creates a Named Pipe that ChildAgent connects to. Supports:
    - Sending messages to connected clients
    - Broadcasting to all connected clients
    - Receiving responses (PONG for heartbeat)
    - Forwarding HEARTBEAT to HeartbeatMonitor
    """
    
    def __init__(self):
        self.logger = get_logger('IPC_SERVER')
        self.running = False
        self._server_thread: Optional[threading.Thread] = None
        self._message_queue: queue.Queue = queue.Queue()
        self._connected_clients: List[Any] = []  # List of pipe handles
        self._clients_lock = threading.Lock()
        self._stop_event: Optional[Any] = None
        self._last_pong_time: float = 0
        self._heartbeat_callback: Optional[Callable] = None
        self._screenshot_callback: Optional[Callable] = None
        self._screenshot_ready_callback: Optional[Callable] = None
        
        if not _win32_available:
            self.logger.error("pywin32 not available - IPC server disabled")
    
    def set_heartbeat_callback(self, callback: Callable):
        """Set callback for when heartbeat is received from ChildAgent."""
        self._heartbeat_callback = callback

    def set_screenshot_callback(self, callback: Callable):
        """Set callback for when screenshot data is received from ChildAgent."""
        self._screenshot_callback = callback
    
    def set_screenshot_ready_callback(self, callback: Callable):
        """Set callback for when screenshot file is ready (SCREENSHOT_READY)."""
        self._screenshot_ready_callback = callback
    
    def _create_security_attributes(self):
        """Create security attributes allowing all users to connect.
        
        This is necessary because the service runs as SYSTEM and 
        the child agent runs as a regular user (child account).
        """
        sa = pywintypes.SECURITY_ATTRIBUTES()
        
        # Create SID for Everyone
        sid_everyone = pywintypes.SID()
        sid_everyone.Initialize(SECURITY_WORLD_SID_AUTHORITY, 1)
        sid_everyone.SetSubAuthority(0, SECURITY_WORLD_RID)
        
        # Create SID for Creator/Owner
        sid_creator = pywintypes.SID()
        sid_creator.Initialize(SECURITY_CREATOR_SID_AUTHORITY, 1)
        sid_creator.SetSubAuthority(0, SECURITY_CREATOR_OWNER_RID)
        
        # Create ACL
        acl = pywintypes.ACL()
        acl.AddAccessAllowedAce(FILE_GENERIC_READ | FILE_GENERIC_WRITE, sid_everyone)
        acl.AddAccessAllowedAce(FILE_ALL_ACCESS, sid_creator)
        
        # Set DACL
        sa.SetSecurityDescriptorDacl(1, acl, 0)
        return sa
    
    def _server_loop(self):
        """Main server loop - creates pipe and handles connections."""
        self.logger.info("IPC Server starting", pipe_name=PIPE_NAME)
        
        while self.running:
            try:
                # Create overlapped structure for async operations
                overlapped = pywintypes.OVERLAPPED()
                overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
                
                # Create Named Pipe instance
                pipe_handle = win32pipe.CreateNamedPipe(
                    PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    PIPE_BUFFER_SIZE,
                    PIPE_BUFFER_SIZE,
                    PIPE_TIMEOUT_MS,
                    self._create_security_attributes()
                )
                
                self.logger.debug("Named Pipe created, waiting for client...")
                
                # Wait for client to connect (non-blocking with overlapped)
                try:
                    hr = win32pipe.ConnectNamedPipe(pipe_handle, overlapped)
                except pywintypes.error as e:
                    if e.winerror == winerror.ERROR_PIPE_CONNECTED:
                        # Client already connected
                        win32event.SetEvent(overlapped.hEvent)
                    else:
                        raise
                
                # Wait for connection or stop event
                handles = [self._stop_event, overlapped.hEvent]
                rc = win32event.WaitForMultipleObjects(handles, False, win32event.INFINITE)
                
                if rc == win32event.WAIT_OBJECT_0:
                    # Stop event signaled
                    win32file.CloseHandle(pipe_handle)
                    break
                elif rc == win32event.WAIT_OBJECT_0 + 1:
                    # Client connected
                    self.logger.info("Child agent connected")
                    
                    # Add to connected clients
                    with self._clients_lock:
                        self._connected_clients.append(pipe_handle)
                    
                    # Handle this client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(pipe_handle,),
                        daemon=True
                    )
                    client_thread.start()
                
                # Cleanup overlapped event
                win32file.CloseHandle(overlapped.hEvent)
                
            except Exception as e:
                self.logger.error(f"IPC Server error: {e}")
                time.sleep(1)
        
        self.logger.info("IPC Server stopped")
    
    def _handle_client(self, pipe_handle):
        """Handle communication with a connected client."""
        try:
            while self.running:
                # Check for messages in queue to send
                try:
                    message = self._message_queue.get(timeout=0.1)
                    self._send_to_client(pipe_handle, message)
                except queue.Empty:
                    pass
                
                # Try to read response from client (non-blocking)
                try:
                    # Check if data available
                    result = win32pipe.PeekNamedPipe(pipe_handle, 0)
                    if result[1] > 0:  # Data available
                        hr, data = win32file.ReadFile(pipe_handle, PIPE_BUFFER_SIZE)
                        if data:
                            self._handle_client_message(data)
                except pywintypes.error as e:
                    if e.winerror in [winerror.ERROR_BROKEN_PIPE, winerror.ERROR_NO_DATA]:
                        self.logger.warning("Client disconnected")
                        break
                    # Ignore other read errors (no data available)
                    
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            # Remove from connected clients
            with self._clients_lock:
                if pipe_handle in self._connected_clients:
                    self._connected_clients.remove(pipe_handle)
            
            try:
                win32pipe.DisconnectNamedPipe(pipe_handle)
                win32file.CloseHandle(pipe_handle)
            except:
                pass
    
    def _send_to_client(self, pipe_handle, message: IPCMessage):
        """Send message to specific client."""
        try:
            data = message.to_bytes()
            win32file.WriteFile(pipe_handle, data)
            self.logger.debug(f"Sent message: {message.command}")
        except pywintypes.error as e:
            self.logger.error(f"Failed to send to client: {e}")
            raise
    
    def _handle_client_message(self, data: bytes):
        """Handle message received from client."""
        try:
            message = IPCMessage.from_bytes(data)
            self.logger.debug(f"Received from client: {message.command}")
            
            if message.command == IPCCommand.PONG.value:
                self._last_pong_time = time.time()
                self.logger.debug("Heartbeat received from client")
            elif message.command == IPCCommand.HEARTBEAT.value:
                # Forward to HeartbeatMonitor
                if self._heartbeat_callback:
                    self._heartbeat_callback()
                self.logger.debug("HEARTBEAT received from ChildAgent")
            elif message.command == IPCCommand.STATUS_RESPONSE.value:
                self.logger.debug(f"Status from client: {message.data}")
            elif message.command == IPCCommand.SCREENSHOT_DATA.value:
                self.logger.info("Screenshot data received from client")
                if self._screenshot_callback:
                    self._screenshot_callback(message.data.get("image"))
            elif message.command == IPCCommand.SCREENSHOT_READY.value:
                # New: ChildAgent saved screenshot to file, forward path to callback
                file_path = message.data.get("path", "")
                self.logger.info(f"Screenshot ready at: {file_path}")
                if self._screenshot_ready_callback:
                    self._screenshot_ready_callback(file_path)
                
        except Exception as e:
            self.logger.error(f"Error parsing client message: {e}")
    
    def start(self):
        """Start the IPC server."""
        if not _win32_available:
            self.logger.warning("Cannot start IPC server - pywin32 not available")
            return False
        
        if self.running:
            return True
        
        self.running = True
        self._stop_event = win32event.CreateEvent(None, True, False, None)
        
        self._server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self._server_thread.start()
        
        self.logger.info("IPC Server started")
        return True
    
    def stop(self):
        """Stop the IPC server."""
        if not self.running:
            return
        
        self.running = False
        
        # Signal stop
        if self._stop_event:
            win32event.SetEvent(self._stop_event)
        
        # Close all client connections
        with self._clients_lock:
            for handle in self._connected_clients:
                try:
                    win32pipe.DisconnectNamedPipe(handle)
                    win32file.CloseHandle(handle)
                except:
                    pass
            self._connected_clients.clear()
        
        # Wait for server thread
        if self._server_thread:
            self._server_thread.join(timeout=5)
        
        self.logger.info("IPC Server stopped")
    
    def send_message(self, message: IPCMessage):
        """Queue message for sending to all connected clients."""
        self._message_queue.put(message)
    
    def broadcast(self, message: IPCMessage):
        """Send message immediately to all connected clients."""
        with self._clients_lock:
            for handle in self._connected_clients[:]:  # Copy list
                try:
                    self._send_to_client(handle, message)
                except:
                    # Client disconnected, will be cleaned up by handler
                    pass
    
    def send_ping(self):
        """Send heartbeat ping to all clients."""
        from .ipc_common import msg_ping
        self.broadcast(msg_ping())
    
    def is_client_alive(self, max_age_seconds: float = 10.0) -> bool:
        """Check if client responded to ping recently."""
        if not self._connected_clients:
            return False
        return (time.time() - self._last_pong_time) < max_age_seconds
    
    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        with self._clients_lock:
            return len(self._connected_clients)


# Singleton instance for easy access
_ipc_server: Optional[IPCServer] = None


def get_ipc_server() -> IPCServer:
    """Get or create the global IPC server instance."""
    global _ipc_server
    if _ipc_server is None:
        _ipc_server = IPCServer()
    return _ipc_server
