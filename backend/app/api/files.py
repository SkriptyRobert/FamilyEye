from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Device
from ..api.devices import verify_device_api_key
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
        
    # Generate URL (Assuming static mount at /static/uploads)
    # relative path: screenshots/{device_id}/{filename}
    # full url: {BACKEND_URL}/static/uploads/screenshots/{device_id}/{filename}
    
    relative_path = f"screenshots/{device.device_id}/{filename}"
    full_url = f"{settings.BACKEND_URL}/static/uploads/{relative_path}"
    
    # Update device record
    device.last_screenshot = full_url
    device.screenshot_requested = False
    db.commit()
    
    return {
        "status": "success",
        "url": full_url,
        "filename": filename
    }
