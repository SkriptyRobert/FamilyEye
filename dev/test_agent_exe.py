"""
Simple Agent Test - Just run the exe and monitor
"""
import subprocess
import time
import os
from datetime import datetime

def main():
    print(f"\n{'#'*60}")
    print(f"# FamilyEye Agent - Local Test (EXE)")
    print(f"# Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")
    
    # Path to exe
    exe_path = r"installer\agent\dist\agent_service.exe"
    
    if not os.path.exists(exe_path):
        print(f"✗ Agent exe not found: {exe_path}")
        print("Run: python installer/agent/build_agent.py")
        return
    
    print(f"Running: {exe_path}")
    print(f"Press Ctrl+C to stop\n")
    print(f"{'='*60}\n")
    
    try:
        # Run agent in foreground
        process = subprocess.Popen(
            [exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output
        for line in process.stdout:
            print(line.strip())
            
    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user")
        if process:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    main()
