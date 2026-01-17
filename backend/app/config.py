"""Configuration settings."""
import os
import socket
import secrets
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_local_ip():
    """Get local IP address for network access."""
    try:
        # Connect to external address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
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
        "⚠️ SECRET_KEY not set or using insecure default. "
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
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(_base_dir, 'parental_control.db')}")
    
    # Server
    HOST: str = os.getenv("BACKEND_HOST", os.getenv("HOST", "0.0.0.0"))  # Listen on all interfaces
    PORT: int = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    
    # Backend URL - use actual IP for network access
    _local_ip = get_local_ip()
    _protocol = "https" if os.path.exists(os.path.join(_base_dir, "certs", "server.crt")) else "http"
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

