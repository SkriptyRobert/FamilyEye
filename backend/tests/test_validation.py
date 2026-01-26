import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

client = TestClient(app)

def test_api_malformed_json():
    # Sending invalid JSON string
    response = client.post(
        "/api/reports/agent/report", 
        content="not a json", 
        headers={"Content-Type": "application/json"}
    )
    # FastAPI/Pydantic should catch this and return 422 Unprocessable Entity, not 500
    assert response.status_code == 422

def test_api_missing_required_fields():
    # Missing api_key and device_id
    payload = {
        "usage_logs": []
    }
    response = client.post("/api/reports/agent/report", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_api_invalid_data_types():
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
    response = client.post("/api/reports/agent/report", json=payload)
    assert response.status_code == 422
