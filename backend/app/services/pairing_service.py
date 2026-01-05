"""Pairing service for device registration."""
import uuid
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta, timezone as dt_timezone
from sqlalchemy.orm import Session
from ..models import PairingToken, Device, User
from ..config import settings


def generate_pairing_token(parent_id: int, db: Session) -> PairingToken:
    """Generate a new pairing token."""
    token = str(uuid.uuid4())
    # datetime.utcnow is naive, but let's stick to what worked before or serve what the DB expects
    expires_at = datetime.utcnow() + timedelta(minutes=settings.PAIRING_TOKEN_EXPIRE_MINUTES)
    
    pairing_token = PairingToken(
        token=token,
        parent_id=parent_id,
        expires_at=expires_at
    )
    db.add(pairing_token)
    db.commit()
    db.refresh(pairing_token)
    
    return pairing_token


def validate_pairing_token(token: str, db: Session) -> PairingToken:
    """Validate and return pairing token if valid."""
    pairing_token = db.query(PairingToken).filter(
        PairingToken.token == token,
        PairingToken.used == False,
        PairingToken.expires_at > datetime.utcnow()
    ).first()
    
    if not pairing_token:
        raise ValueError("Invalid or expired pairing token")
    
    return pairing_token


def generate_qr_code(pairing_token: PairingToken, backend_url: str) -> str:
    """Generate QR code image as base64 string."""
    pairing_url = f"parental-control://pair?token={pairing_token.token}&backend={backend_url}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(pairing_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)  # Reset position to beginning
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def create_device_from_pairing(
    token: str,
    device_name: str,
    device_type: str,
    mac_address: str,
    device_id: str,
    db: Session
) -> Device:
    """Create device from pairing token."""
    pairing_token = validate_pairing_token(token, db)
    
    # Check if device already exists by device_id
    existing_device_by_id = db.query(Device).filter(
        Device.device_id == device_id
    ).first()
    
    if existing_device_by_id:
        raise ValueError("Device already paired with this device_id")
    
    # Check if device with same MAC address already exists
    # If it exists, we allow re-pairing (update existing device)
    existing_device_by_mac = db.query(Device).filter(
        Device.mac_address == mac_address
    ).first()
    
    if existing_device_by_mac:
        # Update existing device instead of creating new one
        # This allows re-pairing the same physical device
        existing_device_by_mac.device_id = device_id
        existing_device_by_mac.name = device_name
        existing_device_by_mac.device_type = device_type
        # Generate new API key for security
        api_key = str(uuid.uuid4())
        existing_device_by_mac.api_key = api_key
        existing_device_by_mac.parent_id = pairing_token.parent_id
        existing_device_by_mac.is_active = True
        
        # Mark token as used
        pairing_token.used = True
        pairing_token.device_id = existing_device_by_mac.id
        
        db.commit()
        db.refresh(existing_device_by_mac)
        
        return existing_device_by_mac
    
    # Generate API key
    api_key = str(uuid.uuid4())
    
    # Create device
    new_device = Device(
        name=device_name,
        device_type=device_type,
        mac_address=mac_address,
        device_id=device_id,
        parent_id=pairing_token.parent_id,
        api_key=api_key
    )
    db.add(new_device)
    
    # Mark token as used
    pairing_token.used = True
    pairing_token.device_id = new_device.id
    
    db.commit()
    db.refresh(new_device)
    
    return new_device

