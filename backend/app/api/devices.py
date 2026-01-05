"""Device management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from ..database import get_db
from ..models import Device, User
from ..schemas import DeviceCreate, DeviceUpdate, DeviceResponse, PairingTokenResponse, PairingRequest, PairingResponse
from ..api.auth import get_current_parent
from ..services.pairing_service import (
    generate_pairing_token,
    generate_qr_code,
    create_device_from_pairing
)
from ..config import settings

router = APIRouter()


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
    
    # Update last_seen - caller must commit
    from datetime import timezone
    device.last_seen = datetime.now(timezone.utc)
    # db.commit()  <-- Released to caller
    
    return device


@router.post("/pairing/token", response_model=PairingTokenResponse)
async def create_pairing_token(
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Create a new pairing token for device registration."""
    pairing_token = generate_pairing_token(current_user.id, db)
    
    pairing_url = f"parental-control://pair?token={pairing_token.token}&backend={settings.BACKEND_URL}"
    
    return PairingTokenResponse(
        token=pairing_token.token,
        expires_at=pairing_token.expires_at,
        pairing_url=pairing_url
    )


@router.get("/pairing/qr/{token}")
async def get_pairing_qr_code(
    token: str,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get QR code image for pairing token."""
    from ..models import PairingToken
    pairing_token = db.query(PairingToken).filter(
        PairingToken.token == token,
        PairingToken.parent_id == current_user.id
    ).first()
    
    if not pairing_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pairing token not found"
        )
    
    qr_code_image = generate_qr_code(pairing_token, settings.BACKEND_URL)
    
    return {"qr_code": qr_code_image, "token": token}


@router.post("/pairing/pair", response_model=PairingResponse)
async def pair_device(
    pairing_data: PairingRequest,
    db: Session = Depends(get_db)
):
    """Pair a new device using pairing token."""
    try:
        device = create_device_from_pairing(
            token=pairing_data.token,
            device_name=pairing_data.device_name,
            device_type=pairing_data.device_type,
            mac_address=pairing_data.mac_address,
            device_id=pairing_data.device_id,
            db=db
        )
        
        return PairingResponse(
            device_id=device.device_id,  # Return string device_id, not database ID
            api_key=device.api_key,
            backend_url=settings.BACKEND_URL
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"Pairing error: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {error_detail}"
        )


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
    
    # Generate new API key
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
    
    # Delete all related data
    from ..models import UsageLog, Rule
    
    # Delete usage logs
    db.query(UsageLog).filter(UsageLog.device_id == device_id).delete()
    
    # Delete rules
    db.query(Rule).filter(Rule.device_id == device_id).delete()
    
    # Delete device
    db.delete(device)
    db.commit()
    
    return None


@router.post("/{device_id}/lock", status_code=status.HTTP_200_OK)
async def lock_device(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Lock device remotely (instant action)."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Create a temporary lock rule
    from ..models import Rule
    lock_rule = Rule(
        device_id=device.id,
        rule_type="lock_device",
        enabled=True
    )
    db.add(lock_rule)
    db.commit()
    
    return {"status": "success", "message": "Lock command sent to device"}


@router.post("/{device_id}/unlock", status_code=status.HTTP_200_OK)
async def unlock_device(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Unlock device remotely."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Remove lock rules
    from ..models import Rule
    lock_rules = db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "lock_device"
    ).all()
    
    for rule in lock_rules:
        db.delete(rule)
    db.commit()
    
    return {"status": "success", "message": "Unlock command sent to device"}


@router.post("/{device_id}/pause-internet", status_code=status.HTTP_200_OK)
async def pause_internet(
    device_id: int,
    duration_minutes: int = 60,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Pause internet access for device (temporary block)."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Create temporary network block rule
    from ..models import Rule
    from datetime import datetime, timedelta
    
    # Use local time for schedule so it matches the device's clock and UI expectation
    now = datetime.now()
    block_rule = Rule(
        device_id=device.id,
        rule_type="network_block",
        enabled=True,
        schedule_start_time=now.strftime("%H:%M"),
        schedule_end_time=(now + timedelta(minutes=duration_minutes)).strftime("%H:%M")
    )
    db.add(block_rule)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Internet paused for {duration_minutes} minutes",
        "expires_at": (now + timedelta(minutes=duration_minutes)).isoformat()
    }


@router.post("/{device_id}/resume-internet", status_code=status.HTTP_200_OK)
async def resume_internet(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Resume internet access for device."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Remove network block rules
    from ..models import Rule
    block_rules = db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "network_block"
    ).all()
    
    for rule in block_rules:
        db.delete(rule)
    db.commit()
    
    return {"status": "success", "message": "Internet access resumed"}


@router.post("/{device_id}/request-screenshot", status_code=status.HTTP_200_OK)
async def request_screenshot(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Request a screenshot from the device (instant action)."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Set the flag for the next agent report to pick up
    device.screenshot_requested = True
    db.commit()
    
    return {"status": "success", "message": "Screenshot requested from device"}
