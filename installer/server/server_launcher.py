import os
import sys
import webbrowser
import threading
import time
import argparse
import logging
import traceback
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import pystray

# Setup logging with multiple fallbacks
def setup_logging():
    log_paths = [
        Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "FamilyEye" / "Server" / "logs",
        Path(os.environ.get("TEMP", "C:\\Temp")) / "FamilyEyeLogs",
        Path(".").absolute() / "logs"
    ]
    
    for log_dir in log_paths:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "launcher.log"
            logging.basicConfig(
                filename=str(log_file),
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            return log_file
        except Exception:
            continue
    return None

log_file = setup_logging()
logger = logging.getLogger("Launcher")

# Standard console output (PyInstaller --console will show this)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

def setup_environment():
    """Setup paths and load configuration."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
        app_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.absolute()
        app_dir = base_dir

    backend_dir = base_dir / "backend"
    sys.path.insert(0, str(backend_dir))
    
    # Load .env
    env_path = app_dir / ".env"
    if env_path.exists():
        logger.info(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
    else:
        # Fallback
        legacy_env = app_dir / "backend" / ".env"
        if legacy_env.exists():
            load_dotenv(legacy_env)
    
    return base_dir


def run_tray_app(open_browser_on_start=False):
    """Run the system tray application."""
    logger.info("Starting Tray App...")
    
    # === Server Thread ===
    def start_server_thread():
        try:
            try:
                from run_https import main as start_backend
            except ImportError:
                from backend.run_https import main as start_backend
            
            logger.info("Starting backend...")
            start_backend()
        except Exception as e:
            logger.error(f"Server crashed: {e}")
            logger.error(traceback.format_exc())

    server_thread = threading.Thread(target=start_server_thread, daemon=True)
    server_thread.start()
    
    # === Tray Logic ===
    def on_open_dashboard(icon, item):
        try:
            from backend.app.config import get_local_ip
            ip = get_local_ip()
        except ImportError:
             # Try alternate import path if running from source/different structure
             try:
                 from app.config import get_local_ip
                 ip = get_local_ip()
             except:
                 ip = "localhost" # Last resort
        
        port = os.getenv("BACKEND_PORT", os.getenv("PORT", "8000"))
        
        # Ensure we don't default to localhost if we found a real IP
        if ip == "127.0.0.1":
             ip = "localhost"
             
        url = f"https://{ip}:{port}"
        logger.info(f"Opening dashboard at: {url}")
        webbrowser.open(url)
    
    def on_exit(icon, item):
        logger.info("User requested exit from tray.")
        icon.stop()
        sys.exit(0)

    # Load icon
    icon_path = None
    if getattr(sys, 'frozen', False):
         icon_path = Path(sys._MEIPASS) / "assets" / "server_icon.ico"
    else:
         icon_path = Path(__file__).parent / "assets" / "server_icon.ico"
    
    if not icon_path.exists():
        # Generate a simple icon if missing (fallback)
        image = Image.new('RGB', (64, 64), color = (73, 109, 137))
    else:
        try:
            image = Image.open(icon_path)
        except Exception as e:
             logger.error(f"Failed to load icon: {e}")
             image = Image.new('RGB', (64, 64), color = (255, 0, 0))

    menu = pystray.Menu(
        pystray.MenuItem("FamilyEye Server", lambda: None, enabled=False),
        pystray.MenuItem("Otevřít Dashboard", on_open_dashboard, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Ukončit", on_exit)
    )

    icon = pystray.Icon("FamilyEye", image, "FamilyEye Server", menu)
    
    if open_browser_on_start:
        threading.Timer(3.0, lambda: on_open_dashboard(icon, None)).start()
        
    logger.info("Running tray icon loop...")
    icon.run()

def main():
    try:
        parser = argparse.ArgumentParser(description="FamilyEye Server Launcher")
        parser.add_argument("--open-browser", action="store_true", help="Open browser on start (with Tray)")
        parser.add_argument("--launch-browser-only", action="store_true", help="Open browser and exit immediately")
        args = parser.parse_args()
        
        setup_environment()
        
        if args.launch_browser_only:
            # Just open the URL and die. Valid for Installer Post-Install.
            # Reuse the logic but without the Tray/Icon overhead.
            try:
                from backend.app.config import get_local_ip
                ip = get_local_ip()
            except ImportError:
                 try:
                     from app.config import get_local_ip
                     ip = get_local_ip()
                 except:
                     ip = "localhost"

            port = os.getenv("BACKEND_PORT", os.getenv("PORT", "8000"))
            
            if ip == "127.0.0.1":
                 ip = "localhost"
                 
            url = f"https://{ip}:{port}"
            logger.info(f"Opening dashboard (Standalone): {url}")
            webbrowser.open(url)
            sys.exit(0)

        # Normal mode - tray icon
        run_tray_app(open_browser_on_start=args.open_browser)
            
    except Exception as e:
        logger.critical(f"Launcher crashed: {e}")
        logger.critical(traceback.format_exc())
        if not sys.argv[1:].count("--init-admin"):
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Critical Error: {e}\nSee logs at {log_file}", "FamilyEye Server Error", 0x10)

if __name__ == "__main__":
    main()
