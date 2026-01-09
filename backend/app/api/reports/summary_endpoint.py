"""
Device summary endpoint with Smart Insights.

This endpoint is complex and kept separate for maintainability.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict
from datetime import datetime, timedelta, timezone
import logging

from ...database import get_db
from ...models import UsageLog, Device, User, Rule
from ...api.auth import get_current_parent
from ...services.app_filter import app_filter

# Import running_processes_cache from sibling module
from .device_endpoints import running_processes_cache

# Create router for this endpoint only
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
    
    # Calculate "Today" in Device's Local Time
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

    # Convert local midnight back to UTC for DB querying
    today_start_utc = local_midnight - timedelta(seconds=offset_seconds)
    today_end_utc = today_start_utc + timedelta(days=1)
    today_str = local_midnight.strftime('%Y-%m-%d')
    yesterday_start_utc = today_start_utc - timedelta(days=1)
    yesterday_end_utc = today_start_utc
    
    # Calculate precise usage via interval merging
    today_usage, elapsed_today_seconds = _calculate_precise_usage(
        db, device_id, today_start_utc, today_end_utc
    )
    
    # First report tracking
    first_report_iso = None
    if device.first_report_today_utc and not is_historical:
        first_utc = device.first_report_today_utc
        if first_utc.tzinfo is not None:
            first_utc = first_utc.replace(tzinfo=None)
        first_local = first_utc + timedelta(seconds=offset_seconds)
        if first_local.strftime('%Y-%m-%d') == today_str:
            first_report_iso = device.first_report_today_utc.isoformat()
    
    logger.info(f"Device {device_id} precise usage: {today_usage}s")
    
    # Get top apps and apply consistency check
    top_apps_query = db.query(
        UsageLog.app_name,
        func.sum(UsageLog.duration).label('total_duration')
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= today_start_utc,
        UsageLog.timestamp < today_end_utc
    ).group_by(UsageLog.app_name).order_by(func.sum(UsageLog.duration).desc()).limit(100).all()

    # Consistency check: total should be >= max app
    if top_apps_query:
        max_app_usage = top_apps_query[0].total_duration or 0
        if max_app_usage > today_usage:
            today_usage = int(max_app_usage)
            elapsed_today_seconds = today_usage

    # Get window titles
    latest_titles = _get_latest_window_titles(db, device_id, today_start_utc, today_end_utc)
    
    # Total apps today
    apps_today = len(set(log.app_name for log in top_apps_query))
    
    # Active rules count
    active_rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True
    ).count()
    
    # Total usage (all time)
    total_usage_all = db.query(func.sum(UsageLog.duration)).filter(
        UsageLog.device_id == device_id
    ).scalar() or 0
    
    # Last usage timestamp
    last_usage = db.query(func.max(UsageLog.timestamp)).filter(
        UsageLog.device_id == device_id
    ).scalar()
    
    # Yesterday and week avg
    yesterday_usage = _calculate_day_usage(db, device_id, yesterday_start_utc, yesterday_end_utc)
    week_avg = _calculate_week_average(db, device_id, today_start_utc)
    
    # Apps with time limits
    apps_with_limits = _get_apps_with_limits(db, device_id, today_start_utc, today_end_utc)
    
    # Daily limit info
    daily_limit_info = _get_daily_limit_info(db, device_id, today_usage)
    
    # Schedules
    active_schedules = _get_active_schedules(db, device_id)
    
    # Smart Insights
    insights = _calculate_smart_insights(
        db, device_id, today_start_utc, today_end_utc, today_usage, apps_with_limits
    )
    
    # Running processes (only for today)
    running_procs_data = running_processes_cache.get(device_id, {}) if not is_historical else {}
    running_processes = running_procs_data.get("processes", [])
    running_processes_updated = running_procs_data.get("updated_at")
    
    # Format last_seen
    last_seen_iso = None
    if device.last_seen:
        ls = device.last_seen
        if ls.tzinfo is None:
            ls = ls.replace(tzinfo=timezone.utc)
        last_seen_iso = ls.isoformat()

    # Merge and deduplicate top apps by friendly name
    top_apps_map = {}
    
    for app in top_apps_query:
        if not app_filter.is_trackable(app[0]):
            continue

        raw_name = app[0]
        duration = app[1]
        friendly_name = app_filter.get_friendly_name(raw_name)
        
        # Use a case-insensitive key for grouping
        key = friendly_name.lower()
        
        if key in top_apps_map:
            top_apps_map[key]["duration_seconds"] += duration
            # Prefer showing the Friendly Name as display name
            top_apps_map[key]["display_name"] = friendly_name 
        else:
            top_apps_map[key] = {
                "app_name": raw_name, # Keep one raw name as reference
                "duration_seconds": duration,
                "display_name": friendly_name,
                "window_title": latest_titles.get(raw_name, ""),
                "category": app_filter.get_category(raw_name),
                "icon_type": app_filter.get_icon_type(raw_name)
            }
            
    # Convert back to list and sort by duration
    final_top_apps = sorted(
        top_apps_map.values(), 
        key=lambda x: x["duration_seconds"], 
        reverse=True
    )

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
        "date_selected": today_str,
        "insights": insights,
        "running_processes": running_processes,
        "running_processes_updated": running_processes_updated.isoformat() if running_processes_updated else None
    }


# ============================================
# HELPER FUNCTIONS (extracted from get_device_summary)
# ============================================

def _calculate_precise_usage(db: Session, device_id: int, start_utc: datetime, end_utc: datetime):
    """Calculate precise usage via interval merging."""
    from dateutil import parser
    
    daily_logs = db.query(UsageLog.app_name, UsageLog.timestamp, UsageLog.duration).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc,
        UsageLog.timestamp < end_utc
    ).all()
    
    all_segments = []
    for log in daily_logs:
        # Retroactive filtering: Skip logs for apps that are now blacklisted
        if not app_filter.is_trackable(log.app_name):
            continue
            
        ts_obj = log.timestamp if hasattr(log.timestamp, 'timestamp') else parser.parse(log.timestamp)
        start_ts = ts_obj.timestamp()
        if log.duration > 0:
            all_segments.append((start_ts, start_ts + log.duration))
    
    # Merge intervals
    total_seconds = 0.0
    if all_segments:
        all_segments.sort(key=lambda x: x[0])
        curr_start, curr_end = all_segments[0]
        for next_start, next_end in all_segments[1:]:
            if next_start < curr_end:
                curr_end = max(curr_end, next_end)
            else:
                total_seconds += curr_end - curr_start
                curr_start, curr_end = next_start, next_end
        total_seconds += curr_end - curr_start
    
    today_usage = int(total_seconds)
    return today_usage, today_usage


def _get_latest_window_titles(db: Session, device_id: int, start_utc: datetime, end_utc: datetime) -> Dict:
    """Get latest window titles for each app."""
    titles_query = db.query(
        UsageLog.app_name,
        UsageLog.window_title
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc,
        UsageLog.timestamp < end_utc,
        UsageLog.window_title.isnot(None),
        UsageLog.window_title != ""
    ).order_by(UsageLog.timestamp.desc()).all()
    
    latest_titles = {}
    for app, title in titles_query:
        if app not in latest_titles:
            latest_titles[app] = title
    return latest_titles


def _calculate_day_usage(db: Session, device_id: int, start_utc: datetime, end_utc: datetime) -> int:
    """Calculate usage for a specific day using minute buckets."""
    unique_minutes = db.query(
        func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc,
        UsageLog.timestamp < end_utc
    ).scalar() or 0
    return unique_minutes * 60


def _calculate_week_average(db: Session, device_id: int, today_start_utc: datetime) -> float:
    """Calculate 7-day average usage."""
    week_total = 0
    for i in range(1, 8):
        day_start = today_start_utc - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= day_start,
            UsageLog.timestamp < day_end
        ).scalar() or 0
        week_total += day_minutes * 60
    return week_total / 7 if week_total > 0 else 0


def _get_apps_with_limits(db: Session, device_id: int, start_utc: datetime, end_utc: datetime):
    """Get apps with time limits and their usage."""
    time_limit_rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True,
        Rule.rule_type == "time_limit",
        Rule.app_name.isnot(None)
    ).all()
    
    apps_with_limits = []
    for rule in time_limit_rules:
        app_name = rule.app_name
        app_usage = db.query(func.sum(UsageLog.duration)).filter(
            UsageLog.device_id == device_id,
            func.lower(UsageLog.app_name).in_([app_name.lower(), f"{app_name.lower()}.exe"]),
            UsageLog.timestamp >= start_utc,
            UsageLog.timestamp < end_utc
        ).scalar() or 0
        
        limit_seconds = (rule.time_limit or 0) * 60
        remaining = max(0, limit_seconds - app_usage)
        
        apps_with_limits.append({
            "app_name": app_name,
            "friendly_name": app_filter.get_friendly_name(app_name),
            "category": app_filter.get_category(app_name),
            "icon_type": app_filter.get_icon_type(app_name),
            "usage_seconds": app_usage,
            "usage_minutes": round(app_usage / 60, 1),
            "limit_minutes": rule.time_limit or 0,
            "limit_seconds": limit_seconds,
            "remaining_seconds": remaining,
            "remaining_minutes": round(remaining / 60, 1),
            "percentage_used": round((app_usage / limit_seconds * 100) if limit_seconds > 0 else 0, 1)
        })
    return apps_with_limits


def _get_daily_limit_info(db: Session, device_id: int, today_usage: int):
    """Get daily device limit info if set."""
    daily_limit_rule = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True,
        Rule.rule_type == "daily_limit"
    ).first()
    
    if not daily_limit_rule or not daily_limit_rule.time_limit:
        return None
    
    limit_minutes = daily_limit_rule.time_limit
    limit_seconds = limit_minutes * 60
    remaining = max(0, limit_seconds - today_usage)
    percentage = round((today_usage / limit_seconds * 100) if limit_seconds > 0 else 0, 1)
    
    return {
        "limit_minutes": limit_minutes,
        "limit_seconds": limit_seconds,
        "usage_seconds": today_usage,
        "usage_minutes": round(today_usage / 60, 1),
        "remaining_seconds": remaining,
        "remaining_minutes": round(remaining / 60, 1),
        "percentage_used": percentage
    }


def _get_active_schedules(db: Session, device_id: int):
    """Get active schedule rules."""
    schedule_rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True,
        Rule.rule_type == "schedule"
    ).all()
    
    return [{
        "id": s.id,
        "start_time": s.schedule_start_time,
        "end_time": s.schedule_end_time,
        "days": s.schedule_days,
        "app_name": s.app_name
    } for s in schedule_rules]


def _calculate_smart_insights(db: Session, device_id: int, start_utc: datetime, end_utc: datetime, 
                               today_usage: int, apps_with_limits: list):
    """Calculate Smart Insights analytics."""
    from dateutil import parser
    
    try:
        logs_today = db.query(
            UsageLog.app_name, UsageLog.timestamp, UsageLog.duration, UsageLog.is_focused
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= start_utc,
            UsageLog.timestamp < end_utc
        ).order_by(UsageLog.timestamp.asc()).all()

        # Focus Analysis - DISABLED (moved to experimental)
        # Flow Index and Deep Work features were disabled due to unreliable data.
        # The is_focused flag from agent depends on window detection accuracy,
        # and 15-minute threshold is not meaningful for gaming/entertainment.
        # Logic preserved in: backend/app/services/experimental/insights_service.py
        context_switches = 0
        deep_work_seconds = 0
        flow_index = 0

        # Anomaly Detection
        is_early_start = False
        is_night_owl = False
        avg_start_hour = None
        starts = []
        
        if logs_today:
            first_dt = logs_today[0][1] if hasattr(logs_today[0][1], 'hour') else parser.parse(logs_today[0][1])
            
            for log in logs_today:
                l_dt = log[1] if hasattr(log[1], 'hour') else parser.parse(log[1])
                if l_dt.hour >= 22:
                    is_night_owl = True
                    break

            for k in range(1, 8):
                day_start = start_utc - timedelta(days=k)
                day_end = day_start + timedelta(days=1)
                first_d = db.query(func.min(UsageLog.timestamp)).filter(
                    UsageLog.device_id == device_id,
                    UsageLog.timestamp >= day_start,
                    UsageLog.timestamp < day_end
                ).scalar()
                if first_d:
                    fd = first_d if hasattr(first_d, 'hour') else parser.parse(first_d)
                    starts.append(fd.hour + fd.minute/60)
            
            if starts:
                avg_start_hour = sum(starts) / len(starts)
                first_hour = first_dt.hour + first_dt.minute/60
                if first_hour < (avg_start_hour - 1.5):
                    is_early_start = True

        # New apps detection
        apps_today_set = set(log[0].lower() for log in logs_today) if logs_today else set()
        apps_last_week = db.query(func.distinct(UsageLog.app_name)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= start_utc - timedelta(days=7),
            UsageLog.timestamp < start_utc
        ).all()
        apps_last_week_set = set(a[0].lower() for a in apps_last_week)
        new_apps = list(apps_today_set - apps_last_week_set)

        # Wellness Score
        total_mins = today_usage / 60
        if total_mins <= 120:
            base_score = 100 - (total_mins / 120 * 20)
        else:
            base_score = 80 - ((total_mins - 120) / 60 * 20)
        
        if is_night_owl:
            base_score -= 15
        forced_count = sum(1 for a in apps_with_limits if a['percentage_used'] >= 100)
        base_score -= (forced_count * 10)
        wellness_score = max(0, min(100, round(base_score)))

        return {
            "days_of_history": len(starts),
            "focus": {
                "context_switches": context_switches,
                "deep_work_minutes": round(deep_work_seconds / 60, 1),
                "focus_index": wellness_score,
                "flow_index": flow_index
            },
            "anomalies": {
                "is_early_start": is_early_start,
                "is_night_owl": is_night_owl,
                "avg_start_hour": round(avg_start_hour, 1) if avg_start_hour else None,
                "new_apps": new_apps,
                "total_violations": forced_count
            },
            "balance": {
                "wellness_score": wellness_score,
                "usage_intensity": "High" if total_mins > 240 else "Moderate" if total_mins > 120 else "Low"
            }
        }
    except Exception as e:
        logger.error(f"Error calculating Smart Insights: {str(e)}")
        return None
