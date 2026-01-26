"""
Summary calculation service.

Business logic for device usage summary calculations,
extracted from summary_endpoint.py for modularity.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from ..models import UsageLog, Rule
from .app_filter import app_filter

logger = logging.getLogger("summary_service")


def calculate_precise_usage(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    end_utc: datetime
) -> Tuple[int, int]:
    """
    Calculate precise usage via interval merging.
    
    Returns:
        Tuple of (today_usage_seconds, elapsed_today_seconds)
    """
    from dateutil import parser
    
    daily_logs = db.query(
        UsageLog.app_name, UsageLog.timestamp, UsageLog.duration
    ).filter(
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
    
    # Merge overlapping intervals
    total_seconds = _merge_intervals(all_segments)
    today_usage = int(total_seconds)
    return today_usage, today_usage


def _merge_intervals(segments: List[Tuple[float, float]]) -> float:
    """Merge overlapping time intervals and return total seconds."""
    if not segments:
        return 0.0
        
    segments.sort(key=lambda x: x[0])
    total_seconds = 0.0
    curr_start, curr_end = segments[0]
    
    for next_start, next_end in segments[1:]:
        if next_start < curr_end:
            curr_end = max(curr_end, next_end)
        else:
            total_seconds += curr_end - curr_start
            curr_start, curr_end = next_start, next_end
    
    total_seconds += curr_end - curr_start
    return total_seconds


def get_latest_window_titles(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    end_utc: datetime
) -> Dict[str, str]:
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


def calculate_day_usage(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    end_utc: datetime
) -> int:
    """Calculate usage for a specific day using minute buckets."""
    unique_minutes = db.query(
        func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc,
        UsageLog.timestamp < end_utc
    ).scalar() or 0
    return unique_minutes * 60


def calculate_week_average(
    db: Session, 
    device_id: int, 
    today_start_utc: datetime
) -> float:
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


def get_apps_with_limits(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    end_utc: datetime
) -> List[Dict]:
    """Get apps with time limits and their current usage."""
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


def get_daily_limit_info(
    db: Session, 
    device_id: int, 
    today_usage: int
) -> Optional[Dict]:
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


def get_active_schedules(db: Session, device_id: int) -> List[Dict]:
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


def get_activity_timeline(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    end_utc: datetime
) -> List[Dict]:
    """Get granular activity segments for timeline visualization."""
    from dateutil import parser
    
    logs = db.query(
        UsageLog.app_name, UsageLog.timestamp, UsageLog.duration
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc,
        UsageLog.timestamp < end_utc,
        UsageLog.duration > 0
    ).order_by(UsageLog.timestamp.asc()).all()
    
    timeline = []
    current_segment = None
    
    for log in logs:
        # Retroactive filtering
        if not app_filter.is_trackable(log.app_name):
            continue
            
        ts_obj = log.timestamp if hasattr(log.timestamp, 'timestamp') else parser.parse(log.timestamp)
        start_ts = ts_obj.timestamp()
        end_ts = start_ts + log.duration
        
        friendly_name = app_filter.get_friendly_name(log.app_name)
        
        # Merge adjacent logs for same app (gap < 5s)
        if current_segment and \
           current_segment['app_name'] == friendly_name and \
           abs(start_ts - current_segment['end_ts']) < 5:
            
            current_segment['end_ts'] = max(current_segment['end_ts'], end_ts)
            current_segment['duration'] = current_segment['end_ts'] - current_segment['start_ts']
        else:
            if current_segment:
                timeline.append(current_segment)
            
            current_segment = {
                "app_name": friendly_name,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "duration": end_ts - start_ts,
                "icon_type": app_filter.get_icon_type(log.app_name)
            }
            
    if current_segment:
        timeline.append(current_segment)
        
    return timeline


def calculate_smart_insights(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    end_utc: datetime,
    today_usage: int, 
    apps_with_limits: List[Dict]
) -> Optional[Dict]:
    """
    Calculate Smart Insights analytics.
    
    Includes:
    - Focus metrics (disabled, returns placeholder values)
    - Anomaly detection (early start, night owl, new apps)
    - Wellness score
    """
    from dateutil import parser
    
    try:
        logs_today = db.query(
            UsageLog.app_name, UsageLog.timestamp, UsageLog.duration, UsageLog.is_focused
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= start_utc,
            UsageLog.timestamp < end_utc
        ).order_by(UsageLog.timestamp.asc()).all()

        # Filter blacklisted apps
        logs_today = [
            log for log in logs_today 
            if app_filter.is_trackable(log.app_name)
        ]

        # Focus Analysis - DISABLED (unreliable data)
        context_switches = 0
        deep_work_seconds = 0
        flow_index = 0

        # Anomaly Detection
        anomalies = _detect_anomalies(db, device_id, start_utc, logs_today)
        
        # New apps detection
        new_apps = _detect_new_apps(db, device_id, start_utc, logs_today)

        # Wellness Score
        wellness_score = _calculate_wellness_score(
            today_usage, anomalies['is_night_owl'], apps_with_limits
        )

        total_mins = today_usage / 60
        
        return {
            "days_of_history": anomalies['days_of_history'],
            "focus": {
                "context_switches": context_switches,
                "deep_work_minutes": round(deep_work_seconds / 60, 1),
                "focus_index": wellness_score,
                "flow_index": flow_index
            },
            "anomalies": {
                "is_early_start": anomalies['is_early_start'],
                "is_night_owl": anomalies['is_night_owl'],
                "avg_start_hour": anomalies['avg_start_hour'],
                "new_apps": new_apps,
                "total_violations": sum(1 for a in apps_with_limits if a['percentage_used'] >= 100)
            },
            "balance": {
                "wellness_score": wellness_score,
                "usage_intensity": "High" if total_mins > 240 else "Moderate" if total_mins > 120 else "Low"
            }
        }
    except Exception as e:
        logger.error(f"Error calculating Smart Insights: {str(e)}")
        return None


def _detect_anomalies(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    logs_today: list
) -> Dict:
    """Detect usage anomalies like early start or night owl patterns."""
    from dateutil import parser
    
    is_early_start = False
    is_night_owl = False
    avg_start_hour = None
    starts = []
    
    if logs_today:
        first_dt = logs_today[0][1] if hasattr(logs_today[0][1], 'hour') else parser.parse(logs_today[0][1])
        
        # Night owl check
        for log in logs_today:
            l_dt = log[1] if hasattr(log[1], 'hour') else parser.parse(log[1])
            if l_dt.hour >= 22:
                is_night_owl = True
                break

        # Historical start times
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
        
        # Early start detection
        if starts:
            avg_start_hour = sum(starts) / len(starts)
            first_hour = first_dt.hour + first_dt.minute/60
            if first_hour < (avg_start_hour - 1.5):
                is_early_start = True
    
    return {
        "is_early_start": is_early_start,
        "is_night_owl": is_night_owl,
        "avg_start_hour": round(avg_start_hour, 1) if avg_start_hour else None,
        "days_of_history": len(starts)
    }


def _detect_new_apps(
    db: Session, 
    device_id: int, 
    start_utc: datetime, 
    logs_today: list
) -> List[str]:
    """Detect apps used today that weren't used in the last week."""
    apps_today_set = set(log[0].lower() for log in logs_today) if logs_today else set()
    
    apps_last_week = db.query(func.distinct(UsageLog.app_name)).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_utc - timedelta(days=7),
        UsageLog.timestamp < start_utc
    ).all()
    
    apps_last_week_set = set(a[0].lower() for a in apps_last_week)
    return list(apps_today_set - apps_last_week_set)


def _calculate_wellness_score(
    today_usage: int, 
    is_night_owl: bool, 
    apps_with_limits: List[Dict]
) -> int:
    """Calculate wellness score based on usage patterns."""
    total_mins = today_usage / 60
    
    if total_mins <= 120:
        base_score = 100 - (total_mins / 120 * 20)
    else:
        base_score = 80 - ((total_mins - 120) / 60 * 20)
    
    if is_night_owl:
        base_score -= 15
    
    forced_count = sum(1 for a in apps_with_limits if a['percentage_used'] >= 100)
    base_score -= (forced_count * 10)
    
    return max(0, min(100, round(base_score)))
