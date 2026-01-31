from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Device, User
from ..api.devices.utils import verify_device_api_key
from ..api.auth import get_current_parent, get_user_from_token_string, get_current_user
import shutil
import os
import uuid
from datetime import datetime
from ..config import settings

router = APIRouter()
security = HTTPBearer(auto_error=False) # Allow manual handling

if os.environ.get('FAMILYEYE_SERVICE_MODE') == '1':
    # Service Mode -> ProgramData
    app_data = os.getenv('ProgramData', 'C:\\ProgramData')
    UPLOAD_DIR = os.path.join(app_data, "FamilyEye", "Server", "uploads")
elif os.name == 'nt':
    app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    UPLOAD_DIR = os.path.join(app_data, "FamilyEye", "Server", "uploads")
else:
    UPLOAD_DIR = "uploads" # Linux/Mac (or Docker) uses relative

SCREENSHOTS_DIR = os.path.join(UPLOAD_DIR, "screenshots")

# Ensure directories exist
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_current_device(
    api_key: str,
    device_id: str,
    db: Session = Depends(get_db)
) -> Device:
    # Simplified: explicit verification in endpoint (no Header/Query DI for UploadFile).
    return verify_device_api_key(device_id, api_key, db)

async def get_current_parent_allow_query(
    request: Request,
    token: Optional[str] = Query(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from Header OR Query param (for img tags).
    """
    token_str = None
    
    # 1. Try Header
    if auth and auth.credentials:
        token_str = auth.credentials
    
    # 2. Try Query Param
    if not token_str and token:
        token_str = token
        
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Validation logic reused from auth.py
    user = get_user_from_token_string(token_str, db)
    
    if user.role != "parent":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents can access this resource"
        )
        
    return user


@router.get("/screenshots/{device_id}/{filename}")
async def get_screenshot(
    device_id: str,
    filename: str,
    current_user: User = Depends(get_current_parent_allow_query),
    db: Session = Depends(get_db)
):
    """
    Get a screenshot file with authentication.
    Only authenticated parents can access screenshots.
    Supports ?token=XYZ for contexts where headers can't be set (e.g. img tags).
    """
    # Verify device belongs to this parent
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.parent_id == current_user.id # or user checks if not explicitly parent_id (future proofing)
    ).first()
    
    # Schema uses parent_id; expansion to User->Device relation possible later.
    if not device:
         d_check = db.query(Device).filter(Device.device_id == device_id).first()
         if d_check and d_check.parent_id != current_user.id:
              pass  # Strict parent_id check; multi-parent expansion elsewhere
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or access denied"
        )
    
    # Construct file path safely (prevent path traversal)
    safe_filename = os.path.basename(filename)  # Strip any path components
    file_path = os.path.join(SCREENSHOTS_DIR, str(device_id), safe_filename)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        # File missing (e.g. lost on container restart). Clear broken reference so UI stops requesting it.
        if device.last_screenshot:
            device.last_screenshot = None
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )
    
    # Determine media type
    ext = os.path.splitext(file_path)[1].lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(file_path, media_type=media_type)


@router.post("/upload/screenshot")
async def upload_screenshot(
    device_id: str, # passed as query or form? Query is easier for client.
    api_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a screenshot from a device."""
    # Verify Device
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.api_key == api_key
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )
    
    # Create device directory
    device_dir = os.path.join(SCREENSHOTS_DIR, str(device.device_id))
    os.makedirs(device_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"screenshot_{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(device_dir, filename)
    
    # Validate file content (Basic Magic Number check)
    header = await file.read(1024)
    await file.seek(0)
    
    if not (header.startswith(b'\xff\xd8') or # JPEG
            header.startswith(b'\x89PNG\r\n\x1a\n') or # PNG
            header.startswith(b'RIFF') and header[8:12] == b'WEBP'): # WEBP
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid image file format. Only JPG, PNG, WEBP are allowed."
        )

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
        
    # Generate authenticated URL (requires JWT to access)
    # Format: {BACKEND_URL}/api/files/screenshots/{device_id}/{filename}
    relative_path = f"screenshots/{device.device_id}/{filename}"
    full_url = f"{settings.BACKEND_URL}/api/files/{relative_path}"
    
    # Update device record (Store RELATIVE path for dynamism)
    device.last_screenshot = relative_path
    device.screenshot_requested = False
    db.commit()
    
    return {
        "status": "success",
        "url": full_url,
        "filename": filename
    }
