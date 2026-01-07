"""
Pair Local Agent with Dashboard
Uses the generated pairing token to configure the agent.
"""
import sys
import os
import subprocess

# Pairing details
BACKEND_URL = "https://192.168.0.145:8000"
PAIRING_TOKEN = "f82bb1ad-1415-4987-a057-2debfc008ec0"

print(f"\n{'='*60}")
print(f"Pairing Agent with Dashboard")
print(f"{'='*60}\n")
print(f"Backend URL: {BACKEND_URL}")
print(f"Pairing Token: {PAIRING_TOKEN}\n")

# Check if agent exe exists
agent_exe = r"installer\agent\dist\agent_service.exe"
if not os.path.exists(agent_exe):
    print(f"✗ Agent not found: {agent_exe}")
    print("Run: python installer/agent/build_agent.py")
    sys.exit(1)

# Run pairing command
print("Running pairing command...")
try:
    result = subprocess.run(
        [agent_exe, "--register"],
        input=f"{BACKEND_URL}\n{PAIRING_TOKEN}\n",
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    if result.returncode == 0:
        print("\n✓ Agent paired successfully!")
        print("\nAgent config should now be at:")
        print(r"  Dev: clients\windows\agent\config.json")
        print(r"  Production: C:\ProgramData\FamilyEye\Agent\config.json")
    else:
        print(f"\n✗ Pairing failed with code {result.returncode}")
        
except Exception as e:
    print(f"\n✗ Pairing error: {e}")
