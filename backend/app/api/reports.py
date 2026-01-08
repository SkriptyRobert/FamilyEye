"""Reports and usage statistics endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from datetime import datetime, timedelta
from ..database import get_db
from ..models import UsageLog, Device, User, Rule
from ..schemas import UsageLogCreate, UsageLogResponse, AgentReportRequest, CriticalEventRequest
from ..api.auth import get_current_parent
from ..api.devices import verify_device_api_key

router = APIRouter()

# In-memory cache for running processes per device (updated with each report)
# Format: {device_id: {"processes": [...], "updated_at": datetime}}
running_processes_cache: Dict[int, dict] = {}


@router.post("/agent/report", status_code=status.HTTP_201_CREATED)
async def agent_report_usage(
    request: AgentReportRequest,
    db: Session = Depends(get_db)
):
    """Agent endpoint to report usage statistics."""
    from datetime import datetime
    import logging
    
    logger = logging.getLogger("reports")
    
    device = verify_device_api_key(request.device_id, request.api_key, db)
    
    # Update last_seen timestamp
    # Update last_seen timestamp
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    device.last_seen = now_utc
    
    # Calculate timezone offset
    if request.client_timestamp:
        # Client sends naive local time. We compare to naive UTC.
        client_ts = request.client_timestamp
        server_naive = now_utc.replace(tzinfo=None)
        if client_ts.tzinfo is not None:
             # If client sent aware time (unlikely with datetime.now().isoformat()), convert to naive
             client_ts = client_ts.replace(tzinfo=None)
             
        diff = client_ts - server_naive
        offset_seconds = int(diff.total_seconds())
        
        # Only update if changed significantly (> 1 minute to avoid drift noise)
        if abs(device.timezone_offset - offset_seconds) > 60:
            device.timezone_offset = offset_seconds
            logger.debug(f"Updated timezone offset for device {device.id}: {offset_seconds}s")

    # Track first report of the day (for elapsed time calculation in dashboard)
    offset_seconds = device.timezone_offset or 0
    device_local_now = now_utc + timedelta(seconds=offset_seconds)
    today_local_str = device_local_now.strftime('%Y-%m-%d')
    
    # Check if first_report_today_utc is from a different day (or null)
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

    # Log incoming report
    logger.info(f"Received usage report from device {device.id} ({device.name}): {len(request.usage_logs)} logs")
    
    # Use centralized filter service (Path A architecture)
    from ..services.app_filter import app_filter
    
    # Create usage log entries - use AppFilterService for filtering
    total_duration = 0
    filtered_count = 0
    trackable_duration = 0
    
    for log_data in request.usage_logs:
        app_name = log_data.app_name
        
        # Check if app is trackable (should count toward limits)
        is_trackable = app_filter.is_trackable(app_name)
        
        if not is_trackable:
            filtered_count += 1
            logger.debug(f"Filtered non-trackable app: {app_name}")
            continue  # Don't store hidden/system apps
        
        # Get enhanced metadata from filter service
        friendly_name = app_filter.get_friendly_name(app_name)
        category = app_filter.get_category(app_name)
        
        usage_log = UsageLog(
            device_id=device.id,
            app_name=app_name,
            window_title=log_data.window_title,
            exe_path=log_data.exe_path,
            duration=log_data.duration,
            is_focused=log_data.is_focused,
            timestamp=log_data.timestamp or datetime.utcnow()
        )
        db.add(usage_log)
        total_duration += log_data.duration
        trackable_duration += log_data.duration
        logger.debug(f"  - {friendly_name} ({category or 'unknown'}): {log_data.duration}s")
    
    if filtered_count > 0:
        logger.info(f"Filtered {filtered_count} non-trackable app entries (backend filter)")
    
    db.commit()
    
    logger.info(f"Saved {len(request.usage_logs) - filtered_count} usage logs, trackable duration: {trackable_duration}s ({trackable_duration // 60}m)")
    
    # Store running processes in DB and cache for live monitoring
    if hasattr(request, 'running_processes') and request.running_processes:
        import json
        processes_json = json.dumps(request.running_processes)
        device.current_processes = processes_json
        
        # Also keep in cache if needed elsewhere
        running_processes_cache[device.id] = {
            "processes": request.running_processes,
            "updated_at": datetime.utcnow()
        }
        logger.debug(f"Saved {len(request.running_processes)} running processes for device {device.id}")
        
    # Commit changes to device
    db.add(device)
    db.commit()
    
    # Check for pending commands to send back to agent
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
    import logging
    logger = logging.getLogger("reports")
    
    device_id = request.get("device_id")
    api_key = request.get("api_key")
    image_base64 = request.get("image")
    
    device = verify_device_api_key(device_id, api_key, db)
    
    logger.info(f"Received screenshot from device {device.id}")
    
    # In a real app, we would save the file to disk and store the path
    # For now, we'll store the base64 or a placeholder
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
    This allows dashboard to show real-time status updates.
    """
    from datetime import datetime, timezone
    import logging
    
    logger = logging.getLogger("reports")
    
    device = verify_device_api_key(request.device_id, request.api_key, db)
    
    # Update last_seen timestamp
    device.last_seen = datetime.now(timezone.utc)
    
    logger.warning(f"CRITICAL EVENT from device {device.id}: {request.event_type} - {request.app_name or 'N/A'}")
    
    # For limit_exceeded events, update usage log with actual time
    if request.event_type == 'limit_exceeded' and request.app_name and request.used_seconds:
        # Calculate device's current day start in UTC
        offset_seconds = device.timezone_offset or 0
        now_device = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
        local_midnight = now_device.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_utc = local_midnight - timedelta(seconds=offset_seconds)
        today_end_utc = today_start_utc + timedelta(days=1)
        
        # Get current usage for this app today (within device's local day range)
        current_usage = db.query(func.sum(UsageLog.duration)).filter(
            UsageLog.device_id == device.id,
            func.lower(UsageLog.app_name) == request.app_name.lower(),
            UsageLog.timestamp >= today_start_utc,
            UsageLog.timestamp < today_end_utc
        ).scalar() or 0
        
        # If agent reports more than DB has, add the difference
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


@router.get("/device/{device_id}/usage", response_model=List[UsageLogResponse])
async def get_device_usage(
    device_id: int,
    days: int = 7,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get usage statistics for a device."""
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
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    usage_logs = db.query(UsageLog).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_date
    ).order_by(UsageLog.timestamp.desc()).all()
    
    # Enrich with metadata
    from ..services.app_filter import app_filter
    results = []
    for log in usage_logs:
        # Filter out noisy/blacklisted apps even if they exist in DB
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




@router.get("/device/{device_id}/summary")
async def get_device_summary(
    device_id: int,
    date: str = None,  # Optional date filter (YYYY-MM-DD)
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get usage summary for a device."""
    import logging
    logger = logging.getLogger("reports")
    logger.info(f"get_device_summary called for device_id={device_id}")
    
    # Use centralized filter service
    from ..services.app_filter import app_filter
    
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
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    offset_seconds = device.timezone_offset or 0
    device_local_now = now_utc + timedelta(seconds=offset_seconds)
    
    if date:
        try:
            from dateutil import parser
            dt = parser.parse(date)
            # Use provided date as local midnight
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
    
    # --- PRECISE USAGE CALCULATION (Interval Merging) ---
    # Fetch all logs for today to calculate precise screen time (Wall Clock)
    # This avoids "7 minutes usage in 6 minutes time" paradox caused by minute-bucketing
    
    daily_logs = db.query(UsageLog.app_name, UsageLog.timestamp, UsageLog.duration).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= today_start_utc,
        UsageLog.timestamp < today_end_utc
    ).all()
    
    # Algorithm: Merge overlapping intervals from ALL apps to find "Time Machine Was Used"
    from dateutil import parser
    all_segments = []
    
    for log in daily_logs:
        # DB returns datetime object or string depending on driver
        ts_obj = log.timestamp if hasattr(log.timestamp, 'timestamp') else parser.parse(log.timestamp)
        start_ts = ts_obj.timestamp()
        duration = log.duration
        if duration > 0:
            all_segments.append((start_ts, start_ts + duration))
            
    # Merge intervals
    total_seconds = 0.0
    if all_segments:
        all_segments.sort(key=lambda x: x[0])
        merged = []
        if all_segments:
            curr_start, curr_end = all_segments[0]
            for next_start, next_end in all_segments[1:]:
                if next_start < curr_end: # Overlap
                    curr_end = max(curr_end, next_end)
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
        
        total_seconds = sum(end - start for start, end in merged)
    
    today_usage = int(total_seconds)
    
    # Calculate elapsed time since first report today (Wall-Clock "Active Time")
    # This gives users a logical view: "Monitoring started at 17:17, now 17:47 = 30m elapsed"
    elapsed_today_seconds = 0
    first_report_iso = None
    if device.first_report_today_utc and not is_historical:
        # Convert first report to device local time for day comparison
        # Ensure timezone consistency - strip tzinfo for comparison
        first_utc = device.first_report_today_utc
        if first_utc.tzinfo is not None:
            first_utc = first_utc.replace(tzinfo=None)
        first_local = first_utc + timedelta(seconds=offset_seconds)
        first_day_str = first_local.strftime('%Y-%m-%d')
        
        # Ensure device_local_now is also naive for comparison
        device_local_now_naive = device_local_now
        if hasattr(device_local_now, 'tzinfo') and device_local_now.tzinfo is not None:
            device_local_now_naive = device_local_now.replace(tzinfo=None)
        
        # Only compute if first report is from today
        if first_day_str == today_str:
            elapsed_delta = device_local_now_naive - first_local
            elapsed_today_seconds = max(0, int(elapsed_delta.total_seconds()))
            first_report_iso = device.first_report_today_utc.isoformat()
            logger.debug(f"Device {device_id} elapsed today: {elapsed_today_seconds}s (since {first_report_iso})")
    
    logger.info(f"Device {device_id} precise usage: {today_usage}s, elapsed: {elapsed_today_seconds}s")
    
    # Total apps used today (from the fetched list to save query)
    apps_today = len(set(log.app_name for log in daily_logs))
    
    # Most used apps today - Aggregate from fetched logs (Python side) or Query
    # Query is cleaner for aggregation/ordering
    top_apps_query = db.query(
        UsageLog.app_name,
        func.sum(UsageLog.duration).label('total_duration')
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= today_start_utc,
        UsageLog.timestamp < today_end_utc
    ).group_by(UsageLog.app_name).order_by(func.sum(UsageLog.duration).desc()).limit(100).all()

    # Get latest window titles for each app to show what's actually happening
    latest_titles = {}
    titles_query = db.query(
        UsageLog.app_name,
        UsageLog.window_title
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= today_start_utc,
        UsageLog.timestamp < today_end_utc,
        UsageLog.window_title.isnot(None),
        UsageLog.window_title != ""
    ).order_by(UsageLog.timestamp.desc()).all()
    
    for app, title in titles_query:
        if app not in latest_titles:
            latest_titles[app] = title
    
    # Active rules
    active_rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True
    ).count()
    
    # Calculate total usage time (all time) - Keep simplistic sum or cache? 
    # For now, simplistic sum is okay for all-time
    total_usage_all = db.query(func.sum(UsageLog.duration)).filter(
        UsageLog.device_id == device_id
    ).scalar() or 0
    # Note: total_usage variable was shadowed, renamed to total_usage_all
    
    # Get last usage timestamp
    last_usage = db.query(func.max(UsageLog.timestamp)).filter(
        UsageLog.device_id == device_id
    ).scalar()
    
    # Yesterday's usage - Use Minute Buckets (Legacy) for speed on historical data?
    # Or fetch logs? Yesterday logs might be many. Keep Minute Buckets for Yesterday/Week for performance.
    # Count unique report minutes - truncate timestamp to minute level before counting
    reporting_interval = 60
    unique_minutes_yesterday = db.query(
        func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= yesterday_start_utc,
        UsageLog.timestamp < yesterday_end_utc
    ).scalar() or 0
    yesterday_usage = unique_minutes_yesterday * reporting_interval
    
    # Calculate week average (count of unique minutes for last 7 days / 7) 
    week_total = 0
    for i in range(1, 8):
        day_start_utc = today_start_utc - timedelta(days=i)
        day_end_utc = day_start_utc + timedelta(days=1)
        
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= day_start_utc,
            UsageLog.timestamp < day_end_utc
        ).scalar() or 0
        
        week_total += day_minutes * reporting_interval
    
    week_avg = week_total / 7 if week_total > 0 else 0
    
    # Get rules with time limits to show which apps have limits
    time_limit_rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True,
        Rule.rule_type == "time_limit",
        Rule.app_name.isnot(None)
    ).all()
    
    # Calculate usage for apps with time limits
    apps_with_limits = []
    for rule in time_limit_rules:
        app_name = rule.app_name
        # Get today's usage for this app - improved matching (case-insensitive, handles .exe)
        app_usage_today = db.query(func.sum(UsageLog.duration)).filter(
            UsageLog.device_id == device_id,
            func.lower(UsageLog.app_name).in_([app_name.lower(), f"{app_name.lower()}.exe"]),
            UsageLog.timestamp >= today_start_utc,
            UsageLog.timestamp < today_end_utc
        ).scalar() or 0
        
        limit_seconds = (rule.time_limit or 0) * 60  # Convert minutes to seconds
        remaining_seconds = max(0, limit_seconds - app_usage_today)
        
        apps_with_limits.append({
            "app_name": app_name,
            "friendly_name": app_filter.get_friendly_name(app_name),
            "category": app_filter.get_category(app_name),
            "icon_type": app_filter.get_icon_type(app_name),
            "usage_seconds": app_usage_today,
            "usage_minutes": round(app_usage_today / 60, 1),
            "limit_minutes": rule.time_limit or 0,
            "limit_seconds": limit_seconds,
            "remaining_seconds": remaining_seconds,
            "remaining_minutes": round(remaining_seconds / 60, 1),
            "percentage_used": round((app_usage_today / limit_seconds * 100) if limit_seconds > 0 else 0, 1)
        })
    
    # Get daily limit for device (if set)
    daily_limit_rule = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True,
        Rule.rule_type == "daily_limit"
    ).first()
    
    daily_limit_info = None
    if daily_limit_rule and daily_limit_rule.time_limit:
        limit_minutes = daily_limit_rule.time_limit
        limit_seconds_daily = limit_minutes * 60
        usage_seconds = today_usage
        remaining = max(0, limit_seconds_daily - usage_seconds)
        percentage = round((usage_seconds / limit_seconds_daily * 100) if limit_seconds_daily > 0 else 0, 1)
        
        daily_limit_info = {
            "limit_minutes": limit_minutes,
            "limit_seconds": limit_seconds_daily,
            "usage_seconds": usage_seconds,
            "usage_minutes": round(usage_seconds / 60, 1),
            "remaining_seconds": remaining,
            "remaining_minutes": round(remaining / 60, 1),
            "percentage_used": percentage
        }
    
    # Get active schedules
    schedule_rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True,
        Rule.rule_type == "schedule"
    ).all()
    
    active_schedules = []
    for schedule in schedule_rules:
        active_schedules.append({
            "id": schedule.id,
            "start_time": schedule.schedule_start_time,
            "end_time": schedule.schedule_end_time,
            "days": schedule.schedule_days,
            "app_name": schedule.app_name  # None means all apps
        })
    
    # --- SMART INSIGHTS ANALYTICS ---
    insights = None
    try:
        # Fetch raw logs for the selected day including is_focused flag
        logs_today = db.query(UsageLog.app_name, UsageLog.timestamp, UsageLog.duration, UsageLog.is_focused).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= today_start_utc,
            UsageLog.timestamp < today_end_utc
        ).order_by(UsageLog.timestamp.asc()).all()

        # 1. Focus Analysis (Parallel Tracks: Multi-monitor & Multitasking aware)
        context_switches = 0
        deep_work_seconds = 0
        
        if logs_today:
            from dateutil import parser
            app_tracks = {}
            
            # Noise Minimization: Only track apps that were actually FOCUSED (or transition).
            # Fix: Round timestamps to seconds for reliable matching (ignore microseconds)
            ts_has_focus = {}
            for log in logs_today:
                ts_key = int(log[1].timestamp()) if hasattr(log[1], 'timestamp') else int(parser.parse(log[1]).timestamp())
                if log[3]: # is_focused
                    ts_has_focus[ts_key] = True
            
            # Collect ALL potential focus segments from eligible apps
            all_segments = []
            
            for log in logs_today:
                app_name, timestamp, duration, is_focused = log
                
                # Timestamp matching logic (Sloppy match)
                ts_obj = timestamp if hasattr(timestamp, 'timestamp') else parser.parse(timestamp)
                ts_key = int(ts_obj.timestamp())
                
                # Filter Noise: If this second had a focused app, but this log isn't it -> Skip.
                if ts_key in ts_has_focus and not is_focused:
                    continue
                
                start_ts = ts_obj.timestamp()
                end_ts = start_ts + duration
                all_segments.append((start_ts, end_ts))

            # Merge overlapping segments from ALL apps into one timeline
            # This allows switching tools (IDE -> Browser -> IDE) to count as one Deep Work session
            merged_intervals = []
            if all_segments:
                all_segments.sort(key=lambda x: x[0])
                
                current_start, current_end = all_segments[0]
                GRACE_PERIOD = 100 # 100s tolerance for gaps
                
                for i in range(1, len(all_segments)):
                    next_start, next_end = all_segments[i]
                    
                    # If start inside current (overlap) OR gap is within tolerance
                    if next_start <= (current_end + GRACE_PERIOD):
                        current_end = max(current_end, next_end)
                    else:
                        # Gap too big, finish this block
                        merged_intervals.append((current_start, current_end))
                        current_start, current_end = next_start, next_end
                
                merged_intervals.append((current_start, current_end))

            # Calculate Deep Work & Context Switches
            # Deep Work = Total time of merged blocks that are > 15 min
            deep_work_seconds = sum((end - start) for start, end in merged_intervals if (end - start) >= 15 * 60)
            
            # Simple Context Switch estimation: Number of gaps/breaks in the merged timeline
            # If we have N merged blocks, we had N-1 switches/breaks significantly long enough to break flow
            context_switches = max(0, len(merged_intervals) - 1)

        # Flow Index = (Total Time in Deep Work / Total Screen Time) * 100
        # today_usage here is the Screen Time calculated at the top of get_device_summary
        # Cap at 100% to prevent impossible values due to interval merging
        focus_index = min(100, round((deep_work_seconds / today_usage * 100), 1)) if today_usage > 0 else 0

        # 2. Anomaly Detection (Night Owl & Early Start)
        first_activity_today = logs_today[0][1] if logs_today else None
        last_activity_today = logs_today[-1][1] if logs_today else None
        
        is_early_start = False
        is_night_owl = False
        avg_start_hour = None
        starts = []
        
        if first_activity_today:
            from dateutil import parser
            first_dt = parser.parse(first_activity_today) if isinstance(first_activity_today, str) else first_activity_today
            
            # Night Owl: Any session after 22:00
            for log in logs_today:
                l_dt = parser.parse(log[1]) if isinstance(log[1], str) else log[1]
                if l_dt.hour >= 22:
                    is_night_owl = True
                    break

            # Calculate Average Start Hour (Past 7 days)
            for k in range(1, 8):
                day_start_utc_h = today_start_utc - timedelta(days=k)
                day_end_utc_h = day_start_utc_h + timedelta(days=1)
                first_d = db.query(func.min(UsageLog.timestamp)).filter(
                    UsageLog.device_id == device_id, 
                    UsageLog.timestamp >= day_start_utc_h,
                    UsageLog.timestamp < day_end_utc_h
                ).scalar()
                
                if first_d:
                    first_d_dt = parser.parse(first_d) if isinstance(first_d, str) else first_d
                    # Adjust to device local time roughly for hour extraction (approximation)
                    # Ideally we use timezone_offset but for simple check this might suffice
                    # or better: just rely on the hour if we trust the offset logic elsewhere
                    starts.append(first_d_dt.hour + first_d_dt.minute/60)
            
            if starts:
                avg_start_hour = sum(starts) / len(starts)
                if (first_dt.hour + first_dt.minute/60) < (avg_start_hour - 1.5):
                    is_early_start = True

        # 3. New apps detection
        apps_today_set = set(app[0].lower() for app in logs_today)
        apps_last_week = db.query(func.distinct(UsageLog.app_name)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp >= today_start_utc - timedelta(days=7),
            UsageLog.timestamp < today_start_utc
        ).all()
        apps_last_week_set = set(app[0].lower() for app in apps_last_week)
        new_apps = list(apps_today_set - apps_last_week_set)
        
        # 4. Wellness Score (Refined Logic)
        # Base 100
        total_mins = today_usage / 60
        if total_mins <= 120:
            # 0-120 mins: Slow linear decay (from 100 down to 80)
            base_score = 100 - (total_mins / 120 * 20)
        else:
            # > 120 mins: Rapid exponential/steep decay (-20 points for every additional hour)
            extra_hours = (total_mins - 120) / 60
            base_score = 80 - (extra_hours * 20)
            
        # Penalties
        if is_night_owl: base_score -= 15
        forced_terminations_count = sum(1 for a in apps_with_limits if a['percentage_used'] >= 100)
        base_score -= (forced_terminations_count * 10)
        
        wellness_score = max(0, min(100, round(base_score)))
        
        insights = {
            "days_of_history": len(starts),
            "focus": {
                "context_switches": context_switches,
                "deep_work_minutes": round(deep_work_seconds / 60, 1),
                "focus_index": wellness_score, # Placeholder
                "flow_index": focus_index
            },
            "anomalies": {
                "is_early_start": is_early_start,
                "is_night_owl": is_night_owl,
                "avg_start_hour": round(avg_start_hour, 1) if avg_start_hour is not None else None,
                "new_apps": new_apps,
                "total_violations": forced_terminations_count
            },
            "balance": {
                "wellness_score": wellness_score,
                "usage_intensity": "High" if total_mins > 240 else "Moderate" if total_mins > 120 else "Low"
            }
        }
    except Exception as e:
        logger.error(f"Error calculating Smart Insights: {str(e)}")
        insights = None

    # --- END SMART INSIGHTS ---

    # Get cached running processes for this device (only if today is selected)
    running_procs_data = {}
    if not is_historical:
        running_procs_data = running_processes_cache.get(device_id, {})
    
    running_processes = running_procs_data.get("processes", [])
    running_processes_updated = running_procs_data.get("updated_at")
    
    # Fix last_seen offset: ensure it's ISO with Z or offset
    last_seen_iso = None
    if device.last_seen:
        ls = device.last_seen
        if ls.tzinfo is None:
            ls = ls.replace(tzinfo=timezone.utc)
        last_seen_iso = ls.isoformat()

    return {
        "device_id": device_id,
        "device_name": device.name,
        "is_online": device.is_online, # Use the model property logic
        "today_usage_seconds": today_usage,
        "today_usage_hours": round(today_usage / 3600, 2),
        "elapsed_today_seconds": elapsed_today_seconds,  # NEW: Wall-clock elapsed since first report
        "first_report_today": first_report_iso,  # NEW: Timestamp for dashboard display
        "yesterday_usage_seconds": yesterday_usage,
        "week_avg_seconds": week_avg,
        "total_usage_seconds": total_usage_all,
        "total_usage_hours": round(total_usage_all / 3600, 2),
        "apps_used_today": apps_today,
        "apps_used_today": apps_today,
        "top_apps": [{
            "app_name": app[0], 
            "duration_seconds": app[1],
            "display_name": app_filter.get_friendly_name(app[0]),
            "window_title": latest_titles.get(app[0], ""),
            "category": app_filter.get_category(app[0]),
            "icon_type": app_filter.get_icon_type(app[0])
        } for app in top_apps_query if app_filter.is_trackable(app[0])],
        "active_rules": active_rules,
        "apps_with_limits": apps_with_limits,
        "daily_limit": daily_limit_info,
        "schedules": active_schedules,
        "last_seen": last_seen_iso,
        "last_usage": last_usage,
        "paired_at": device.paired_at,
        "is_historical": is_historical,
        "date_selected": today_str,
        # NEW: Smart Insights Data
        "insights": insights,
        # NEW: Running processes for live monitoring (empty for history)
        "running_processes": running_processes,
        "running_processes_updated": running_processes_updated.isoformat() if running_processes_updated else None
    }

@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_old_logs(
    days: int = 90,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Cleanup usage logs older than X days."""
    # Note: In a larger app this should be a periodic worker task
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # We only cleanup logs for devices belonging to this parent for security
    # via subquery or join
    device_ids = db.query(Device.id).filter(Device.parent_id == current_user.id).all()
    device_ids = [d[0] for d in device_ids]
    
    deleted_count = db.query(UsageLog).filter(
        UsageLog.device_id.in_(device_ids),
        UsageLog.timestamp < cutoff_date
    ).delete(synchronize_session=False)
    
    db.commit()
    return {"status": "success", "deleted_count": deleted_count}


# ============================================
# ADVANCED STATISTICS ENDPOINTS
# ============================================

from ..cache import stats_cache

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
    """
    Get usage data grouped by date and hour for heatmap visualization.
    
    Optimized for minimal resource usage:
    - Max 14 days of data
    - Aggregation at database level
    - 5 minute cache
    """
    import logging
    logger = logging.getLogger("reports")
    
    # Limit to max 14 days for performance
    days = min(days, 14)
    
    # Check cache first
    cache_key = f"usage_by_hour:{device_id}:{days}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit for usage-by-hour device {device_id}")
        return cached
    
    # Verify ownership
    verify_device_ownership(device_id, current_user.id, db)
    
    # Calculate date range
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=days)
    start_str = start_date.strftime('%Y-%m-%d')
    
    # SQLite-compatible query using strftime for hour extraction
    # GROUP BY date and hour
    results = db.query(
        func.date(UsageLog.timestamp).label('date'),
        func.strftime('%H', UsageLog.timestamp).label('hour'),
        func.sum(UsageLog.duration).label('total_duration'),
        func.count(func.distinct(UsageLog.app_name)).label('apps_count'),
        func.count(UsageLog.id).label('sessions_count')
    ).filter(
        UsageLog.device_id == device_id,
        UsageLog.timestamp >= start_str
    ).group_by(
        func.date(UsageLog.timestamp),
        func.strftime('%H', UsageLog.timestamp)
    ).order_by(
        func.date(UsageLog.timestamp),
        func.strftime('%H', UsageLog.timestamp)
    ).all()
    
    # Format response
    response = [{
        "date": str(r.date) if r.date else None,
        "hour": int(r.hour) if r.hour else 0,
        "duration_seconds": int(r.total_duration or 0),
        "duration_minutes": round(int(r.total_duration or 0) / 60, 1),
        "apps_count": int(r.apps_count or 0),
        "sessions_count": int(r.sessions_count or 0)
    } for r in results]
    
    # Cache for 5 minutes
    stats_cache.set(cache_key, response, ttl=300)
    
    return response


@router.get("/device/{device_id}/usage-trends")
async def get_usage_trends(
    device_id: int,
    period: str = "week",
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Get daily usage trends for line chart visualization.
    
    Args:
        period: "week" (7 days) or "month" (30 days)
    """
    import logging
    logger = logging.getLogger("reports")
    
    # Validate period
    days = 7 if period == "week" else 30
    
    # Check cache
    cache_key = f"usage_trends:{device_id}:{period}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Verify ownership
    verify_device_ownership(device_id, current_user.id, db)
    
    # Calculate date range
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=days)
    
    # Get daily aggregates
    results = []
    for i in range(days):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        # Get first and last activity (for display only)
        first_activity = db.query(func.min(UsageLog.timestamp)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar()
        
        last_activity = db.query(func.max(UsageLog.timestamp)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar()
        
        # Calculate total_seconds as COUNT of unique MINUTES (truncated to minute level)
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        total_seconds = day_minutes * 60  # 60 seconds per minute
        
        # Get first/last time strings for display
        first_time_str = None
        last_time_str = None
        if first_activity and last_activity:
            try:
                if isinstance(first_activity, str):
                    from dateutil import parser
                    first_activity = parser.parse(first_activity)
                if isinstance(last_activity, str):
                    last_activity = parser.parse(last_activity)
                first_time_str = first_activity.strftime('%H:%M')
                last_time_str = last_activity.strftime('%H:%M')
            except Exception:
                pass
        
        # Get apps count and sessions count
        stats = db.query(
            func.count(func.distinct(UsageLog.app_name)).label('apps_count'),
            func.count(UsageLog.id).label('sessions_count')
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).first()
        
        # Get peak hour
        peak_hour_result = db.query(
            func.strftime('%H', UsageLog.timestamp).label('hour'),
            func.sum(UsageLog.duration).label('total')
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).group_by(
            func.strftime('%H', UsageLog.timestamp)
        ).order_by(
            func.sum(UsageLog.duration).desc()
        ).first()
        
        peak_hour = int(peak_hour_result.hour) if peak_hour_result and peak_hour_result.hour else None
        
        results.append({
            "date": day_str,
            "total_seconds": int(total_seconds),
            "total_hours": round(total_seconds / 3600, 2),
            "apps_count": stats.apps_count if stats else 0,
            "sessions_count": stats.sessions_count if stats else 0,
            "peak_hour": peak_hour,
            "first_activity": first_time_str,
            "last_activity": last_time_str
        })
    
    # Reverse to show oldest first
    results.reverse()
    
    # Cache for 5 minutes
    stats_cache.set(cache_key, results, ttl=300)
    
    return results


@router.get("/device/{device_id}/weekly-pattern")
async def get_weekly_pattern(
    device_id: int,
    weeks: int = 4,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Get average usage by day of week (Monday-Sunday).
    
    Useful for identifying patterns like "more usage on weekends".
    """
    import logging
    logger = logging.getLogger("reports")
    
    # Limit weeks for performance
    weeks = min(weeks, 8)
    
    # Check cache
    cache_key = f"weekly_pattern:{device_id}:{weeks}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Verify ownership
    verify_device_ownership(device_id, current_user.id, db)
    
    # Calculate date range
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(weeks=weeks)
    
    # Initialize results for each day of week
    day_totals = {i: {"total_seconds": 0, "sessions": 0, "days_count": 0, "hours": {}} for i in range(7)}
    
    # Process each day in the range
    for i in range((weeks * 7)):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        day_of_week = day.weekday()  # 0=Monday, 6=Sunday
        
        # Calculate usage as COUNT of unique MINUTES (truncated to minute level)
        day_minutes = db.query(
            func.count(func.distinct(func.strftime('%Y-%m-%d %H:%M', UsageLog.timestamp)))
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        day_usage = day_minutes * 60  # 60 seconds per minute
        
        if day_usage > 0:
            day_totals[day_of_week]["total_seconds"] += day_usage
            day_totals[day_of_week]["days_count"] += 1
        
        # Get sessions count
        sessions = db.query(func.count(UsageLog.id)).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).scalar() or 0
        
        day_totals[day_of_week]["sessions"] += sessions
        
        # Get hourly distribution for peak hour calculation
        hourly = db.query(
            func.strftime('%H', UsageLog.timestamp).label('hour'),
            func.sum(UsageLog.duration).label('total')
        ).filter(
            UsageLog.device_id == device_id,
            UsageLog.timestamp.like(f'{day_str}%')
        ).group_by(
            func.strftime('%H', UsageLog.timestamp)
        ).all()
        
        for h in hourly:
            if h.hour:
                hour_int = int(h.hour)
                day_totals[day_of_week]["hours"][hour_int] = \
                    day_totals[day_of_week]["hours"].get(hour_int, 0) + (h.total or 0)
    
    # Calculate averages and format response
    results = []
    for day_num in range(7):
        data = day_totals[day_num]
        days_count = max(data["days_count"], 1)  # Avoid division by zero
        
        avg_seconds = data["total_seconds"] / days_count
        avg_sessions = data["sessions"] / days_count
        
        # Find peak hour
        peak_hour = None
        if data["hours"]:
            peak_hour = max(data["hours"].items(), key=lambda x: x[1])[0]
        
        results.append({
            "day_of_week": day_num,
            "day_name": CZECH_DAYS[day_num],
            "avg_duration_seconds": int(avg_seconds),
            "avg_duration_hours": round(avg_seconds / 3600, 2),
            "avg_sessions_count": int(avg_sessions),
            "peak_hour": peak_hour
        })
    
    # Cache for 10 minutes (less volatile data)
    stats_cache.set(cache_key, results, ttl=600)
    
    return results


@router.get("/device/{device_id}/app-details")
async def get_app_details(
    device_id: int,
    app_name: str,
    days: int = 7,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """
    Get detailed analysis of a specific application's usage.
    """
    import logging
    logger = logging.getLogger("reports")
    
    # Limit days for performance
    days = min(days, 30)
    
    # Check cache
    cache_key = f"app_details:{device_id}:{app_name}:{days}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Verify ownership
    verify_device_ownership(device_id, current_user.id, db)
    
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=days)
    start_str = start_date.strftime('%Y-%m-%d')
    
    # Handle app_name with or without .exe
    app_name_lower = app_name.lower()
    app_names = [app_name_lower, f"{app_name_lower}.exe"]
    
    # Get total stats
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
    
    # Get usage by hour (24 items)
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
    
    # Build 24-hour array
    usage_by_hour = [{"hour": h, "duration_seconds": 0} for h in range(24)]
    for stat in hourly_stats:
        if stat.hour:
            hour_int = int(stat.hour)
            usage_by_hour[hour_int]["duration_seconds"] = int(stat.total or 0)
    
    # Get usage by day
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
    
    # Format dates
    first_use_date = None
    last_use_date = None
    if total_stats.first_use:
        try:
            if isinstance(total_stats.first_use, str):
                first_use_date = total_stats.first_use[:10]
            else:
                first_use_date = total_stats.first_use.strftime('%Y-%m-%d')
        except Exception:
            pass
    if total_stats.last_use:
        try:
            if isinstance(total_stats.last_use, str):
                last_use_date = total_stats.last_use[:10]
            else:
                last_use_date = total_stats.last_use.strftime('%Y-%m-%d')
        except Exception:
            pass
    
    response = {
        "app_name": app_name,
        "total_duration_seconds": total_seconds,
        "total_duration_hours": round(total_seconds / 3600, 2),
        "sessions_count": sessions_count,
        "avg_session_duration_seconds": avg_session,
        "usage_by_hour": usage_by_hour,
        "usage_by_day": usage_by_day,
        "first_use_date": first_use_date,
        "last_use_date": last_use_date
    }
    
    # Cache for 5 minutes
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
    """
    Get usage trends for a specific application over time.
    """
    import logging
    logger = logging.getLogger("reports")
    
    # Limit days for performance
    days = min(days, 60)
    
    # Check cache
    cache_key = f"app_trends:{device_id}:{app_name}:{days}"
    cached = stats_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Verify ownership
    verify_device_ownership(device_id, current_user.id, db)
    
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    
    # Handle app_name with or without .exe
    app_name_lower = app_name.lower()
    app_names = [app_name_lower, f"{app_name_lower}.exe"]
    
    results = []
    for i in range(days):
        day = now_utc - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        # Get daily stats for this app
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
        
        # Format times
        first_use = None
        last_use = None
        if stats.first_use:
            try:
                if isinstance(stats.first_use, str):
                    from dateutil import parser
                    first_use = parser.parse(stats.first_use).strftime('%H:%M')
                else:
                    first_use = stats.first_use.strftime('%H:%M')
            except Exception:
                pass
        if stats.last_use:
            try:
                if isinstance(stats.last_use, str):
                    from dateutil import parser
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
    
    # Reverse to show oldest first
    results.reverse()
    
    # Cache for 5 minutes
    stats_cache.set(cache_key, results, ttl=300)
    
    return results
