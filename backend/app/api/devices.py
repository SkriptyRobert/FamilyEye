"""Device management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from ..database import get_db
from ..models import Device, User, PairingToken, UsageLog, Rule
from ..schemas import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceSettingsProtectionUpdate, PairingTokenResponse, PairingRequest, PairingResponse, PairingStatusResponse
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


@router.get("/pairing/status/{token}", response_model=PairingStatusResponse)
async def check_pairing_status(
    token: str,
    db: Session = Depends(get_db)
):
    """Check if a pairing token has been used."""
    import logging
    logger = logging.getLogger("pairing_status")
    
    logger.info(f"Checking pairing status for token: {token[:8]}...")
    
    pairing_token = db.query(PairingToken).filter(
        PairingToken.token == token
    ).first()
    
    if not pairing_token:
        logger.warning(f"Token not found: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pairing token not found"
        )
        
    device = None
    if pairing_token.used and pairing_token.device_id:
        device = db.query(Device).filter(Device.id == pairing_token.device_id).first()
        logger.info(f"Token used, device found: {device.name if device else 'None'}")
    else:
        logger.info(f"Token not used yet (used={pairing_token.used}, device_id={pairing_token.device_id})")
        
    return {
        "used": pairing_token.used,
        "device": device
    }

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
    
    # Delete all related data (files + specialized cleanup)
    from ..services.cleanup_service import cleanup_device_data
    cleanup_device_data(db, device_id)
    
    # Delete related data manually just in case cascade fails or logic changes
    
    # 1. Unlink or delete PairingTokens associated with this device
    from ..models import PairingToken
    # Set device_id to None for tokens used to pair this device (keep history)
    # OR delete them. Setting to None is safer to avoid FK error.
    db.query(PairingToken).filter(PairingToken.device_id == device_id).update({PairingToken.device_id: None})
    
    # 2. Delete usage logs (redundant if cascade is on, but safe)
    db.query(UsageLog).filter(UsageLog.device_id == device_id).delete()
    
    # 3. Delete rules
    db.query(Rule).filter(Rule.device_id == device_id).delete()
    
    # 4. Delete Shield Data (Keywords, Alerts are cascaded usually, but files handled by cleanup_device_data)
    
    # Finally Delete device
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
    
    # Try Real-Time Push
    from ..api.websocket import send_command_to_device
    await send_command_to_device(device.device_id, "LOCK_NOW")
    
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

    # Try Real-Time Push
    from ..api.websocket import send_command_to_device
    await send_command_to_device(device.device_id, "UNLOCK_NOW")
    
    return {"status": "success", "message": "Unlock command sent to device"}


# ... pause/resume internet (kept as is for now, or update later) ...


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

    # Try Real-Time Push
    from ..api.websocket import send_command_to_device
    await send_command_to_device(device.device_id, "SCREENSHOT_NOW")
    
    return {"status": "success", "message": "Screenshot requested from device"}


@router.post("/{device_id}/unlock-settings", status_code=status.HTTP_200_OK)
async def unlock_settings(
    device_id: int,
    duration_minutes: int = 5,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Temporarily minimize agent protection to allow settings changes.
    Creates an 'unlock_settings' rule for 5 minutes.
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
    
    # 1. Clean up old unlock rules
    from ..models import Rule
    db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "unlock_settings"
    ).delete()
    
    # 2. Create new time-bounded rule
    from datetime import datetime, timedelta, timezone
    
    # Calculate times
    now_utc = datetime.now(timezone.utc)
    offset_seconds = device.timezone_offset or 0
    device_now = now_utc + timedelta(seconds=offset_seconds)
    
    unlock_rule = Rule(
        device_id=device.id,
        rule_type="unlock_settings",
        enabled=True,
        # We use schedule times to signal validity window to the agent
        schedule_start_time=device_now.strftime("%H:%M"),
        schedule_end_time=(device_now + timedelta(minutes=duration_minutes)).strftime("%H:%M") 
    )
    db.add(unlock_rule)
    db.commit()
    
@router.post("/{device_id}/reset-pin", status_code=status.HTTP_200_OK)
async def reset_pin(
    device_id: int,
    request: dict, # Expects {"new_pin": "1234"}
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Remotely reset the PIN code for the Android application.
    Sends a 'RESET_PIN' command to the agent.
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
        
    new_pin = request.get("new_pin", "0000")
    
    # Validate PIN format (4-6 digits)
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be 4-6 digits"
        )
    
    # Try Real-Time Push
    from ..api.websocket import send_command_to_device
    # Command format: RESET_PIN:1234
    await send_command_to_device(device.device_id, f"RESET_PIN:{new_pin}")
    
    return {
        "status": "success", 
        "message": f"PIN reset command sent to device. New PIN: {new_pin}"
    }


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
    - 'full_with_exceptions': Block Settings except whitelisted areas (wifi, bluetooth, etc)
    - 'standard': Block only dangerous activities (legacy behavior)
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
    
    # Validate protection level
    valid_levels = {"full", "off"}
    if data.settings_protection not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid protection level. Must be one of: {valid_levels}"
        )
    
    # Update device
    device.settings_protection = data.settings_protection
    device.settings_exceptions = data.settings_exceptions
    db.commit()
    
    # Notify agent to refresh rules
    from ..api.websocket import send_command_to_device
    await send_command_to_device(device.device_id, "REFRESH_RULES")
    
    return {
        "status": "success",
        "settings_protection": device.settings_protection,
        "settings_exceptions": device.settings_exceptions
    }
