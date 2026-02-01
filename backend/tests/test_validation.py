"""Tests for API request validation (agent report endpoint)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app, base_url="http://test")


def test_api_malformed_json(client):
    """Invalid JSON body returns 422."""
    response = client.post(
        "/api/reports/agent/report",
        content="not a json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_api_missing_required_fields(client):
    """Missing api_key and device_id returns 422."""
    payload = {"usage_logs": []}
    response = client.post("/api/reports/agent/report", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_api_invalid_data_types(client):
    """duration as string instead of int returns 422."""
    payload = {
        "device_id": "test",
        "api_key": "test",
        "usage_logs": [
            {"app_name": "chrome", "duration": "invalid_number"}
        ]
    }
    response = client.post("/api/reports/agent/report", json=payload)
    assert response.status_code == 422
