"""
Statistics calculation service.

Common helpers for stats endpoints to reduce code duplication.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dateutil import parser

from ..models import UsageLog
from ..db_utils import minute_bucket, hour_expr, day_range_utc


def get_app_name_variants(app_name: str) -> List[str]:
    """Get all possible variants of an app name for case-insensitive matching."""
    app_name_lower = app_name.lower()
    return [app_name_lower, f"{app_name_lower}.exe"]


def calculate_day_usage_minutes(
    db: Session, 
    device_id: int, 
    day_str: str
) -> int:
    """
    Calculate unique minutes of usage for a specific day.
    
    Uses minute-bucket deduplication for accurate usage calculation.
    """
    day_start, day_end = day_range_utc(day_str)
    unique_minutes = db.query(
        func.count(func.distinct(minute_bucket(db, UsageLog.timestamp)))
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= day_start,
        UsageLog.timestamp < day_end
    ).scalar() or 0
    return unique_minutes


def calculate_day_usage_range(
    db: Session, 
    device_id: int, 
    start: datetime, 
    end: datetime
) -> int:
    """Calculate unique minutes of usage for a datetime range."""
    unique_minutes = db.query(
        func.count(func.distinct(minute_bucket(db, UsageLog.timestamp)))
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start,
        UsageLog.timestamp < end
    ).scalar() or 0
    return unique_minutes


def get_activity_boundaries(
    db: Session, 
    device_id: int, 
    day_str: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get first and last activity times for a day.
    
    Returns:
        Tuple of (first_time_str, last_time_str) in HH:MM format, or (None, None)
    """
    day_start, day_end = day_range_utc(day_str)
    first_activity = db.query(func.min(UsageLog.timestamp)).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= day_start,
        UsageLog.timestamp < day_end
    ).scalar()

    last_activity = db.query(func.max(UsageLog.timestamp)).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= day_start,
        UsageLog.timestamp < day_end
    ).scalar()
    
    if not first_activity or not last_activity:
        return None, None
    
    try:
        if isinstance(first_activity, str):
            first_activity = parser.parse(first_activity)
        if isinstance(last_activity, str):
            last_activity = parser.parse(last_activity)
        return first_activity.strftime('%H:%M'), last_activity.strftime('%H:%M')
    except Exception:
        return None, None


def get_day_stats(
    db: Session, 
    device_id: int, 
    day_str: str
) -> Tuple[int, int]:
    """
    Get basic stats for a day.
    
    Returns:
        Tuple of (unique_apps_count, sessions_count)
    """
    day_start, day_end = day_range_utc(day_str)
    stats = db.query(
        func.count(func.distinct(UsageLog.app_name)).label('apps_count'),
        func.count(UsageLog.id).label('sessions_count')
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= day_start,
        UsageLog.timestamp < day_end
    ).first()
    
    return (stats.apps_count or 0, stats.sessions_count or 0) if stats else (0, 0)


def get_app_day_duration(
    db: Session, 
    device_id: int, 
    app_names: List[str], 
    day_str: str
) -> int:
    """Get total duration for specific app(s) on a given day."""
    day_start, day_end = day_range_utc(day_str)
    return db.query(func.sum(UsageLog.duration)).filter(
        UsageLog.device_id == device_id,
        func.lower(UsageLog.app_name).in_(app_names),
        UsageLog.timestamp >= day_start,
        UsageLog.timestamp < day_end
    ).scalar() or 0


def get_app_total_stats(
    db: Session, 
    device_id: int, 
    app_names: List[str], 
    start_date: str
):
    """Get total stats for an app from start_date to now."""
    return db.query(
        func.sum(UsageLog.duration).label('total_duration'),
        func.count(UsageLog.id).label('sessions_count'),
        func.min(UsageLog.timestamp).label('first_use'),
        func.max(UsageLog.timestamp).label('last_use')
    ).filter(
        UsageLog.device_id == device_id,
        func.lower(UsageLog.app_name).in_(app_names),
        UsageLog.timestamp >= start_date
    ).first()


def get_hourly_distribution(
    db: Session,
    device_id: int,
    app_names: List[str],
    start_date: str,
    timezone_offset_seconds: int = 0
) -> List[dict]:
    """Get usage distribution by hour for specific app(s) in device local time.
    Timestamps in DB are UTC; offset is Client - Server in seconds."""
    hourly_stats = db.query(
        hour_expr(db, UsageLog.timestamp).label('hour'),
        func.sum(UsageLog.duration).label('total')
    ).filter(
        UsageLog.device_id == device_id,
        func.lower(UsageLog.app_name).in_(app_names),
        UsageLog.timestamp >= start_date
    ).group_by(
        hour_expr(db, UsageLog.timestamp)
    ).all()
    offset_hours = timezone_offset_seconds // 3600
    usage_by_hour = [{"hour": h, "duration_seconds": 0} for h in range(24)]
    for stat in hourly_stats:
        if stat.hour is not None:
            utc_hour = int(stat.hour)
            local_hour = (utc_hour + offset_hours) % 24
            usage_by_hour[local_hour]["duration_seconds"] += int(stat.total or 0)
    return usage_by_hour


def format_timestamp_to_time(timestamp) -> Optional[str]:
    """Format a timestamp to HH:MM string."""
    if not timestamp:
        return None
    try:
        if isinstance(timestamp, str):
            timestamp = parser.parse(timestamp)
        return timestamp.strftime('%H:%M')
    except Exception:
        return None
