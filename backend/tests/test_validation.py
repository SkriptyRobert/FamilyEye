import pytest
from httpx import ASGITransport, AsyncClient
import os
import sys
import asyncio

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

@pytest.fixture
def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    ac = AsyncClient(transport=transport, base_url="http://test")
    yield ac
    asyncio.run(ac.aclose())

@pytest.mark.asyncio
async def test_api_malformed_json(client):
    # Sending invalid JSON string
    response = await client.post(
        "/api/reports/agent/report", 
        content="not a json", 
        headers={"Content-Type": "application/json"}
    )
    # FastAPI/Pydantic should catch this and return 422 Unprocessable Entity, not 500
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_api_missing_required_fields(client):
    # Missing api_key and device_id
    payload = {
        "usage_logs": []
    }
    response = await client.post("/api/reports/agent/report", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_api_invalid_data_types(client):
    # duration as string instead of int
    payload = {
        "device_id": "test",
        "api_key": "test",
        "usage_logs": [
            {
                "app_name": "chrome",
                "duration": "invalid_number"
            }
        ]
    }
    response = await client.post("/api/reports/agent/report", json=payload)
    assert response.status_code == 422
