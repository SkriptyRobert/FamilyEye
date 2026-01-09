"""
Device-related endpoints for usage data and summaries.

Split from monolithic reports.py for better maintainability.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from datetime import datetime, timedelta, timezone
import logging

from ...database import get_db
from ...models import UsageLog, Device, User, Rule
from ...schemas import UsageLogResponse
from ..auth import get_current_parent
from ...services.app_filter import app_filter

router = APIRouter()
logger = logging.getLogger("device_endpoints")

# In-memory cache for running processes
running_processes_cache: Dict[int, dict] = {}


def get_running_processes_cache() -> Dict[int, dict]:
    """Get the running processes cache."""
    return running_processes_cache


def set_running_processes_cache(device_id: int, data: dict):
    """Set running processes for a device."""
    running_processes_cache[device_id] = data


@router.get("/device/{device_id}/usage", response_model=List[UsageLogResponse])
async def get_device_usage(
    device_id: int,
    days: int = 7,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get usage statistics for a device."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    usage_logs = db.query(UsageLog).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_date
    ).order_by(UsageLog.timestamp.desc()).all()
    
    results = []
    for log in usage_logs:
        if not app_filter.is_trackable(log.app_name):
            continue
            
        results.append({
            "id": log.id,
            "device_id": log.device_id,
            "app_name": log.app_name,
            "duration": log.duration,
            "timestamp": log.timestamp,
            "friendly_name": app_filter.get_friendly_name(log.app_name),
            "category": app_filter.get_category(log.app_name),
            "icon_type": app_filter.get_icon_type(log.app_name)
        })
    
    return results


@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_old_logs(
    days: int = 90,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Cleanup usage logs older than X days."""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    device_ids = db.query(Device.id).filter(Device.parent_id == current_user.id).all()
    device_ids = [d[0] for d in device_ids]
    
    deleted_count = db.query(UsageLog).filter(
        UsageLog.device_id.in_(device_ids),
        UsageLog.timestamp < cutoff_date
    ).delete(synchronize_session=False)
    
    db.commit()
    return {"status": "success", "deleted_count": deleted_count}
