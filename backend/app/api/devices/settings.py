"""Device settings management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Device, User
from ...schemas import DeviceSettingsProtectionUpdate
from ..auth import get_current_parent
from ..websocket import send_command_to_device

router = APIRouter()


@router.put("/{device_id}/settings-protection", status_code=status.HTTP_200_OK)
async def update_settings_protection(
    device_id: int,
    data: DeviceSettingsProtectionUpdate,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Update device settings protection level.
    
    Levels:
    - 'full': Block entire Settings app (maximum security)
    - 'off': Disable settings protection
    """
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    valid_levels = {"full", "partial", "off"}
    if data.settings_protection not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid protection level. Must be one of: {valid_levels}"
        )
    
    device.settings_protection = data.settings_protection
    device.settings_exceptions = data.settings_exceptions
    db.commit()
    
    await send_command_to_device(device.device_id, "REFRESH_RULES")
    
    return {
        "status": "success",
        "settings_protection": device.settings_protection,
        "settings_exceptions": device.settings_exceptions
    }
