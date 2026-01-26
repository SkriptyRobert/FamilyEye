import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.pairing_service import create_device_from_pairing, generate_pairing_token
from app.models import PairingToken, Device, User

def test_generate_pairing_token():
    db = MagicMock()
    parent_id = 42
    
    token = generate_pairing_token(parent_id, db)
    
    assert token.parent_id == parent_id
    assert token.token is not None
    assert token.used is False
    assert token.expires_at > datetime.now(timezone.utc)
    db.add.assert_called_once()
    db.commit.assert_called_once()

def test_create_device_from_pairing_success():
    db = MagicMock()
    
    # Mock return values for validate_pairing_token and existing device checks
    mock_token = PairingToken(id=1, token="test-token", parent_id=10, used=False, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    
    # Mock the query chain: db.query(PairingToken).filter(...).first()
    db.query.return_value.filter.return_value.first.side_effect = [
        mock_token, # 1. validate_pairing_token
        None,       # 2. existing_device_by_id
        None        # 3. existing_device_by_mac
    ]
    
    # Special case: existing_device_by_mac check
    # The code does db.query(Device).filter(Device.mac_address == mac_address, Device.parent_id == ...).first()
    # Let's mock a sequence of returns for .first()
    
    device = create_device_from_pairing(
        token="test-token",
        device_name="Test Phone",
        device_type="android",
        mac_address="AA:BB:CC:DD:EE:FF",
        device_id="unique-guid",
        db=db
    )
    
    assert device.name == "Test Phone"
    assert device.device_id == "unique-guid"
    assert device.parent_id == 10
    assert mock_token.used is True
    assert db.add.called
    assert db.commit.called
