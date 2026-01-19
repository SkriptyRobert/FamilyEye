
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Device, ShieldKeyword, ShieldAlert
from ..schemas import ShieldKeywordCreate, ShieldKeywordResponse, ShieldAlertCreate, ShieldAlertResponse
from typing import List, Optional

router = APIRouter(prefix="/shield", tags=["smart-shield"])

from ..api.auth import get_current_parent
from ..models import User

# --- Keyword Management ---

@router.get("/keywords/{device_id}", response_model=List[ShieldKeywordResponse])
def get_keywords(
    device_id: int, 
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get all monitored keywords for a device."""
    # Verify ownership
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device: 
        raise HTTPException(status_code=404, detail="Device not found")
    if device.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return db.query(ShieldKeyword).filter(ShieldKeyword.device_id == device_id).all()

@router.post("/keywords", response_model=ShieldKeywordResponse)
def add_keyword(
    keyword_data: ShieldKeywordCreate, 
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Add a new keyword to monitor."""
    device = db.query(Device).filter(Device.id == keyword_data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device.parent_id != current_user.id:
         raise HTTPException(status_code=403, detail="Access denied")
        
    keyword = ShieldKeyword(
        device_id=keyword_data.device_id,
        keyword=keyword_data.keyword.lower(),
        category=keyword_data.category,
        severity=keyword_data.severity,
        enabled=True
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword

@router.delete("/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: int, 
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Remove a keyword."""
    keyword = db.query(ShieldKeyword).filter(ShieldKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
        
    # Check device ownership via keyword->device
    device = db.query(Device).filter(Device.id == keyword.device_id).first()
    if not device or device.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(keyword)
    db.commit()
    return {"status": "success"}

# --- Agent Endpoints ---

from ..schemas import AgentRulesRequest

@router.post("/agent/keywords", response_model=List[ShieldKeywordResponse])
def get_agent_keywords(auth: AgentRulesRequest, db: Session = Depends(get_db)):
    """Fetch keywords for a device (Agent only)."""
    device = db.query(Device).filter(Device.device_id == auth.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    if device.api_key != auth.api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    return db.query(ShieldKeyword).filter(ShieldKeyword.device_id == device.id).all()

# --- Alert Reporting (Agent) ---

@router.post("/alert", status_code=status.HTTP_201_CREATED)
async def report_alert(alert_data: ShieldAlertCreate, db: Session = Depends(get_db)):
    """Report a content detection alert from the agent."""
    # Lookup by string GUID
    device = db.query(Device).filter(Device.device_id == alert_data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Spam Prevention: Adaptive Burst Logic
    from datetime import datetime, timedelta, timezone
    
    # Use UTC for consistency
    now_utc = datetime.now(timezone.utc)
    
    # Fetch last 2 alerts for this specific detection pattern
    recent_alerts = db.query(ShieldAlert).filter(
        ShieldAlert.device_id == device.id,
        ShieldAlert.keyword == alert_data.keyword,
        ShieldAlert.app_name == alert_data.app_name
    ).order_by(ShieldAlert.timestamp.desc()).limit(2).all()
    
    if recent_alerts:
        last_alert = recent_alerts[0]
        
        # Ensure timezone awareness for comparison
        last_ts = last_alert.timestamp
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        
        time_since_last = (now_utc - last_ts).total_seconds()
        
        # 1. Absolute Spam Protection (always block sub-second duplicates)
        if time_since_last < 5: 
            return {"status": "alert_deduplicated_instant"}

        # 2. Burst Logic
        if len(recent_alerts) == 2:
            penultimate_alert = recent_alerts[1]
            penultimate_ts = penultimate_alert.timestamp
            if penultimate_ts.tzinfo is None:
                penultimate_ts = penultimate_ts.replace(tzinfo=timezone.utc)
            
            # Check gap between previous two alerts to determine mode
            gap_prev = (last_ts - penultimate_ts).total_seconds()
            
            # If previous alerts were close (Burst Mode detected)
            if gap_prev < 120: # Less than 2 minutes apart
                # Enforce long cooldown (5 minutes)
                if time_since_last < 300:
                    return {"status": "alert_deduplicated_cooldown"}
            
            # Else: Normal mode, just allow (subject to 5s instant check)

    # Clean screenshot URL to store relative path (Dynamic Domain Support)
    screenshot_url = alert_data.screenshot_url
    if screenshot_url and "/api/files/" in screenshot_url:
        screenshot_url = screenshot_url.split("/api/files/")[-1]

    alert = ShieldAlert(
        device_id=device.id, # Use internal SQL ID for relationship
        keyword=alert_data.keyword,
        app_name=alert_data.app_name,
        detected_text=alert_data.detected_text,
        screenshot_url=screenshot_url,
        severity=alert_data.severity,
        is_read=False
    )
    db.add(alert)
    db.commit()
    
    # Notify Parent via WebSocket
    try:
        from .websocket import notify_user
        
        # Determine full_url for websocket notification if needed based on schema logic
        # But schema logic only applies to Pydantic Response models.
        # WebSocket sends raw dict. We should send Full URL for immediate display, 
        # as frontend might not process WS payload through Pydantic.
        # However, frontend handles blob fetch. Blob fetch needs Full URL? 
        # Most likely yes, or relative to base.
        # Let's verify schema behavior: it prepends BACKEND_URL to relative paths.
        ws_screenshot_url = screenshot_url
        if ws_screenshot_url and not ws_screenshot_url.startswith("http"):
             from ..config import settings
             ws_screenshot_url = f"{settings.BACKEND_URL}/api/files/{ws_screenshot_url}"
        
        if hasattr(device, 'user_id') and device.user_id:
             await notify_user(device.user_id, {
                "type": "shield_alert",
                "device_id": device.id,
                "device_name": device.name,
                "keyword": alert.keyword,
                "app_name": alert.app_name,
                "severity": alert.severity,
                "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
                "screenshot_url": ws_screenshot_url
            })
    except Exception as e:
        print(f"Failed to send notification: {e}")
    
    return {"status": "alert_recorded"}

# --- Alert Viewing (Frontend) ---

@router.get("/alerts/{device_id}", response_model=List[ShieldAlertResponse])
def get_alerts(
    device_id: int, 
    limit: int = 50, 
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get recent alerts for a device."""
    # Verify ownership
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if device.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return db.query(ShieldAlert)\
        .filter(ShieldAlert.device_id == device_id)\
        .order_by(ShieldAlert.timestamp.desc())\
        .limit(limit)\
        .all()

# --- Alert Management ---

@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: int, 
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Delete an alert and its screenshot."""
    alert = db.query(ShieldAlert).filter(ShieldAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Verify ownership via alert->device->parent
    device = db.query(Device).filter(Device.id == alert.device_id).first()
    if not device or device.parent_id != current_user.id:
         raise HTTPException(status_code=403, detail="Access denied")
            
    # Delete screenshot if exists
    if alert.screenshot_url and "/static/uploads/" in alert.screenshot_url:
        try:
            # Extract relative path from URL
            # URL: .../static/uploads/screenshots/DEVICE/FILE
            relative_path = alert.screenshot_url.split("/static/uploads/")[-1]
            # Construct local path. Assuming CWD is backend root.
            # Local: upgrades/../uploads/.. ?? 
            # App runs in backend root. uploads is in backend/uploads.
            import os
            file_path = os.path.join("uploads", relative_path)
            
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting screenshot: {e}")

    db.delete(alert)
    db.commit()
    return {"status": "deleted"}

from pydantic import BaseModel

class BatchDeleteSchema(BaseModel):
    alert_ids: List[int]

@router.post("/alerts/batch-delete")
def batch_delete_alerts(
    payload: BatchDeleteSchema, 
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Delete multiple alerts."""
    # Only delete alerts where the device belongs to the current user
    alerts = db.query(ShieldAlert)\
        .join(Device)\
        .filter(
            ShieldAlert.id.in_(payload.alert_ids), 
            Device.parent_id == current_user.id
        ).all()
    
    count = 0
    import os
    
    for alert in alerts:
        # Delete screenshot
        if alert.screenshot_url and "/static/uploads/" in alert.screenshot_url:
            try:
                relative_path = alert.screenshot_url.split("/static/uploads/")[-1]
                file_path = os.path.join("uploads", relative_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        
        db.delete(alert)
        count += 1
        
    db.commit()
    return {"status": "deleted", "count": count}
