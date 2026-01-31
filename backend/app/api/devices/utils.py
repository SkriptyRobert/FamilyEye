"""Device utility functions."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ...models import Device


def verify_device_api_key(device_id: str, api_key: str, db: Session) -> Device:
    """Verify device API key and return device."""
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.api_key == api_key
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials"
        )
    
    device.last_seen = datetime.now(timezone.utc)
    
    return device
