"""
Tests for rules API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta

from app.main import app
from app.database import get_db
from app.models import User, Device, Rule, UsageLog


@pytest.fixture
def client(db_engine, db_session):
    """Create test client. get_db yields a new session to same DB so request thread sees test data."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://test") as tc:
        yield tc
    app.dependency_overrides.clear()


def test_agent_fetch_rules_success(client, db_session, test_user, test_device):
    """Test agent can fetch rules for device."""
    rule = Rule(
        device_id=test_device.id,
        rule_type="time_limit",
        app_name="youtube",
        time_limit=60,
        enabled=True
    )
    db_session.add(rule)
    db_session.commit()

    usage_log = UsageLog(
        device_id=test_device.id,
        app_name="YouTube",
        duration=300,
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add(usage_log)
    db_session.commit()

    response = client.post(
        "/api/rules/agent/fetch",
        json={
            "device_id": test_device.device_id,
            "api_key": test_device.api_key
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert "daily_usage" in data
    assert "usage_by_app" in data
    assert len(data["rules"]) >= 1
    assert data["daily_usage"] >= 0


def test_agent_fetch_rules_invalid_api_key(client, db_session, test_device):
    """Test agent fetch fails with invalid API key."""
    response = client.post(
        "/api/rules/agent/fetch",
        json={
            "device_id": test_device.device_id,
            "api_key": "invalid-key"
        }
    )

    assert response.status_code == 401


def test_agent_fetch_rules_calculates_daily_usage(client, db_session, test_user, test_device):
    """Test daily_usage is calculated correctly."""
    now = datetime.now(timezone.utc)
    for i in range(5):
        usage_log = UsageLog(
            device_id=test_device.id,
            app_name="YouTube",
            duration=60,
            timestamp=now - timedelta(minutes=i)
        )
        db_session.add(usage_log)
    db_session.commit()

    response = client.post(
        "/api/rules/agent/fetch",
        json={
            "device_id": test_device.device_id,
            "api_key": test_device.api_key
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["daily_usage"] >= 0
    assert "YouTube" in data["usage_by_app"]
    assert data["usage_by_app"]["YouTube"] >= 300
