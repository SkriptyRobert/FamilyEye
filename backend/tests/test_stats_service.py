"""
Tests for stats service functions.
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.services import stats_service
from app.models import UsageLog, Device


def test_calculate_day_usage_minutes(db_session, test_device):
    """Test daily usage calculation counts unique minutes."""
    now = datetime.now(timezone.utc)
    day_str = now.strftime('%Y-%m-%d')
    
    # Add logs in same minute (should count as 1 minute)
    for i in range(5):
        log = UsageLog(
            device_id=test_device.id,
            app_name="YouTube",
            duration=60,
            timestamp=now.replace(second=i*10)
        )
        db_session.add(log)
    
    # Add log in different minute (should count as 2 minutes total)
    log2 = UsageLog(
        device_id=test_device.id,
        app_name="YouTube",
        duration=60,
        timestamp=now.replace(minute=now.minute + 1)
    )
    db_session.add(log2)
    db_session.commit()
    
    minutes = stats_service.calculate_day_usage_minutes(
        db_session,
        test_device.id,
        day_str
    )
    
    assert minutes == 2, "Should count unique minutes, not total logs"


def test_get_app_day_duration(db_session, test_device):
    """Test app duration calculation sums correctly."""
    now = datetime.now(timezone.utc)
    day_str = now.strftime('%Y-%m-%d')
    
    # Add multiple logs for same app
    for duration in [60, 120, 180]:
        log = UsageLog(
            device_id=test_device.id,
            app_name="YouTube",
            duration=duration,
            timestamp=now
        )
        db_session.add(log)
    
    db_session.commit()
    
    total = stats_service.get_app_day_duration(
        db_session,
        test_device.id,
        ["youtube"],
        day_str
    )
    
    assert total == 360, "Should sum all durations (60+120+180=360)"


def test_get_activity_boundaries(db_session, test_device):
    """Test activity boundaries return first and last times."""
    now = datetime.now(timezone.utc)
    day_str = now.strftime('%Y-%m-%d')
    
    # Add logs at different times
    log1 = UsageLog(
        device_id=test_device.id,
        app_name="App1",
        duration=60,
        timestamp=now.replace(hour=8, minute=0)
    )
    log2 = UsageLog(
        device_id=test_device.id,
        app_name="App2",
        duration=60,
        timestamp=now.replace(hour=20, minute=30)
    )
    db_session.add_all([log1, log2])
    db_session.commit()
    
    first, last = stats_service.get_activity_boundaries(
        db_session,
        test_device.id,
        day_str
    )
    
    assert first == "08:00", "Should return first activity time"
    assert last == "20:30", "Should return last activity time"
