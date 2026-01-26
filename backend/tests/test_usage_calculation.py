import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.summary_service import calculate_precise_usage

def test_interval_merging():
    # Mock DB session
    db = MagicMock()
    
    # Setup test logs:
    # 1. 10:00:00 - 10:00:30 (30s)
    # 2. 10:00:20 - 10:00:50 (30s, overlaps with #1)
    # 3. 10:01:00 - 10:01:10 (10s)
    
    base_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    # Mock return values from the query
    mock_log1 = MagicMock(app_name="chrome", timestamp=base_time, duration=30)
    mock_log2 = MagicMock(app_name="chrome", timestamp=base_time.replace(second=20), duration=30)
    mock_log3 = MagicMock(app_name="minecraft", timestamp=base_time.replace(minute=1), duration=10)
    
    db.query.return_value.filter.return_value.all.return_value = [mock_log1, mock_log2, mock_log3]
    
    # Call the helper function
    total_usage, elapsed = calculate_precise_usage(db, 1, base_time, base_time)
    
    # Expected result:
    # Segment 1 & 2 merge into: 10:00:00 - 10:00:50 (50 seconds)
    # Segment 3: 10:01:00 - 10:01:10 (10 seconds)
    # Total: 60 seconds
    
    assert total_usage == 60
    assert elapsed == 60

def test_interval_merging_complete_overlap():
    db = MagicMock()
    base_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    # Log 2 is completely inside Log 1
    mock_log1 = MagicMock(app_name="chrome", timestamp=base_time, duration=60)
    mock_log2 = MagicMock(app_name="chrome", timestamp=base_time.replace(second=10), duration=30)
    
    db.query.return_value.filter.return_value.all.return_value = [mock_log1, mock_log2]
    
    total_usage, _ = calculate_precise_usage(db, 1, base_time, base_time)
    
    assert total_usage == 60
