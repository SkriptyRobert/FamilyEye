"""
Manual Agent Pairing
Calls the backend pairing API directly to get device credentials.
"""
import requests
import json
import os

BACKEND_URL = "https://192.168.0.145:8000"
PAIRING_TOKEN = "f82bb1ad-1415-4987-a057-2debfc008ec0"

print(f"\n{'='*60}")
print(f"Manual Agent Pairing")
print(f"{'='*60}\n")

# Call pairing API
print("Calling pairing API...")
try:
    import uuid
    # Generate unique device ID
    device_id = f"windows-{os.environ.get('COMPUTERNAME', 'TestPC')}-{str(uuid.uuid4())[:8]}"
    mac_address = "00:00:00:00:00:00"  # Dummy MAC for testing
    
    response = requests.post(
        f"{BACKEND_URL}/api/devices/pairing/pair",
        json={
            "token": PAIRING_TOKEN,
            "device_name": f"Test-{os.environ.get('COMPUTERNAME', 'LocalPC')}",
            "device_type": "windows",
            "mac_address": mac_address,
            "device_id": device_id
        },
        verify=False,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✓ Pairing successful!")
        print(f"\nDevice Credentials:")
        print(f"  Device ID: {data.get('device_id')}")
        print(f"  API Key: {data.get('api_key')}")
        
        # Create config.json
        config = {
            "backend_url": BACKEND_URL,
            "device_id": data.get('device_id'),
            "api_key": data.get('api_key'),
            "polling_interval": 30,
            "reporting_interval": 60
        }
        
        # Save to agent directory
        config_path = r"clients\windows\agent\config.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✓ Config saved to: {config_path}")
        print("\nYou can now run the agent:")
        print("  python dev/test_agent_exe.py")
        
    else:
        print(f"\n✗ Pairing failed: {response.text}")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
