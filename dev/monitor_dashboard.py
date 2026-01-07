"""
Dashboard Monitor - Check what the agent is reporting to the dashboard
"""
import sys
import os
import time
import requests
from datetime import datetime

# Add agent to path for config access
agent_path = os.path.join(os.path.dirname(__file__), '..', 'clients', 'windows', 'agent')
sys.path.insert(0, agent_path)

from config import config

def fetch_device_status():
    """Fetch current device status from dashboard."""
    backend_url = config.get("backend_url")
    device_id = config.get("device_id")
    api_key = config.get("api_key")
    
    try:
        # Fetch rules response (includes usage data)
        response = requests.post(
            f"{backend_url}/api/rules/agent/fetch",
            json={
                "device_id": device_id,
                "api_key": api_key
            },
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def monitor_dashboard(interval=10):
    """Monitor dashboard data in real-time."""
    print(f"\n{'='*80}")
    print(f"Dashboard Monitor - Device: {config.get('device_id')}")
    print(f"Backend: {config.get('backend_url')}")
    print(f"Refresh interval: {interval}s")
    print(f"{'='*80}\n")
    
    last_data = None
    
    try:
        while True:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching dashboard data...")
            data = fetch_device_status()
            
            if data:
                print(f"\n{'─'*80}")
                print(f"Server Time: {data.get('server_time', 'N/A')}")
                print(f"Rules: {len(data.get('rules', []))}")
                print(f"Daily Usage (device): {data.get('daily_usage', 0)}s ({data.get('daily_usage', 0)//60}m)")
                
                usage_by_app = data.get('usage_by_app', {})
                if usage_by_app:
                    print(f"\nApp Usage Today:")
                    for app, seconds in sorted(usage_by_app.items(), key=lambda x: -x[1])[:10]:
                        minutes = seconds // 60
                        print(f"  {app:30s}: {minutes:3d}m ({seconds}s)")
                else:
                    print("\nNo app usage data yet.")
                
                # Show changes
                if last_data and last_data.get('daily_usage') != data.get('daily_usage'):
                    diff = data.get('daily_usage', 0) - last_data.get('daily_usage', 0)
                    print(f"\n📊 Change: +{diff}s since last check")
                
                last_data = data
            else:
                print("✗ Failed to fetch data")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n✓ Monitoring stopped")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Monitor FamilyEye dashboard data")
    parser.add_argument('--interval', type=int, default=10, help='Refresh interval in seconds')
    args = parser.parse_args()
    
    monitor_dashboard(args.interval)
