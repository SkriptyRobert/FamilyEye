"""FastAPI main application."""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import init_db, get_db
from .config import settings
from . import models
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Initialize database
init_db()

app = FastAPI(
    title="Parental Control API",
    description="Backend API for parental control system",
    version="1.0.0"
)

# CORS middleware - povolení všech originů pro development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pro development - v produkci použít konkrétní seznam
    allow_credentials=False,  # Musí být False když allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info(f"Parental Control Backend starting on {settings.HOST}:{settings.PORT}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    print(f"Parental Control Backend starting on {settings.HOST}:{settings.PORT}")
    print(f"Database: {settings.DATABASE_URL}")
    
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


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/info")
async def get_server_info():
    """Get server information for client configuration."""
    import socket
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    local_ip = get_local_ip()
    return {
        "backend_url": settings.BACKEND_URL,
        "local_ip": local_ip,
        "port": settings.PORT,
        "host": settings.HOST,
        "version": "1.0.0"
    }


# Import routers
from .api import auth, devices, rules, reports, websocket, trust
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(trust.router, prefix="/api/trust", tags=["trust"])

# Serve Static Files (Frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")

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

