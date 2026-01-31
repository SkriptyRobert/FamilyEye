"""FastAPI main application."""
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import init_db, get_db
from .config import settings
from . import models
import logging
import sys
import asyncio
import re

# Setup logging to an OS-appropriate writable directory with rotation
import os
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

def _get_log_dir() -> Path:
    if os.environ.get("FAMILYEYE_SERVICE_MODE") == "1":
        program_data = Path(os.environ.get("ProgramData", "C:\\ProgramData"))
        return program_data / "FamilyEye" / "Server" / "logs"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "FamilyEye" / "Server" / "logs"
    return Path("logs")

log_dir = _get_log_dir()
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Timed rotating file handler – rotate at midnight, keep 5 souborů
file_handler = TimedRotatingFileHandler(
    filename=str(log_file),
    when="midnight",
    backupCount=5,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(console_formatter)

# Přidat handlery jen jednou (pokud ještě nejsou)
if not root_logger.handlers:
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


def _read_version() -> str:
    """Read version from repo root VERSION file."""
    try:
        repo_root = Path(__file__).resolve().parent.parent.parent
        version_file = repo_root / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning(f"Failed to read VERSION file: {e}")
    return "2.4.0"


# Initialize database
init_db()

app = FastAPI(
    title="FamilyEye API",
    description="Backend API for FamilyEye parental control system",
    version=_read_version()
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # Changed to True since we use specific origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info(f"FamilyEye Backend starting on {settings.HOST}:{settings.PORT}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    # Initialize SSL certificates if not exists
    try:
        from .ssl_manager import certificates_exist, generate_certificates, get_certificate_info
        if not certificates_exist():
            logger.info("SSL certificates not found, generating...")
            if generate_certificates():
                logger.info("SSL certificates generated successfully!")
            else:
                logger.warning("Failed to generate SSL certificates")
        else:
            info = get_certificate_info()
            logger.info(f"SSL certificates ready: {info.get('ca_subject', 'N/A')}")
    except Exception as e:
        logger.warning(f"SSL initialization skipped: {e}")

    # Start automated cleanup task
    # Start automated cleanup task
    asyncio.create_task(run_daily_cleanup())


async def run_daily_cleanup():
    """Run daily cleanup task in background."""
    while True:
        try:
            # Wait for initial startup (e.g. 1 minute)
            await asyncio.sleep(60) 
            
            logger.info("Running automated daily cleanup...")
            from .database import SessionLocal
            from .services.cleanup_service import cleanup_old_data
            
            db = SessionLocal()
            try:
                cleanup_old_data(db, retention_days_logs=90, retention_days_screenshots=30)
            finally:
                db.close()
            
            # Sleep for 24 hours
            logger.info("Cleanup finished. Next run in 24 hours.")
            await asyncio.sleep(24 * 3600)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in daily cleanup task: {e}")
            await asyncio.sleep(3600) # Retry in 1 hour



@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": app.version}


@app.get("/api/info")
async def get_server_info():
    """Get server information for client configuration."""
    from .config import get_local_ip
    
    local_ip = get_local_ip()
    return {
        "backend_url": settings.BACKEND_URL,
        "local_ip": local_ip,
        "port": settings.PORT,
        "host": settings.HOST,
        "version": app.version
    }


# Import routers
from .api import auth, devices, rules, reports, websocket, trust, files, shield
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(websocket.router, tags=["websocket"]) # No prefix, so it routes to /ws/...
app.include_router(trust.router, prefix="/api/trust", tags=["trust"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(shield.router, prefix="/api", tags=["shield"]) # Note: Router has "/shield" prefix internaly

# Uploads directory (screenshots served via authenticated /api/files/screenshots endpoint)
if os.environ.get("FAMILYEYE_SERVICE_MODE") == "1":
    app_data = os.getenv("ProgramData", "C:\\ProgramData")
    uploads_path = os.path.join(app_data, "FamilyEye", "Server", "uploads")
elif os.name == "nt":
    app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    uploads_path = os.path.join(app_data, "FamilyEye", "Server", "uploads")
else:
    uploads_path = os.path.join(os.getcwd(), "uploads")

os.makedirs(uploads_path, exist_ok=True)
# Screenshots only via /api/files/screenshots/{device_id}/{filename} (auth required).

def _get_android_version() -> str:
    """Extract version name from Android build.gradle.kts."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        gradle_path = os.path.join(base_dir, "clients", "android", "app", "build.gradle.kts")
        
        if os.path.exists(gradle_path):
            with open(gradle_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Match: versionName = "1.0.5"
                match = re.search(r'versionName\s*=\s*"([^"]+)"', content)
                if match:
                    return match.group(1)
    except Exception as e:
        logger.warning(f"Failed to parse Android version: {e}")
    return "latest"

# Helper for base path
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

base_path = get_base_path()

@app.get("/api/download/android-agent")
async def download_android_agent():
    """Download the latest Android Agent APK."""
    # Look in bundled assets or source
    # We need to ensure build_server_exe.py bundles this if we want it to work in exe
    apk_path = os.path.join(base_path, "clients", "android", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    
    if os.path.exists(apk_path):
        version = _get_android_version()
        return FileResponse(
            path=apk_path, 
            filename=f"FamilyEye-Agent-v{version}.apk", 
            media_type="application/vnd.android.package-archive"
        )
    return {"error": "APK file not found. Please build the Android project first."}

# Serve installer (Windows agent EXE from installer/agent/output)
installer_path = os.path.join(base_path, "installer", "agent", "output")
if os.path.exists(installer_path):
    app.mount("/installer", StaticFiles(directory=installer_path), name="installer")

# Serve Static Files (Frontend)
frontend_path = os.path.join(base_path, "frontend", "dist")

if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
    
    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/favicon.svg")
    async def serve_favicon():
        favicon_path = os.path.join(frontend_path, "favicon.svg")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path, media_type="image/svg+xml")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Favicon not found"})

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Do not intercept /api or /docs
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("redoc"):
            # Move on to other handlers
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        
        # Check if it's a static file that exists in dist folder
        static_path = os.path.join(frontend_path, full_path)
        
        if os.path.exists(static_path) and os.path.isfile(static_path):
            return FileResponse(static_path)
        
        # Serve index.html for all other routes (SPA fallback)
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    print(f"WARNING: Frontend dist not found at {frontend_path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)

