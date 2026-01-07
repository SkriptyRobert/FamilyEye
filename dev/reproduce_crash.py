
import sys
import os
import time
import logging
from collections import defaultdict
import threading

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# c:\Users\Administrator\Documents\Cursor\Parential-Control_Enterprise\dev
project_root = os.path.join(current_dir, '..')
agent_path = os.path.join(project_root, 'clients', 'windows', 'agent')
sys.path.append(agent_path)

# Mock modules BEFORE importing monitor
from unittest.mock import MagicMock
sys.modules['clients.windows.agent.config'] = MagicMock()
sys.modules['clients.windows.agent.network_control'] = MagicMock()
sys.modules['clients.windows.agent.ipc_common'] = MagicMock()
# Also mock top-level if needed (depending on how they are imported)
sys.modules['config'] = MagicMock()
sys.modules['network_control'] = MagicMock()
sys.modules['ipc_common'] = MagicMock()

# Setup basic logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("repro")

try:
    print(f"Importing AppMonitor from {agent_path}")
    from monitor import AppMonitor
    
    print("Initializing AppMonitor")
    monitor = AppMonitor()
    
    # Manually inject 'phoneexperiencehost' into detections to trigger logic if it depends on it
    # But since psutil scans real processes, we might not find it.
    # However, we can MOCK psutil!
    import psutil
    
    # Create a mock process for phoneexperiencehost
    class MockProcess:
        def __init__(self, pid, name, exe):
            self.pid = pid
            self.info = {'name': name, 'exe': exe}
        def username(self): return "Administrator"
        
    original_process_iter = psutil.process_iter
    
    def mock_process_iter(attrs):
        yield MockProcess(1234, "phoneexperiencehost.exe", "C:\\Windows\\System32\\PhoneExperienceHost.exe")
        yield MockProcess(5678, "chrome.exe", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
        
    psutil.process_iter = mock_process_iter
    print("Mocked psutil.process_iter")
    
    print("Starting update loop...")
    try:
        monitor.update()
        print("Update completed successfully")
    except KeyError as e:
        print(f"!!! CAUGHT EXPECTED KEYERROR: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"Caught unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"Setup/Run failed: {e}")
    import traceback
    traceback.print_exc()
