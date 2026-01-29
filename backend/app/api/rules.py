"""Rules management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from ..database import get_db
from ..models import Rule, Device, User
from ..schemas import RuleCreate, RuleResponse, AgentRulesRequest, AgentRulesResponse
from ..api.auth import get_current_parent
from ..api.devices.utils import verify_device_api_key
from ..api.websocket import send_command_to_device

router = APIRouter()
logger = logging.getLogger("rules")


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: RuleCreate,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Create a new rule."""
    # Verify device belongs to parent
    device = db.query(Device).filter(
        Device.id == rule_data.device_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Logic to distinguish between updating existing rule vs creating new
    # 1. App/Web rules: Usually overwrite to prevent duplicates (per user request)
    # 2. Device Schedules: Allow multiple (per user request)
    # 3. Device Limits/Lock: Singleton (overwrite)
    
    should_check_existing = False
    existing_rule_query = db.query(Rule).filter(
        Rule.device_id == rule_data.device_id,
        Rule.rule_type == rule_data.rule_type
    )
    
    if rule_data.app_name:
        # specific app rule - overwrite to avoid 10 limits for same app
        existing_rule_query = existing_rule_query.filter(Rule.app_name == rule_data.app_name)
        should_check_existing = True
    elif rule_data.website_url:
        existing_rule_query = existing_rule_query.filter(Rule.website_url == rule_data.website_url)
        should_check_existing = True
    else:
        # Device-wide rule
        # Critical fix: Ensure we don't accidentally match App rules by enforcing None
        existing_rule_query = existing_rule_query.filter(
            Rule.app_name.is_(None), 
            Rule.website_url.is_(None)
        )
        
        if rule_data.rule_type in ["daily_limit", "lock_device"]:
            should_check_existing = True
        elif rule_data.rule_type == "schedule":
            # Allow multiple schedules for device
            should_check_existing = False
        else:
            should_check_existing = True
            
    existing_rule = existing_rule_query.first() if should_check_existing else None
    
    if existing_rule:
        # Update existing rule
        logger.info(f"Updating existing rule id={existing_rule.id}: type={rule_data.rule_type}, app={rule_data.app_name}, time_limit={rule_data.time_limit}")
        for key, value in rule_data.dict().items():
            setattr(existing_rule, key, value)
        
        db.commit()
        db.refresh(existing_rule)
        logger.info(f"Rule updated successfully: id={existing_rule.id}")
        # Notify agent
        await send_command_to_device(device.device_id, "REFRESH_RULES")
        return existing_rule

    new_rule = Rule(**rule_data.dict())
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    
    logger.info(f"Created new rule: id={new_rule.id}, type={new_rule.rule_type}, device_id={new_rule.device_id}, app={new_rule.app_name}, time_limit={new_rule.time_limit}")
    # Notify agent
    await send_command_to_device(device.device_id, "REFRESH_RULES")
    return new_rule


@router.get("/device/{device_id}", response_model=List[RuleResponse])
async def get_device_rules(
    device_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get all rules for a device."""
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
    
    rules = db.query(Rule).filter(
        Rule.device_id == device_id,
        Rule.enabled == True
    ).all()
    
    return rules


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Get rule by ID."""
    rule = db.query(Rule).join(Device).filter(
        Rule.id == rule_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: RuleCreate,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Update a rule."""
    rule = db.query(Rule).join(Device).filter(
        Rule.id == rule_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    for key, value in rule_data.dict().items():
        setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    
    # Notify agent
    if rule.device:
        await send_command_to_device(rule.device.device_id, "REFRESH_RULES")

    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    """Delete a rule."""
    rule = db.query(Rule).join(Device).filter(
        Rule.id == rule_id,
        Device.parent_id == current_user.id
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found"
        )
    
    # Save device_id before deletion to notify agent after commit
    device_id_for_agent = rule.device.device_id if rule.device else None
    
    db.delete(rule)
    db.commit()
    
    # Notify agent
    if device_id_for_agent:
        await send_command_to_device(device_id_for_agent, "REFRESH_RULES")

    return None


# Agent endpoint for fetching rules
@router.post("/agent/fetch", response_model=AgentRulesResponse)
async def agent_fetch_rules(
    request: AgentRulesRequest,
    db: Session = Depends(get_db)
):
    """Agent endpoint to fetch rules for device."""
    device = verify_device_api_key(request.device_id, request.api_key, db)
    db.commit()  # Persist last_seen update from verify_device_api_key
    
    rules_db = db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.enabled == True
    ).all()
    
    # Debug: Log what rules are returned to agent
    time_limit_rules = [r for r in rules_db if r.rule_type == "time_limit"]
    logger.info(f"Agent fetch for device_id={device.device_id} (db_id={device.id}): {len(rules_db)} total rules, {len(time_limit_rules)} time_limit rules")
    for r in time_limit_rules:
        logger.info(f"  - TIME_LIMIT: app={r.app_name}, limit={r.time_limit}min, enabled={r.enabled}")

    # Pre-process rules to fix schedule format for agent (expand '0-6' to '0,1,2...')
    rules = []
    for r in rules_db:
        # Pydantic v2 uses model_validate, fallback to from_orm if needed
        try:
            rule_model = RuleResponse.model_validate(r)
        except AttributeError:
            rule_model = RuleResponse.from_orm(r)

        if rule_model.schedule_days and '-' in rule_model.schedule_days and ',' not in rule_model.schedule_days:
            try:
                parts = rule_model.schedule_days.split('-')
                if len(parts) == 2:
                    start, end = int(parts[0]), int(parts[1])
                    if start <= end:
                        rule_model.schedule_days = ",".join(str(i) for i in range(start, end + 1))
            except (ValueError, TypeError):
                pass
        rules.append(rule_model)
    
    # Calculate daily usage as COUNT of unique MINUTES (truncated to minute level)
    # This ensures all apps logged in same minute count as 1 minute, not N
    from datetime import datetime, timezone, timedelta
    
    # Calculate "Today" based on DEVICE'S local time
    # This aligns backend limits with agent's local daily reset
    now_utc = datetime.now(timezone.utc)
    offset_seconds = device.timezone_offset or 0
    now_device = now_utc + timedelta(seconds=offset_seconds)
    
    # Device's start of day (Local)
    device_today_start_local = now_device.replace(hour=0, minute=0, second=0, microsecond=0)
    # Convert back to UTC for database query
    query_start_utc = device_today_start_local - timedelta(seconds=offset_seconds)
    # Ensure it's unaware or aware matching DB (SQLite is usually naive string, but usually we store naive UTC)
    # If DB stores naive UTC, we need naive query_start_utc.
    # reporter.py sends datetime.utcnow(), so it's naive UTC.
    query_start_utc = query_start_utc.replace(tzinfo=None)
    
    from ..models import UsageLog
    from sqlalchemy import func
    from ..db_utils import minute_bucket

    # Count unique report minutes - truncate timestamp to minute level
    unique_minutes = db.query(
        func.count(func.distinct(minute_bucket(db, UsageLog.timestamp)))
    ).filter(
        UsageLog.device_id == device.id,
        UsageLog.timestamp >= query_start_utc
    ).scalar() or 0
    
    reporting_interval = 60  # seconds
    total_usage = unique_minutes * reporting_interval
    
    # Usage by app (sum of durations for each app)
    usage_by_app_rows = db.query(
        UsageLog.app_name,
        func.sum(UsageLog.duration)
    ).filter(
        UsageLog.device_id == device.id,
        UsageLog.timestamp >= query_start_utc
    ).group_by(UsageLog.app_name).all()
    
    usage_by_app = {row[0]: row[1] for row in usage_by_app_rows}
    
    return {
        "rules": rules,
        "daily_usage": int(total_usage),
        "usage_by_app": usage_by_app,
        "server_time": datetime.now(timezone.utc),
        "settings_protection": device.settings_protection or "full",
        "settings_exceptions": device.settings_exceptions
    }

