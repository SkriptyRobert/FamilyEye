
import sys
import os
import time
from collections import defaultdict
from unittest.mock import MagicMock, patch

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
# agent module is in ../clients/windows/agent
# We need to make sure we can import it
agent_dir = os.path.abspath(os.path.join(current_dir, '..', 'clients', 'windows'))
sys.path.insert(0, agent_dir)

try:
    from agent.monitor import AppMonitor
except ImportError:
    # Fallback if agent package structure is different in dev
    agent_dir = os.path.abspath(os.path.join(current_dir, '..', 'clients', 'windows', 'agent'))
    sys.path.insert(0, agent_dir)
    from monitor import AppMonitor

def test_keyerror_repro():
    print("--- Starting KeyError Repro ---")
    
    # 1. Initialize Monitor
    monitor = AppMonitor()
    
    print(f"usage_today type: {type(monitor.usage_today)}")
    
    # 2. Mock psutil to return 'dllhost'
    mock_proc = MagicMock()
    mock_proc.pid = 1234
    mock_proc.name.return_value = 'dllhost.exe'
    mock_proc.exe.return_value = 'C:\\Windows\\System32\\dllhost.exe'
    mock_proc.username.return_value = 'User'
    
    # Mock _get_pids_with_visible_windows to return empty (so it hits Criteria C or fails)
    # But wait, dllhost often has no window.
    # If no window, and username is User, it hits Criteria C?
    # Line 387: is_user_app = True
    
    with patch('psutil.process_iter', return_value=[mock_proc]):
        with patch('win32gui.EnumWindows', side_effect=lambda x,y: None): # Mock win32
             # Trigger update
             print("Running update()...")
             try:
                 monitor.update()
                 print("✅ Update finished without error.")
             except KeyError as e:
                 print(f"❌ CAUGHT EXPECTED ERROR: {e}")
                 import traceback
                 traceback.print_exc()
             except Exception as e:
                 print(f"❌ CAUGHT UNEXPECTED ERROR: {e}")
                 import traceback
                 traceback.print_exc()

    # 3. Check if 'dllhost' is in usage_today
    if 'dllhost' in monitor.usage_today:
        print(f"dllhost usage: {monitor.usage_today['dllhost']}")
    else:
        print("dllhost not tracked (maybe filtered?)")

if __name__ == "__main__":
    test_keyerror_repro()
