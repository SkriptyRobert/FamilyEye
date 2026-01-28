import os
import shutil
import subprocess
from pathlib import Path

def build_exe():
    project_root = Path(__file__).parent.parent.parent
    installer_dir = Path(__file__).parent
    output_dir = installer_dir / "dist"
    
    # Clean previous build
    if output_dir.exists():
        shutil.rmtree(output_dir)
        
    print(f"Building Server Launcher from {project_root}...")
    
    # Navigate to project root for correct import resolution
    os.chdir(str(project_root))
    
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name", "FamilyEyeServer",
        "--console",  # Use console window to see errors
        "--icon", str(installer_dir / "assets" / "server_icon.ico"),
        
        # Include backend source code
        "--add-data", f"backend{os.pathsep}backend",
        
        # Include frontend build
        "--add-data", f"frontend/dist{os.pathsep}frontend/dist",
        
        # Include assets folder (for tray icon)
        "--add-data", f"installer/server/assets{os.pathsep}assets",
        
        # Add backend to search path so PyInstaller can find 'app' package
        "--paths", "backend",

        # Force analysis of the main backend entry point to find all dependencies
        "--hidden-import", "app.main",
        
        # Hidden imports often missed by analysis
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "fastapi",
        "--hidden-import", "fastapi.middleware.cors", # Explicitly added based on crash
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "jose",
        "--hidden-import", "passlib",
        "--hidden-import", "bcrypt",
        "--hidden-import", "passlib.handlers.bcrypt",
        "--hidden-import", "passlib.handlers.pbkdf2",
        "--hidden-import", "passlib.handlers.sha2_crypt",
        "--hidden-import", "multipart",
        "--hidden-import", "email_validator",
        "--hidden-import", "win32timezone",
        "--hidden-import", "win32service",
        "--hidden-import", "win32serviceutil",
        "--hidden-import", "servicemanager",
        
        # Main script (Service Wrapper)
        "backend/service.py"
    ]
    
    subprocess.run(cmd, check=True)
    
    print("Build complete! Check dist/FamilyEyeServer")

if __name__ == "__main__":
    build_exe()
