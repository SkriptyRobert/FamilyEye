
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Device, ShieldKeyword, ShieldAlert
from ..schemas import ShieldKeywordCreate, ShieldKeywordResponse, ShieldAlertCreate, ShieldAlertResponse
from typing import List, Optional

router = APIRouter(prefix="/shield", tags=["smart-shield"])

# --- Keyword Management ---

@router.get("/keywords/{device_id}", response_model=List[ShieldKeywordResponse])
def get_keywords(device_id: int, db: Session = Depends(get_db)):
    """Get all monitored keywords for a device."""
    # Note: Access control should be here (parent check)
    # For now, relying on device_id validity check in database
    return db.query(ShieldKeyword).filter(ShieldKeyword.device_id == device_id).all()

@router.post("/keywords", response_model=ShieldKeywordResponse)
def add_keyword(keyword_data: ShieldKeywordCreate, db: Session = Depends(get_db)):
    """Add a new keyword to monitor."""
    device = db.query(Device).filter(Device.id == keyword_data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
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
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Remove a keyword."""
    keyword = db.query(ShieldKeyword).filter(ShieldKeyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    
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
def report_alert(alert_data: ShieldAlertCreate, db: Session = Depends(get_db)):
    """Report a content detection alert from the agent."""
    # Lookup by string GUID
    device = db.query(Device).filter(Device.device_id == alert_data.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Spam Prevention: Check for duplicate alert in last 60 seconds
    from datetime import datetime, timedelta, timezone
    
    # 1. Get recent alerts for this device
    recent_threshold = datetime.utcnow() - timedelta(seconds=60)
    
    existing_alert = db.query(ShieldAlert).filter(
        ShieldAlert.device_id == device.id,
        ShieldAlert.keyword == alert_data.keyword,
        ShieldAlert.app_name == alert_data.app_name,
        ShieldAlert.timestamp >= recent_threshold
    ).first()
    
    if existing_alert:
        # Duplicate validation - return success but don't save
        return {"status": "alert_deduplicated"}

    alert = ShieldAlert(
        device_id=device.id, # Use internal SQL ID for relationship
        keyword=alert_data.keyword,
        app_name=alert_data.app_name,
        detected_text=alert_data.detected_text,
        screenshot_url=alert_data.screenshot_url,
        severity=alert_data.severity,
        is_read=False
    )
    db.add(alert)
    db.commit()
    return {"status": "alert_recorded"}

# --- Alert Viewing (Frontend) ---

    return db.query(ShieldAlert)\
        .filter(ShieldAlert.device_id == device_id)\
        .order_by(ShieldAlert.timestamp.desc())\
        .limit(limit)\
        .all()

# --- Alert Management ---

@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert and its screenshot."""
    alert = db.query(ShieldAlert).filter(ShieldAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
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
def batch_delete_alerts(payload: BatchDeleteSchema, db: Session = Depends(get_db)):
    """Delete multiple alerts."""
    alerts = db.query(ShieldAlert).filter(ShieldAlert.id.in_(payload.alert_ids)).all()
    
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
