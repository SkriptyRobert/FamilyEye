"""
Dashboard Verification Script
Compares agent-side data with dashboard data to verify accuracy.
"""
import requests
import json
import time
from datetime import datetime
import urllib3
urllib3.disable_warnings()

# Configuration
BACKEND_URL = "https://192.168.0.145:8000"
with open(r"C:\ProgramData\FamilyEye\Agent\config.json") as f:
    config = json.load(f)

DEVICE_ID = config['device_id']
API_KEY = config['api_key']

print(f"\n{'='*70}")
print(f"Dashboard Verification Tool")
print(f"{'='*70}\n")
print(f"Device ID: {DEVICE_ID}")
print(f"Backend: {BACKEND_URL}")
print(f"\n{'='*70}\n")

def get_device_data():
    """Fetch device data from backend."""
    try:
        headers = {
            'X-Device-ID': DEVICE_ID,
            'X-API-Key': API_KEY
        }
        
        response = requests.get(
            f"{BACKEND_URL}/api/devices/status",
            headers=headers,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None

def format_time(seconds):
    """Format seconds to human readable time."""
    if seconds is None:
        return "0s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def monitor_dashboard():
    """Monitor and display dashboard data."""
    iteration = 0
    
    while True:
        iteration += 1
        print(f"\n{'─'*70}")
        print(f"📊 Iteration #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'─'*70}\n")
        
        data = get_device_data()
        
        if data:
            # Device status
            print(f"🖥️  Device Status:")
            print(f"   Name: {data.get('device_name', 'N/A')}")
            print(f"   Online: {'✓ Yes' if data.get('is_online') else '✗ No'}")
            print(f"   Last Seen: {data.get('last_seen', 'N/A')}")
            
            # Total device time
            print(f"\n⏱️  Total Device Time:")
            total_time = data.get('usage_today', {}).get('total_time', 0)
            print(f"   Today: {format_time(total_time)}")
            
            # Application times
            apps = data.get('usage_today', {}).get('apps', {})
            if apps:
                print(f"\n📱  Application Times:")
                sorted_apps = sorted(apps.items(), key=lambda x: x[1], reverse=True)
                for app_name, app_time in sorted_apps[:10]:
                    print(f"   {app_name}: {format_time(app_time)}")
            else:
                print(f"\n📱  No application data yet")
            
            # Monitoring info
            monitoring = data.get('monitoring', {})
            if monitoring:
                print(f"\n👁️  Currently Monitoring:")
                print(f"   Process: {monitoring.get('current_app', 'N/A')}")
                print(f"   Window: {monitoring.get('window_title', 'N/A')}")
        
        print(f"\n{'─'*70}")
        print(f"Refreshing in 10 seconds... (Ctrl+C to stop)")
        
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print(f"\n\n✓ Monitoring stopped\n")
            break

if __name__ == "__main__":
    try:
        monitor_dashboard()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
