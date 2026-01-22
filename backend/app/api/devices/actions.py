"""Device instant actions (lock, unlock, internet control, etc.)."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ...database import get_db
from ...models import Device, User, Rule
from ..auth import get_current_parent
from ..websocket import send_command_to_device

router = APIRouter()


def _get_device(device_id: int, current_user: User, db: Session) -> Device:
    """Helper to get and validate device."""
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


@router.post("/{device_id}/lock", status_code=status.HTTP_200_OK)
async def lock_device(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Lock device remotely (instant action)."""
    device = _get_device(device_id, current_user, db)
    
    lock_rule = Rule(
        device_id=device.id,
        rule_type="lock_device",
        enabled=True
    )
    db.add(lock_rule)
    db.commit()
    
    await send_command_to_device(device.device_id, "LOCK_NOW")
    
    return {"status": "success", "message": "Lock command sent to device"}


@router.post("/{device_id}/unlock", status_code=status.HTTP_200_OK)
async def unlock_device(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Unlock device remotely."""
    device = _get_device(device_id, current_user, db)
    
    lock_rules = db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "lock_device"
    ).all()
    
    for rule in lock_rules:
        db.delete(rule)
    db.commit()

    await send_command_to_device(device.device_id, "UNLOCK_NOW")
    
    return {"status": "success", "message": "Unlock command sent to device"}


@router.post("/{device_id}/pause-internet", status_code=status.HTTP_200_OK)
async def pause_internet(
    device_id: int,
    duration_minutes: int = Query(60, ge=1, le=1440, description="Duration in minutes (1-1440)"),
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Pause internet access for a device (instant action)."""
    device = _get_device(device_id, current_user, db)
    
    now_utc = datetime.now(timezone.utc)
    offset_seconds = device.timezone_offset or 0
    device_now = now_utc + timedelta(seconds=offset_seconds)
    end_time = device_now + timedelta(minutes=duration_minutes)
    
    # Clean up existing temporary network_block rules
    db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "network_block",
        Rule.schedule_start_time.isnot(None),
        Rule.schedule_end_time.isnot(None)
    ).delete()
    
    # Create temporary network_block rule
    network_block_rule = Rule(
        device_id=device.id,
        rule_type="network_block",
        enabled=True,
        schedule_start_time=device_now.strftime("%H:%M"),
        schedule_end_time=end_time.strftime("%H:%M")
    )
    db.add(network_block_rule)
    db.commit()
    
    await send_command_to_device(device.device_id, "REFRESH_RULES")
    
    return {
        "status": "success",
        "message": f"Internet paused for {duration_minutes} minutes",
        "duration_minutes": duration_minutes
    }


@router.post("/{device_id}/resume-internet", status_code=status.HTTP_200_OK)
async def resume_internet(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Resume internet access for a device (instant action)."""
    device = _get_device(device_id, current_user, db)
    
    deleted_count = db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "network_block",
        Rule.schedule_start_time.isnot(None),
        Rule.schedule_end_time.isnot(None)
    ).delete()
    
    db.commit()
    
    await send_command_to_device(device.device_id, "REFRESH_RULES")
    
    return {
        "status": "success",
        "message": "Internet access resumed",
        "rules_removed": deleted_count
    }


@router.post("/{device_id}/request-screenshot", status_code=status.HTTP_200_OK)
async def request_screenshot(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Request a screenshot from the device (instant action)."""
    device = _get_device(device_id, current_user, db)
    
    device.screenshot_requested = True
    db.commit()

    await send_command_to_device(device.device_id, "SCREENSHOT_NOW")
    
    return {"status": "success", "message": "Screenshot requested from device"}


@router.post("/{device_id}/unlock-settings", status_code=status.HTTP_200_OK)
async def unlock_settings(
    device_id: int,
    duration_minutes: int = 5,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Temporarily minimize agent protection to allow settings changes."""
    device = _get_device(device_id, current_user, db)
    
    db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.rule_type == "unlock_settings"
    ).delete()
    
    now_utc = datetime.now(timezone.utc)
    offset_seconds = device.timezone_offset or 0
    device_now = now_utc + timedelta(seconds=offset_seconds)
    
    unlock_rule = Rule(
        device_id=device.id,
        rule_type="unlock_settings",
        enabled=True,
        schedule_start_time=device_now.strftime("%H:%M"),
        schedule_end_time=(device_now + timedelta(minutes=duration_minutes)).strftime("%H:%M") 
    )
    db.add(unlock_rule)
    db.commit()


@router.post("/{device_id}/reset-pin", status_code=status.HTTP_200_OK)
async def reset_pin(
    device_id: int,
    request: dict,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Remotely reset the PIN code for the Android application."""
    device = _get_device(device_id, current_user, db)
        
    new_pin = request.get("new_pin", "0000")
    
    if not new_pin.isdigit() or len(new_pin) < 4 or len(new_pin) > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be 4-6 digits"
        )
    
    await send_command_to_device(device.device_id, f"RESET_PIN:{new_pin}")
    
    return {
        "status": "success", 
        "message": f"PIN reset command sent to device. New PIN: {new_pin}"
    }
