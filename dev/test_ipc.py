#!/usr/bin/env python
"""Test script for IPC communication.

Tests Named Pipe communication between service (BOSS) and ChildAgent (MESSENGER).

Usage:
    python dev/test_ipc.py server  - Start IPC server (simulates service)
    python dev/test_ipc.py client  - Start IPC client (simulates ChildAgent)
    python dev/test_ipc.py test    - Run automated test
"""
import sys
import os
import time
import threading

# Add parent directory for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
_windows_agent_dir = os.path.join(_project_root, "clients", "windows")
sys.path.insert(0, _windows_agent_dir)
os.chdir(_windows_agent_dir)

from agent.ipc_common import *
from agent.ipc_server import IPCServer
from agent.ipc_client import IPCClient


def run_server():
    """Run IPC server (simulates Windows Service)."""
    print("Starting IPC Server...")
    server = IPCServer()
    server.start()
    
    print("Server running. Press Ctrl+C to stop.")
    print("Connected clients: 0")
    
    try:
        test_msgs = [
            ("SHOW_WARNING", lambda: server.broadcast(msg_show_warning("⚠️ Test", "This is a test warning"))),
            ("SHOW_LOCK_SCREEN", lambda: server.broadcast(msg_show_lock_screen("Device locked by test"))),
            ("PING", lambda: server.broadcast(msg_ping())),
        ]
        
        msg_idx = 0
        while True:
            time.sleep(3)
            print(f"[Server] Connected clients: {server.client_count}")
            
            if server.client_count > 0:
                name, func = test_msgs[msg_idx % len(test_msgs)]
                print(f"[Server] Sending: {name}")
                func()
                msg_idx += 1
                
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.stop()


def run_client():
    """Run IPC client (simulates ChildAgent)."""
    def message_handler(msg):
        print(f"[Client] Received: {msg.command} - {msg.data}")
    
    print("Starting IPC Client...")
    client = IPCClient(message_handler=message_handler)
    client.set_log_callback(lambda m: print(f"[Client] {m}"))
    client.start()
    
    print("Client running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping client...")
    finally:
        client.stop()


def run_test():
    """Run automated IPC test."""
    print("=" * 60)
    print("IPC Communication Test")
    print("=" * 60)
    
    received_messages = []
    
    def on_message(msg):
        received_messages.append(msg)
        print(f"  [✓] Received: {msg.command}")
    
    # Start server
    print("\n1. Starting IPC Server...")
    server = IPCServer()
    server.start()
    time.sleep(0.5)
    print("   Server started: OK")
    
    # Start client
    print("\n2. Starting IPC Client...")
    client = IPCClient(message_handler=on_message)
    client.start()
    
    # Wait for connection
    print("\n3. Waiting for connection...")
    for _ in range(10):
        if server.client_count > 0:
            print(f"   Connected: OK (clients: {server.client_count})")
            break
        time.sleep(0.5)
    else:
        print("   Connection FAILED")
        server.stop()
        client.stop()
        return False
    
    # Send test messages
    print("\n4. Testing message delivery:")
    test_messages = [
        msg_ping(),
        msg_show_warning("Test", "Test message"),
        msg_show_info("Info", "Info message"),
    ]
    
    for msg in test_messages:
        print(f"   Sending: {msg.command}...", end=" ")
        server.broadcast(msg)
        time.sleep(0.3)
    
    # Wait for messages
    time.sleep(1)
    
    # Verify
    print(f"\n5. Verification:")
    print(f"   Messages sent: {len(test_messages)}")
    print(f"   Messages received: {len(received_messages)}")
    
    # PONG response from PING is automatic
    expected_count = len(test_messages) - 1  # PING auto-responds with PONG
    if len(received_messages) >= expected_count:
        print("   Status: PASS ✓")
        success = True
    else:
        print("   Status: FAIL ✗")
        success = False
    
    # Cleanup
    print("\n6. Cleanup...")
    client.stop()
    server.stop()
    print("   Done")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED:", "PASS" if success else "FAIL")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "server":
        run_server()
    elif mode == "client":
        run_client()
    elif mode == "test":
        success = run_test()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown mode: {mode}")
        print(__doc__)
        sys.exit(1)
