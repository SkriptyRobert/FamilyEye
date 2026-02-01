"""Device pairing endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Device, User, PairingToken
from ...schemas import PairingTokenResponse, PairingRequest, PairingResponse, PairingStatusResponse
from ..auth import get_current_parent
from ...services.pairing_service import (
    generate_pairing_token,
    generate_qr_code,
    create_device_from_pairing
)
from ...config import settings
from ...rate_limiter import check_rate_limit
from ...request_utils import get_client_ip

router = APIRouter()


@router.post("/token", response_model=PairingTokenResponse)
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


@router.get("/qr/{token}")
async def get_pairing_qr_code(
    token: str,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get QR code image for pairing token."""
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


@router.post("/pair", response_model=PairingResponse)
async def pair_device(
    request: Request,
    pairing_data: PairingRequest,
    db: Session = Depends(get_db)
):
    """Pair a new device using pairing token. Rate limited to 10/min per IP."""
    ip = get_client_ip(request)
    is_allowed, _, retry_after = check_rate_limit(ip, "pair", max_requests=10, window_seconds=60)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many pairing attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
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
            device_id=device.device_id,
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


@router.get("/status/{token}", response_model=PairingStatusResponse)
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
