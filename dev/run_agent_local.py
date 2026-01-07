"""
Local Agent Test Runner
Runs the agent locally and monitors its behavior, simulating client deployment.
"""
import sys
import os
import time
import subprocess
import threading
from datetime import datetime

# Add agent to path
agent_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'windows', 'agent')
sys.path.insert(0, agent_path)

def check_dashboard_connection():
    """Check if we can connect to the dashboard."""
    import requests
    from config import config
    
    backend_url = config.get("backend_url")
    device_id = config.get("device_id")
    api_key = config.get("api_key")
    
    print(f"\n{'='*60}")
    print(f"Dashboard Connection Test")
    print(f"{'='*60}")
    print(f"Backend URL: {backend_url}")
    print(f"Device ID: {device_id}")
    print(f"API Key: {'*' * 10}{api_key[-4:] if api_key else 'Not Set'}")
    
    try:
        response = requests.get(
            f"{backend_url}/api/agent/rules",
            headers={
                "X-Device-ID": device_id,
                "X-API-Key": api_key
            },
            verify=False,
            timeout=5
        )
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Connection successful!")
            data = response.json()
            print(f"  Rules: {len(data.get('rules', []))}")
            print(f"  Usage by app: {len(data.get('usage_by_app', {}))}")
            print(f"  Daily usage: {data.get('daily_usage', 0)}s")
            return True
        else:
            print(f"✗ Connection failed: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

def tail_logs(stop_event):
    """Tail the agent logs."""
    log_file = r"C:\ProgramData\FamilyEye\Agent\agent.log"
    
    # Wait for log file to be created
    while not os.path.exists(log_file) and not stop_event.is_set():
        time.sleep(0.5)
    
    if not os.path.exists(log_file):
        return
    
    print(f"\n{'='*60}")
    print(f"Agent Logs (tail -f {log_file})")
    print(f"{'='*60}\n")
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        # Go to end of file
        f.seek(0, 2)
        
        while not stop_event.is_set():
            line = f.readline()
            if line:
                # Filter for important logs
                if any(keyword in line for keyword in ['ERROR', 'WARNING', 'SUCCESS', 'CRITICAL', 'INFO']):
                    print(line.strip())
            else:
                time.sleep(0.1)

def run_agent():
    """Run the agent in foreground mode."""
    from main import ParentalControlAgent
    
    print(f"\n{'='*60}")
    print(f"Starting Agent")
    print(f"{'='*60}\n")
    
    agent = ParentalControlAgent()
    agent.run()

if __name__ == "__main__":
    print(f"\n{'#'*60}")
    print(f"# FamilyEye Agent - Local Test Environment")
    print(f"# Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")
    
    # 1. Check dashboard connection
    if not check_dashboard_connection():
        print("\n⚠ Dashboard connection failed. Agent may not sync properly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # 2. Start log tailing in background
    stop_event = threading.Event()
    log_thread = threading.Thread(target=tail_logs, args=(stop_event,), daemon=True)
    log_thread.start()
    
    # 3. Run agent
    try:
        run_agent()
    except KeyboardInterrupt:
        print("\n\n✓ Agent stopped by user")
        stop_event.set()
    except Exception as e:
        print(f"\n\n✗ Agent crashed: {e}")
        import traceback
        traceback.print_exc()
        stop_event.set()
