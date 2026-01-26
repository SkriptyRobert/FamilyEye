"""
Tests for rules API endpoints.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import Depends
from datetime import datetime, timezone, timedelta
import asyncio

from app.main import app
from app.database import get_db
from app.models import User, Device, Rule, UsageLog


@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    # Override get_db dependency before creating client
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create async client
    transport = ASGITransport(app=app)
    ac = AsyncClient(transport=transport, base_url="http://test")
    
    yield ac
    
    # Clean up
    asyncio.run(ac.aclose())
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_user, client):
    """Get auth headers for authenticated requests."""
    # Create token (simplified - in real app use proper auth)
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.email, "password": "test_password"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.mark.asyncio
async def test_agent_fetch_rules_success(client, db_session, test_user, test_device):
    """Test agent can fetch rules for device."""
    # Create a rule
    rule = Rule(
        device_id=test_device.id,
        rule_type="time_limit",
        app_name="youtube",
        time_limit=60,
        enabled=True
    )
    db_session.add(rule)
    db_session.commit()

    # Create usage log for daily_usage calculation
    usage_log = UsageLog(
        device_id=test_device.id,
        app_name="YouTube",
        duration=300,  # 5 minutes
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add(usage_log)
    db_session.commit()

    response = await client.post(
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


@pytest.mark.asyncio
async def test_agent_fetch_rules_invalid_api_key(client, db_session, test_device):
    """Test agent fetch fails with invalid API key."""
    response = await client.post(
        "/api/rules/agent/fetch",
        json={
            "device_id": test_device.device_id,
            "api_key": "invalid-key"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agent_fetch_rules_calculates_daily_usage(client, db_session, test_user, test_device):
    """Test daily_usage is calculated correctly."""
    # Add multiple usage logs
    now = datetime.now(timezone.utc)
    for i in range(5):
        usage_log = UsageLog(
            device_id=test_device.id,
            app_name="YouTube",
            duration=60,  # 1 minute each
            timestamp=now - timedelta(minutes=i)
        )
        db_session.add(usage_log)
    db_session.commit()

    response = await client.post(
        "/api/rules/agent/fetch",
        json={
            "device_id": test_device.device_id,
            "api_key": test_device.api_key
        }
    )

    assert response.status_code == 200
    data = response.json()
    # Should calculate based on unique minutes
    assert data["daily_usage"] >= 0
    assert "YouTube" in data["usage_by_app"]
    assert data["usage_by_app"]["YouTube"] >= 300  # 5 * 60 seconds
