"""
Device summary endpoint.

Thin API layer - business logic is in services/summary_service.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import logging

from ...database import get_db
from ...models import UsageLog, Device, User, Rule
from ...api.auth import get_current_parent
from ...services.app_filter import app_filter
from ...services import summary_service

# Import running_processes_cache from sibling module
from .device_endpoints import running_processes_cache

router = APIRouter()
logger = logging.getLogger("reports")


@router.get("/device/{device_id}/summary")
async def get_device_summary(
    device_id: int,
    date: str = None,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Get usage summary for a device including Smart Insights.
    
    This is the main dashboard data endpoint, containing:
    - Today's usage statistics
    - Top apps with time limits
    - Smart Insights (focus, wellness, anomalies)
    - Running processes
    """
    logger.info(f"get_device_summary called for device_id={device_id}")
    
    # Verify device belongs to parent
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Calculate time boundaries
    time_bounds = _calculate_time_boundaries(device, date)
    
    # Get precise usage
    today_usage, elapsed_today_seconds = summary_service.calculate_precise_usage(
        db, device_id, time_bounds['today_start_utc'], time_bounds['today_end_utc']
    )
    
    # Get top apps and apply consistency check
    top_apps_query = _get_top_apps_query(
        db, device_id, time_bounds['today_start_utc'], time_bounds['today_end_utc']
    )
    
    # Consistency check
    if top_apps_query:
        max_app_usage = top_apps_query[0].total_duration or 0
        if max_app_usage > today_usage:
            today_usage = int(max_app_usage)
            elapsed_today_seconds = today_usage

    # Build response data
    return _build_summary_response(
        db=db,
        device=device,
        device_id=device_id,
        time_bounds=time_bounds,
        today_usage=today_usage,
        elapsed_today_seconds=elapsed_today_seconds,
        top_apps_query=top_apps_query
    )


def _calculate_time_boundaries(device: Device, date: str = None) -> dict:
    """Calculate all time-related boundaries for the summary."""
    now_utc = datetime.now(timezone.utc)
    offset_seconds = device.timezone_offset or 0
    device_local_now = now_utc + timedelta(seconds=offset_seconds)
    
    if date:
        try:
            from dateutil import parser
            dt = parser.parse(date)
            local_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            is_historical = True
        except Exception:
            local_midnight = device_local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            is_historical = False
    else:
        local_midnight = device_local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        is_historical = False

    today_start_utc = local_midnight - timedelta(seconds=offset_seconds)
    today_end_utc = today_start_utc + timedelta(days=1)
    today_str = local_midnight.strftime('%Y-%m-%d')
    
    return {
        'today_start_utc': today_start_utc,
        'today_end_utc': today_end_utc,
        'today_str': today_str,
        'yesterday_start_utc': today_start_utc - timedelta(days=1),
        'yesterday_end_utc': today_start_utc,
        'is_historical': is_historical,
        'offset_seconds': offset_seconds
    }


def _get_top_apps_query(db: Session, device_id: int, start_utc: datetime, end_utc: datetime):
    """Get top apps by usage duration."""
    return db.query(
        UsageLog.app_name,
        func.sum(UsageLog.duration).label('total_duration')
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc,
        UsageLog.timestamp < end_utc
    ).group_by(UsageLog.app_name).order_by(
        func.sum(UsageLog.duration).desc()
    ).limit(100).all()


def _build_summary_response(
    db: Session,
    device: Device,
    device_id: int,
    time_bounds: dict,
    today_usage: int,
    elapsed_today_seconds: int,
    top_apps_query
) -> dict:
    """Build the complete summary response."""
    
    start_utc = time_bounds['today_start_utc']
    end_utc = time_bounds['today_end_utc']
    is_historical = time_bounds['is_historical']
    offset_seconds = time_bounds['offset_seconds']
    
    # First report tracking
    first_report_iso = _get_first_report_iso(device, time_bounds)
    
    # Window titles
    latest_titles = summary_service.get_latest_window_titles(db, device_id, start_utc, end_utc)
    
    # Stats
    apps_today = len(set(log.app_name for log in top_apps_query))
    active_rules = db.query(Rule).filter(Rule.device_id == device_id, Rule.enabled == True).count()
    total_usage_all = db.query(func.sum(UsageLog.duration)).filter(UsageLog.device_id == device_id).scalar() or 0
    last_usage = db.query(func.max(UsageLog.timestamp)).filter(UsageLog.device_id == device_id).scalar()
    
    # Historical comparisons
    yesterday_usage = summary_service.calculate_day_usage(
        db, device_id, time_bounds['yesterday_start_utc'], time_bounds['yesterday_end_utc']
    )
    week_avg = summary_service.calculate_week_average(db, device_id, start_utc)
    
    # Rules and limits
    apps_with_limits = summary_service.get_apps_with_limits(db, device_id, start_utc, end_utc)
    daily_limit_info = summary_service.get_daily_limit_info(db, device_id, today_usage)
    active_schedules = summary_service.get_active_schedules(db, device_id)
    
    # Smart Insights
    insights = summary_service.calculate_smart_insights(
        db, device_id, start_utc, end_utc, today_usage, apps_with_limits
    )
    
    # Running processes (only for today)
    running_procs_data = running_processes_cache.get(device_id, {}) if not is_historical else {}
    running_processes = running_procs_data.get("processes", [])
    running_processes_updated = running_procs_data.get("updated_at")
    
    # Format timestamps
    last_seen_iso = _format_last_seen(device)
    
    # Process top apps
    final_top_apps = _process_top_apps(top_apps_query, latest_titles)

    return {
        "device_id": device_id,
        "device_name": device.name,
        "is_online": device.is_online,
        "today_usage_seconds": today_usage,
        "today_usage_hours": round(today_usage / 3600, 2),
        "elapsed_today_seconds": elapsed_today_seconds,
        "first_report_today": first_report_iso,
        "yesterday_usage_seconds": yesterday_usage,
        "week_avg_seconds": week_avg,
        "total_usage_seconds": total_usage_all,
        "total_usage_hours": round(total_usage_all / 3600, 2),
        "apps_used_today": apps_today,
        "top_apps": final_top_apps,
        "active_rules": active_rules,
        "apps_with_limits": apps_with_limits,
        "daily_limit": daily_limit_info,
        "schedules": active_schedules,
        "last_seen": last_seen_iso,
        "last_usage": last_usage,
        "paired_at": device.paired_at,
        "is_historical": is_historical,
        "date_selected": time_bounds['today_str'],
        "insights": insights,
        "running_processes": running_processes,
        "running_processes_updated": running_processes_updated.isoformat() if running_processes_updated else None,
        "activity_timeline": summary_service.get_activity_timeline(db, device_id, start_utc, end_utc)
    }


def _get_first_report_iso(device: Device, time_bounds: dict) -> str | None:
    """Get first report timestamp in ISO format."""
    if not device.first_report_today_utc or time_bounds['is_historical']:
        return None
        
    first_utc = device.first_report_today_utc
    if first_utc.tzinfo is not None:
        first_utc = first_utc.replace(tzinfo=None)
    
    first_local = first_utc + timedelta(seconds=time_bounds['offset_seconds'])
    if first_local.strftime('%Y-%m-%d') == time_bounds['today_str']:
        return device.first_report_today_utc.isoformat()
    return None


def _format_last_seen(device: Device) -> str | None:
    """Format last_seen timestamp."""
    if not device.last_seen:
        return None
    ls = device.last_seen
    if ls.tzinfo is None:
        ls = ls.replace(tzinfo=timezone.utc)
    return ls.isoformat()


def _process_top_apps(top_apps_query, latest_titles: dict) -> list:
    """Process and deduplicate top apps by friendly name."""
    top_apps_map = {}
    
    for app in top_apps_query:
        if not app_filter.is_trackable(app[0]):
            continue

        raw_name = app[0]
        duration = app[1]
        friendly_name = app_filter.get_friendly_name(raw_name)
        
        key = friendly_name.lower()
        
        if key in top_apps_map:
            top_apps_map[key]["duration_seconds"] += duration
            top_apps_map[key]["display_name"] = friendly_name 
        else:
            top_apps_map[key] = {
                "app_name": raw_name,
                "duration_seconds": duration,
                "display_name": friendly_name,
                "window_title": latest_titles.get(raw_name, ""),
                "category": app_filter.get_category(raw_name),
                "icon_type": app_filter.get_icon_type(raw_name)
            }
            
    return sorted(
        top_apps_map.values(), 
        key=lambda x: x["duration_seconds"], 
        reverse=True
    )
