from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Device, User
from ..api.devices import verify_device_api_key
from ..api.auth import get_current_parent
import shutil
import os
import uuid
from datetime import datetime
from ..config import settings

router = APIRouter()

UPLOAD_DIR = "uploads"
SCREENSHOTS_DIR = os.path.join(UPLOAD_DIR, "screenshots")

# Ensure directories exist
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def get_current_device(
    api_key: str,
    device_id: str,
    db: Session = Depends(get_db)
) -> Device:
    # This is a simplified dependency. 
    # In reality, FastAPI dependency injection for Header/Query is needed.
    # We will use explicit verification in the endpoint for simplicity with UploadFile.
    return verify_device_api_key(device_id, api_key, db)


@router.get("/screenshots/{device_id}/{filename}")
async def get_screenshot(
    device_id: str,
    filename: str,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Get a screenshot file with authentication.
    Only authenticated parents can access screenshots.
    """
    # Verify device belongs to this parent
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or access denied"
        )
    
    # Construct file path safely (prevent path traversal)
    safe_filename = os.path.basename(filename)  # Strip any path components
    file_path = os.path.join(SCREENSHOTS_DIR, str(device_id), safe_filename)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
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
    
    # Update device record
    device.last_screenshot = full_url
    device.screenshot_requested = False
    db.commit()
    
    return {
        "status": "success",
        "url": full_url,
        "filename": filename
    }
