"""Configuration settings."""
import os
import socket
from typing import Optional

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

class Settings:
    """Application settings."""
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
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
    BACKEND_URL: str = os.getenv("BACKEND_URL", f"http://{_local_ip}:{PORT}")
    
    # CORS - allow all for standalone/local network mode
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        f"http://{_local_ip}:3000",
        f"http://{_local_ip}:5173",
        f"http://{_local_ip}:5174",
        "*",  # Allow all for standalone/local network mode
    ]
    
    # Pairing
    PAIRING_TOKEN_EXPIRE_MINUTES: int = 5


settings = Settings()

