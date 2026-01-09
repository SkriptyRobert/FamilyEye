"""
Advanced statistics endpoints for charts and analytics.

Split from monolithic reports.py for better maintainability.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict
from datetime import datetime, timedelta, timezone
import logging
from dateutil import parser

from ...database import get_db
from ...models import UsageLog, Device, User
from ..auth import get_current_parent
from ...cache import stats_cache

router = APIRouter()
logger = logging.getLogger("stats_endpoints")

# Czech day names for weekly pattern
CZECH_DAYS = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]


def verify_device_ownership(device_id: int, user_id: int, db: Session) -> Device:
    """Verify device belongs to the parent and return it."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.parent_id == user_id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    return device


@router.get("/device/{device_id}/usage-by-hour")
async def get_usage_by_hour(
    device_id: int,
    days: int = 7,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get usage data grouped by date and hour for heatmap visualization."""
    days = min(days, 14)
    
    cache_key = f"usage_by_hour:{device_id}:{days}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    verify_device_ownership(device_id, current_user.id, db)
    
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=days)
    
    results = db.query(
        func.strftime('%Y-%m-%d', UsageLog.timestamp).label('date'),
        func.strftime('%H', UsageLog.timestamp).label('hour'),
        func.sum(UsageLog.duration).label('total_seconds')
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_date
    ).group_by(
        func.strftime('%Y-%m-%d', UsageLog.timestamp),
        func.strftime('%H', UsageLog.timestamp)
    ).all()
    
    heatmap_data = []
    for row in results:
        heatmap_data.append({
            "date": row.date,
            "hour": int(row.hour),
            "duration_seconds": int(row.total_seconds or 0),
            "duration_minutes": round((row.total_seconds or 0) / 60, 1)
        })
    
    response = {
        "device_id": device_id,
        "days_analyzed": days,
        "data": heatmap_data
    }
    
    stats_cache.set(cache_key, response, ttl=300)
    return response


@router.get("/device/{device_id}/usage-trends")
async def get_usage_trends(
    device_id: int,
    period: str = "week",
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get daily usage trends for line chart visualization."""
    days = 7 if period == "week" else 30
    
    cache_key = f"usage_trends:{device_id}:{period}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    verify_device_ownership(device_id, current_user.id, db)
    
    now_utc = datetime.now(timezone.utc)
    
    results = []
    for i in range(days):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        first_activity = db.query(func.min(UsageLog.timestamp)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar()
        
        last_activity = db.query(func.max(UsageLog.timestamp)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar()
        
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        total_seconds = day_minutes * 60
        
        first_time_str = None
        last_time_str = None
        if first_activity and last_activity:
            try:
                if isinstance(first_activity, str):
                    first_activity = parser.parse(first_activity)
                if isinstance(last_activity, str):
                    last_activity = parser.parse(last_activity)
                first_time_str = first_activity.strftime('%H:%M')
                last_time_str = last_activity.strftime('%H:%M')
            except Exception:
                pass
        
        stats = db.query(
            func.count(func.distinct(UsageLog.app_name)).label('apps_count'),
            func.count(UsageLog.id).label('sessions_count')
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).first()
        
        results.append({
            "date": day_str,
            "total_seconds": total_seconds,
            "total_minutes": round(total_seconds / 60, 1),
            "apps_count": stats.apps_count if stats else 0,
            "sessions_count": stats.sessions_count if stats else 0,
            "first_activity": first_time_str,
            "last_activity": last_time_str
        })
    
    results.reverse()
    stats_cache.set(cache_key, results, ttl=300)
    return results


@router.get("/device/{device_id}/weekly-pattern")
async def get_weekly_pattern(
    device_id: int,
    weeks: int = 4,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get average usage by day of week (Monday-Sunday)."""
    weeks = min(weeks, 8)
    
    cache_key = f"weekly_pattern:{device_id}:{weeks}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    verify_device_ownership(device_id, current_user.id, db)
    
    now_utc = datetime.now(timezone.utc)
    
    day_totals = {i: {"total_seconds": 0, "sessions": 0, "days_count": 0} for i in range(7)}
    
    for i in range((weeks * 7)):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        day_of_week = day.weekday()
        
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        day_usage = day_minutes * 60
        
        if day_usage > 0:
            day_totals[day_of_week]["total_seconds"] += day_usage
            day_totals[day_of_week]["days_count"] += 1
        
        sessions = db.query(func.count(UsageLog.id)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        
        day_totals[day_of_week]["sessions"] += sessions
    
    results = []
    for day_idx in range(7):
        data = day_totals[day_idx]
        avg_seconds = data["total_seconds"] / data["days_count"] if data["days_count"] > 0 else 0
        avg_sessions = data["sessions"] / data["days_count"] if data["days_count"] > 0 else 0
        
        results.append({
            "day_index": day_idx,
            "day_name": CZECH_DAYS[day_idx],
            "avg_seconds": int(avg_seconds),
            "avg_minutes": round(avg_seconds / 60, 1),
            "avg_sessions": round(avg_sessions, 1),
            "total_seconds": data["total_seconds"],
            "days_with_data": data["days_count"]
        })
    
    stats_cache.set(cache_key, results, ttl=300)
    return results


@router.get("/device/{device_id}/weekly-current")
async def get_weekly_current(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get daily usage for the current week (Monday-Sunday) with actual totals."""
    cache_key = f"weekly_current:{device_id}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    verify_device_ownership(device_id, current_user.id, db)
    
    now_utc = datetime.now(timezone.utc)
    today_weekday = now_utc.weekday()  # 0 = Monday, 6 = Sunday
    
    # Calculate Monday of the current week
    monday = now_utc - timedelta(days=today_weekday)
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    results = []
    for day_idx in range(7):
        day = monday + timedelta(days=day_idx)
        day_str = day.strftime('%Y-%m-%d')
        day_end = day + timedelta(days=1)
        
        # Get total usage for this specific day
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= day,
            UsageLog.timestamp < day_end
        ).scalar() or 0
        
        total_seconds = day_minutes * 60
        
        results.append({
            "day_of_week": day_idx,
            "day_name": CZECH_DAYS[day_idx],
            "date": day_str,
            "total_seconds": total_seconds,
            "total_hours": round(total_seconds / 3600, 2),
            "is_today": day_idx == today_weekday,
            "is_future": day_idx > today_weekday
        })
    
    # Cache for shorter time since it's current week data
    stats_cache.set(cache_key, results, ttl=60)
    return results


@router.get("/device/{device_id}/app-details")

async def get_app_details(
    device_id: int,
    app_name: str,
    days: int = 7,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get detailed analysis of a specific application's usage."""
    days = min(days, 30)
    
    cache_key = f"app_details:{device_id}:{app_name}:{days}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    verify_device_ownership(device_id, current_user.id, db)
    
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=days)
    start_str = start_date.strftime('%Y-%m-%d')
    
    app_name_lower = app_name.lower()
    app_names = [app_name_lower, f"{app_name_lower}.exe"]
    
    total_stats = db.query(
        func.sum(UsageLog.duration).label('total_duration'),
        func.count(UsageLog.id).label('sessions_count'),
        func.min(UsageLog.timestamp).label('first_use'),
        func.max(UsageLog.timestamp).label('last_use')
    ).filter(
        UsageLog.device_id == device_id,
        func.lower(UsageLog.app_name).in_(app_names),
        UsageLog.timestamp >= start_str
    ).first()
    
    total_seconds = int(total_stats.total_duration or 0)
    sessions_count = int(total_stats.sessions_count or 0)
    avg_session = int(total_seconds / sessions_count) if sessions_count > 0 else 0
    
    hourly_stats = db.query(
        func.strftime('%H', UsageLog.timestamp).label('hour'),
        func.sum(UsageLog.duration).label('total')
    ).filter(
        UsageLog.device_id == device_id,
        func.lower(UsageLog.app_name).in_(app_names),
        UsageLog.timestamp >= start_str
    ).group_by(
        func.strftime('%H', UsageLog.timestamp)
    ).all()
    
    usage_by_hour = [{"hour": h, "duration_seconds": 0} for h in range(24)]
    for stat in hourly_stats:
        if stat.hour:
            hour_int = int(stat.hour)
            usage_by_hour[hour_int]["duration_seconds"] = int(stat.total or 0)
    
    usage_by_day = []
    for i in range(days):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        day_duration = db.query(func.sum(UsageLog.duration)).filter(
            UsageLog.device_id == device_id,
            func.lower(UsageLog.app_name).in_(app_names),
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        
        usage_by_day.append({
            "date": day_str,
            "duration_seconds": int(day_duration)
        })
    
    usage_by_day.reverse()
    
    from ...services.app_filter import app_filter
    
    response = {
        "app_name": app_name,
        "friendly_name": app_filter.get_friendly_name(app_name),
        "category": app_filter.get_category(app_name),
        "icon_type": app_filter.get_icon_type(app_name),
        "total_seconds": total_seconds,
        "total_minutes": round(total_seconds / 60, 1),
        "sessions_count": sessions_count,
        "avg_session_seconds": avg_session,
        "usage_by_hour": usage_by_hour,
        "usage_by_day": usage_by_day,
        "days_analyzed": days
    }
    
    stats_cache.set(cache_key, response, ttl=300)
    return response


@router.get("/device/{device_id}/app-trends")
async def get_app_trends(
    device_id: int,
    app_name: str,
    days: int = 30,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get usage trends for a specific application over time."""
    days = min(days, 60)
    
    cache_key = f"app_trends:{device_id}:{app_name}:{days}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    verify_device_ownership(device_id, current_user.id, db)
    
    now_utc = datetime.now(timezone.utc)
    
    app_name_lower = app_name.lower()
    app_names = [app_name_lower, f"{app_name_lower}.exe"]
    
    results = []
    for i in range(days):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        stats = db.query(
            func.sum(UsageLog.duration).label('total_duration'),
            func.count(UsageLog.id).label('sessions_count'),
            func.min(UsageLog.timestamp).label('first_use'),
            func.max(UsageLog.timestamp).label('last_use')
        ).filter(
            UsageLog.device_id == device_id,
            func.lower(UsageLog.app_name).in_(app_names),
            UsageLog.timestamp.like(f'{day_str}%')
        ).first()
        
        duration = int(stats.total_duration or 0)
        sessions = int(stats.sessions_count or 0)
        avg_session = int(duration / sessions) if sessions > 0 else 0
        
        first_use = None
        last_use = None
        if stats.first_use:
            try:
                if isinstance(stats.first_use, str):
                    first_use = parser.parse(stats.first_use).strftime('%H:%M')
                else:
                    first_use = stats.first_use.strftime('%H:%M')
            except Exception:
                pass
        if stats.last_use:
            try:
                if isinstance(stats.last_use, str):
                    last_use = parser.parse(stats.last_use).strftime('%H:%M')
                else:
                    last_use = stats.last_use.strftime('%H:%M')
            except Exception:
                pass
        
        results.append({
            "date": day_str,
            "duration_seconds": duration,
            "duration_minutes": round(duration / 60, 1),
            "sessions_count": sessions,
            "avg_session_duration": avg_session,
            "first_use": first_use,
            "last_use": last_use
        })
    
    results.reverse()
    stats_cache.set(cache_key, results, ttl=300)
    return results
