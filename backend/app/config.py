"""Configuration settings."""
import os
import socket
import secrets
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

def get_local_ip():
    """Get local IP address for network access."""
    try:
        # Method 1: Connect to external address (most reliable for finding primary interface)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    try:
        # Method 2: Get host by name (works if hostname is resolvable)
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip.startswith("127."):
             # Try to find a real interface
             from socket import gethostbyname_ex
             hostname, aliases, ips = gethostbyname_ex(hostname)
             for i in ips:
                 if not i.startswith("127."):
                     return i
        return ip
    except Exception:
        # Fallback to localhost
        return "127.0.0.1"

def _get_secret_key() -> str:
    """Get or generate SECRET_KEY securely."""
    env_key = os.getenv("SECRET_KEY", "")
    insecure_default = "your-secret-key-change-in-production"
    
    if env_key and env_key != insecure_default:
        return env_key
    
    # Auto-generate secure key for standalone/development use
    generated_key = secrets.token_urlsafe(32)
    logger.warning(
        "SECRET_KEY not set or using insecure default. "
        "Auto-generated secure key for this session. "
        "Set SECRET_KEY environment variable for production!"
    )
    return generated_key

class Settings:
    """Application settings."""
    
    # Security - auto-generate if not set
    SECRET_KEY: str = _get_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours
    
    # Database
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Path Resolution Logic
    if os.environ.get('FAMILYEYE_SERVICE_MODE') == '1':
        # Service Mode -> ProgramData (System-wide)
        _app_data = os.getenv('ProgramData', 'C:\\ProgramData')
        _db_dir = os.path.join(_app_data, "FamilyEye", "Server")
    elif os.name == 'nt':
        # Legacy/Tray Mode -> LocalAppData (User-specific)
        _app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        _db_dir = os.path.join(_app_data, "FamilyEye", "Server")
    else:
        # Dev/Linux
        _db_dir = _base_dir

    try:
        os.makedirs(_db_dir, exist_ok=True)
    except OSError:
        # If we can't create directory (permission issue), fallback to base
        logger.warning(f"Could not create DB directory at {_db_dir}, falling back to local.")
        _db_dir = _base_dir
        
    _default_db_path = os.path.join(_db_dir, 'parental_control.db')

    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")
    
    # Server
    HOST: str = os.getenv("BACKEND_HOST", os.getenv("HOST", "0.0.0.0"))  # Listen on all interfaces
    PORT: int = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    
    # Backend URL - use actual IP for network access
    _local_ip = get_local_ip()
    
    # Robust Protocol Detection: Check ALL possible cert locations
    _cert_found = False
    
    # 1. Check Service Mode Location (ProgramData)
    _prog_data = os.getenv('ProgramData', 'C:\\ProgramData')
    _service_cert = os.path.join(_prog_data, "FamilyEye", "Server", "certs", "server.crt")
    
    # 2. Check User Mode Location (LocalAppData)
    _local_app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    _user_cert = os.path.join(_local_app_data, "FamilyEye", "Server", "certs", "server.crt")
    
    # 3. Check Local Dev Location
    _dev_cert = os.path.join(_base_dir, "certs", "server.crt")

    if os.path.exists(_service_cert):
        _cert_found = True
    elif os.path.exists(_user_cert):
        _cert_found = True
    elif os.path.exists(_dev_cert):
        _cert_found = True
        
    _protocol = "https" if _cert_found else "http"
    
    # CRITICAL: Always use the detected IP and configured Port.
    # Do NOT trust localhost unless we explicitly want it.
    BACKEND_URL: str = os.getenv("BACKEND_URL", f"{_protocol}://{_local_ip}:{PORT}")
    
    # CORS - allow all for standalone/local network mode
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://localhost:3000",
        "https://localhost:5173",
        "http://127.0.0.1:3000",
        "https://127.0.0.1:3000",
        f"http://{_local_ip}:3000",
        f"https://{_local_ip}:3000",
        f"http://{_local_ip}:5173",
        f"https://{_local_ip}:5173",
        f"http://{_local_ip}:{PORT}",
        f"https://{_local_ip}:{PORT}",
        "https://localhost:8000",
        "http://localhost:8000",
    ]
    
    # Pairing
    PAIRING_TOKEN_EXPIRE_MINUTES: int = 5


settings = Settings()

