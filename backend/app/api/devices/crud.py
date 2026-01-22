"""Device CRUD operations."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from ...database import get_db
from ...models import Device, User, UsageLog, Rule, PairingToken
from ...schemas import DeviceUpdate, DeviceResponse
from ..auth import get_current_parent
from ...services.cleanup_service import cleanup_device_data

router = APIRouter()


@router.get("/", response_model=List[DeviceResponse])
async def get_devices(
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get all devices for current parent."""
    devices = db.query(Device).filter(Device.parent_id == current_user.id).all()
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get device by ID."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return device


@router.post("/{device_id}/regenerate-api-key", response_model=DeviceResponse)
async def regenerate_api_key(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Regenerate API key for a device."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    new_api_key = str(uuid.uuid4())
    device.api_key = new_api_key
    db.commit()
    db.refresh(device)
    
    return device


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Update a device (e.g. rename)."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if device_update.name is not None:
        device.name = device_update.name
        
    db.commit()
    db.refresh(device)
    
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Delete a device and all its data."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    cleanup_device_data(db, device_id)
    
    db.query(PairingToken).filter(PairingToken.device_id == device_id).update({PairingToken.device_id: None})
    db.query(UsageLog).filter(UsageLog.device_id == device_id).delete()
    db.query(Rule).filter(Rule.device_id == device_id).delete()
    
    db.delete(device)
    db.commit()
    
    return None
