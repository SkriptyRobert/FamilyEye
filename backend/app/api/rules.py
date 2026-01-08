"""Rules management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Rule, Device, User
from ..schemas import RuleCreate, RuleResponse, AgentRulesRequest, AgentRulesResponse
from ..api.auth import get_current_parent
from ..api.devices import verify_device_api_key

router = APIRouter()


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
    
    # Check for existing rule of the same type for this app/website
    existing_rule_query = db.query(Rule).filter(
        Rule.device_id == rule_data.device_id,
        Rule.rule_type == rule_data.rule_type
    )
    
    if rule_data.app_name:
        existing_rule_query = existing_rule_query.filter(Rule.app_name == rule_data.app_name)
    elif rule_data.website_url:
        existing_rule_query = existing_rule_query.filter(Rule.website_url == rule_data.website_url)
    elif rule_data.rule_type in ["daily_limit", "lock_device"]:
        # Singleton rules per device
        pass
        
    existing_rule = existing_rule_query.first()
    
    if existing_rule:
        # Update existing rule
        for key, value in rule_data.dict().items():
            setattr(existing_rule, key, value)
        
        db.commit()
        db.refresh(existing_rule)
        return existing_rule

    new_rule = Rule(**rule_data.dict())
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    
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
    
    db.delete(rule)
    db.commit()
    
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
    
    rules = db.query(Rule).filter(
        Rule.device_id == device.id,
        Rule.enabled == True
    ).all()
    
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
    
    # Calculate daily usage as ELAPSED time since first activity today
    # This aligns with user expectation: "PC is on for X minutes"
    first_log_ts = db.query(func.min(UsageLog.timestamp)).filter(
        UsageLog.device_id == device.id,
        UsageLog.timestamp >= query_start_utc
    ).scalar()
    
    if first_log_ts:
        # Calculate elapsed seconds from first log until now (UTC)
        # Use naive utcnow() to match naive database timestamps
        elapsed_delta = datetime.utcnow() - first_log_ts
        total_usage = max(0, int(elapsed_delta.total_seconds()))
    else:
        total_usage = 0
    
    # Usage by app (sum of durations for each app)
    usage_by_app_rows = db.query(
        UsageLog.app_name,
        func.sum(UsageLog.duration)
    ).filter(
        UsageLog.device_id == device.id,
        UsageLog.timestamp >= query_start_utc
    ).group_by(UsageLog.app_name).all()
    
    # CAP each app's time to not exceed elapsed time
    # This prevents confusing display where app time > total time
    # (can happen if apps run concurrently, but user expects logical consistency)
    usage_by_app = {}
    for row in usage_by_app_rows:
        app_name = row[0]
        app_duration = row[1] if row[1] else 0
        # Cap to elapsed time - no app can show more time than monitoring has been active
        capped_duration = min(app_duration, total_usage) if total_usage > 0 else app_duration
        usage_by_app[app_name] = capped_duration
    
    return {
        "rules": rules,
        "daily_usage": int(total_usage),
        "usage_by_app": usage_by_app,
        "server_time": datetime.now(timezone.utc),
        "server_day_id": now_device.strftime("%Y-%m-%d")  # Device's local day for cross-midnight sync
    }

