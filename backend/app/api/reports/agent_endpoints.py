"""
Agent endpoints for reporting usage and critical events.

Split from monolithic reports.py for better maintainability.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from datetime import datetime, timedelta, timezone
import logging
import json

from ...database import get_db
from ...models import UsageLog, Device, Rule
from ...schemas import AgentReportRequest, CriticalEventRequest
from ..devices import verify_device_api_key
from ...services.app_filter import app_filter

router = APIRouter()
logger = logging.getLogger("agent_endpoints")

# In-memory cache for running processes per device
running_processes_cache: Dict[int, dict] = {}


@router.post("/agent/report", status_code=status.HTTP_201_CREATED)
async def agent_report_usage(
    request: AgentReportRequest,
    db: Session = Depends(get_db)
):
    """Agent endpoint to report usage statistics."""
    device = verify_device_api_key(request.device_id, request.api_key, db)
    
    # Update last_seen timestamp
    now_utc = datetime.now(timezone.utc)
    device.last_seen = now_utc
    
    # Calculate timezone offset
    if request.client_timestamp:
        client_ts = request.client_timestamp
        server_naive = now_utc.replace(tzinfo=None)
        if client_ts.tzinfo is not None:
            client_ts = client_ts.replace(tzinfo=None)
             
        diff = client_ts - server_naive
        offset_seconds = int(diff.total_seconds())
        
        if abs(device.timezone_offset - offset_seconds) > 60:
            device.timezone_offset = offset_seconds
            logger.debug(f"Updated timezone offset for device {device.id}: {offset_seconds}s")

    # Track first report of the day
    offset_seconds = device.timezone_offset or 0
    device_local_now = now_utc + timedelta(seconds=offset_seconds)
    today_local_str = device_local_now.strftime('%Y-%m-%d')
    
    needs_reset = False
    if device.first_report_today_utc:
        first_local = device.first_report_today_utc + timedelta(seconds=offset_seconds)
        first_day_str = first_local.strftime('%Y-%m-%d')
        needs_reset = (first_day_str != today_local_str)
    else:
        needs_reset = True
        
    if needs_reset:
        device.first_report_today_utc = now_utc
        logger.info(f"New day for device {device.id}: first_report_today_utc set to {now_utc.isoformat()}")

    logger.info(f"Received usage report from device {device.id} ({device.name}): {len(request.usage_logs)} logs")
    
    # Process usage logs
    total_duration = 0
    filtered_count = 0
    trackable_duration = 0
    
    for log_data in request.usage_logs:
        app_name = log_data.app_name
        is_trackable = app_filter.is_trackable(app_name)
        
        if not is_trackable:
            filtered_count += 1
            logger.debug(f"Filtered non-trackable app: {app_name}")
            continue
        
        friendly_name = app_filter.get_friendly_name(app_name)
        category = app_filter.get_category(app_name)
        
        usage_log = UsageLog(
            device_id=device.id,
            app_name=app_name,
            window_title=log_data.window_title,
            exe_path=log_data.exe_path,
            duration=log_data.duration,
            is_focused=log_data.is_focused,
            timestamp=log_data.timestamp or datetime.now(timezone.utc)
        )
        db.add(usage_log)
        total_duration += log_data.duration
        trackable_duration += log_data.duration
        logger.debug(f"  - {friendly_name} ({category or 'unknown'}): {log_data.duration}s")
    
    if filtered_count > 0:
        logger.info(f"Filtered {filtered_count} non-trackable app entries (backend filter)")
    
    db.commit()
    logger.info(f"Saved {len(request.usage_logs) - filtered_count} usage logs, trackable duration: {trackable_duration}s ({trackable_duration // 60}m)")
    
    # Store running processes
    if hasattr(request, 'running_processes') and request.running_processes:
        processes_json = json.dumps(request.running_processes)
        device.current_processes = processes_json
        
        running_processes_cache[device.id] = {
            "processes": request.running_processes,
            "updated_at": datetime.now(timezone.utc)
        }
        logger.debug(f"Saved {len(request.running_processes)} running processes for device {device.id}")
        
    db.add(device)
    db.commit()
    
    # Check for pending commands
    commands = []
    if device.screenshot_requested:
        commands.append({"type": "screenshot"})
        device.screenshot_requested = False
        db.add(device)
        db.commit()
        logger.info(f"Sent screenshot command to device {device.id}")
    
    return {
        "status": "success", 
        "logs_received": len(request.usage_logs), 
        "last_seen": device.last_seen.isoformat(),
        "commands": commands
    }


@router.post("/agent/screenshot", status_code=status.HTTP_201_CREATED)
async def agent_upload_screenshot(
    request: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Endpoint for agent to upload requested screenshot."""
    device_id = request.get("device_id")
    api_key = request.get("api_key")
    image_base64 = request.get("image")
    
    device = verify_device_api_key(device_id, api_key, db)
    
    logger.info(f"Received screenshot from device {device.id}")
    
    device.last_screenshot = f"data:image/jpeg;base64,{image_base64}"
    db.add(device)
    db.commit()
    
    return {"status": "success"}


@router.post("/agent/critical-event", status_code=status.HTTP_201_CREATED)
async def agent_critical_event(
    request: CriticalEventRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Agent endpoint for immediate critical event reporting.
    Called when: limit exceeded, app blocked, daily limit reached
    """
    device = verify_device_api_key(request.device_id, request.api_key, db)
    device.last_seen = datetime.now(timezone.utc)
    
    logger.warning(f"CRITICAL EVENT from device {device.id}: {request.event_type} - {request.app_name or 'N/A'}")
    
    # For limit_exceeded events, update usage log with actual time
    if request.event_type == 'limit_exceeded' and request.app_name and request.used_seconds:
        offset_seconds = device.timezone_offset or 0
        now_device = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
        local_midnight = now_device.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_utc = local_midnight - timedelta(seconds=offset_seconds)
        today_end_utc = today_start_utc + timedelta(days=1)
        
        current_usage = db.query(func.sum(UsageLog.duration)).filter(
            UsageLog.device_id == device.id,
            func.lower(UsageLog.app_name) == request.app_name.lower(),
            UsageLog.timestamp >= today_start_utc,
            UsageLog.timestamp < today_end_utc
        ).scalar() or 0
        
        diff = request.used_seconds - current_usage
        if diff > 0:
            usage_log = UsageLog(
                device_id=device.id,
                app_name=request.app_name,
                duration=diff,
                timestamp=request.timestamp or datetime.now(timezone.utc)
            )
            db.add(usage_log)
            logger.info(f"Added {diff}s to {request.app_name} usage (total now: {request.used_seconds}s)")
    
    db.commit()
    
    return {
        "status": "received",
        "event_type": request.event_type,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }


def get_running_processes_cache():
    """Get the running processes cache for other modules."""
    return running_processes_cache
