"""
Tests that verify db_utils and stats/summary logic work on PostgreSQL.

Run only when TEST_POSTGRES_URL is set (e.g. in CI with postgres service):
  set TEST_POSTGRES_URL=postgresql://user:pass@localhost:5432/familyeye_test
  pip install psycopg2-binary
  pytest tests/test_postgres_compat.py -v
"""
import os
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from sqlalchemy import func

from app.database import Base
from app.models import User, Device, UsageLog
from app.db_utils import date_expr, hour_expr
from app.services import stats_service
from app.services import summary_service


def _get_postgres_url():
    return os.environ.get("TEST_POSTGRES_URL", "").strip()


@pytest.fixture(scope="module")
def postgres_engine():
    """Create PostgreSQL engine from TEST_POSTGRES_URL. Skip if not set."""
    url = _get_postgres_url()
    if not url or not url.startswith("postgresql"):
        pytest.skip("TEST_POSTGRES_URL not set or not postgresql (e.g. postgresql://user:pass@localhost:5432/db)")
    try:
        engine = create_engine(url, pool_pre_ping=True)
        engine.connect()
    except Exception as e:
        pytest.skip(f"Cannot connect to PostgreSQL: {e}")
    yield engine
    engine.dispose()


@pytest.fixture
def postgres_session(postgres_engine):
    """Fresh PostgreSQL session per test; creates and drops schema."""
    Base.metadata.create_all(postgres_engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(postgres_engine)


@pytest.fixture
def postgres_user(postgres_session: Session) -> User:
    """Create a test user in PostgreSQL."""
    user = User(
        email="pgtest@example.com",
        password_hash="hashed",
        role="parent"
    )
    postgres_session.add(user)
    postgres_session.commit()
    postgres_session.refresh(user)
    return user


@pytest.fixture
def postgres_device(postgres_session: Session, postgres_user: User) -> Device:
    """Create a test device in PostgreSQL."""
    device = Device(
        name="PG Test Device",
        device_id="pg-test-device-id",
        device_type="android",
        parent_id=postgres_user.id,
        mac_address="AA:BB:CC:DD:EE:FF",
        api_key="pg-test-api-key"
    )
    postgres_session.add(device)
    postgres_session.commit()
    postgres_session.refresh(device)
    return device


def test_postgres_calculate_day_usage_minutes(postgres_session, postgres_device):
    """PostgreSQL: daily usage counts unique minutes (minute_bucket)."""
    now = datetime.now(timezone.utc)
    day_str = now.strftime("%Y-%m-%d")

    for i in range(5):
        log = UsageLog(
            device_id=postgres_device.id,
            app_name="YouTube",
            duration=60,
            timestamp=now.replace(second=i * 10)
        )
        postgres_session.add(log)
    log2 = UsageLog(
        device_id=postgres_device.id,
        app_name="YouTube",
        duration=60,
        timestamp=now.replace(minute=now.minute + 1)
    )
    postgres_session.add(log2)
    postgres_session.commit()

    minutes = stats_service.calculate_day_usage_minutes(
        postgres_session,
        postgres_device.id,
        day_str
    )
    assert minutes == 2


def test_postgres_get_app_day_duration(postgres_session, postgres_device):
    """PostgreSQL: app duration sums correctly (minute_bucket in get_app_day_duration)."""
    now = datetime.now(timezone.utc)
    day_str = now.strftime("%Y-%m-%d")

    for duration in [60, 120, 180]:
        log = UsageLog(
            device_id=postgres_device.id,
            app_name="YouTube",
            duration=duration,
            timestamp=now
        )
        postgres_session.add(log)
    postgres_session.commit()

    total = stats_service.get_app_day_duration(
        postgres_session,
        postgres_device.id,
        ["youtube"],
        day_str
    )
    assert total == 360


def test_postgres_get_activity_boundaries(postgres_session, postgres_device):
    """PostgreSQL: activity boundaries use day_range_utc and return HH:MM."""
    now = datetime.now(timezone.utc)
    day_str = now.strftime("%Y-%m-%d")

    log1 = UsageLog(
        device_id=postgres_device.id,
        app_name="App1",
        duration=60,
        timestamp=now.replace(hour=8, minute=0)
    )
    log2 = UsageLog(
        device_id=postgres_device.id,
        app_name="App2",
        duration=60,
        timestamp=now.replace(hour=20, minute=30)
    )
    postgres_session.add_all([log1, log2])
    postgres_session.commit()

    first, last = stats_service.get_activity_boundaries(
        postgres_session,
        postgres_device.id,
        day_str
    )
    assert first == "08:00"
    assert last == "20:30"


def test_postgres_calculate_day_usage_summary(postgres_session, postgres_device):
    """PostgreSQL: summary_service.calculate_day_usage uses minute_bucket."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    for i in range(3):
        log = UsageLog(
            device_id=postgres_device.id,
            app_name="Browser",
            duration=120,
            timestamp=now.replace(minute=now.minute + i)
        )
        postgres_session.add(log)
    postgres_session.commit()

    total_seconds = summary_service.calculate_day_usage(
        postgres_session,
        postgres_device.id,
        day_start,
        day_end
    )
    # 3 logs in 3 distinct minutes -> 3 * 60 = 180 seconds
    assert total_seconds == 180


def test_postgres_usage_by_hour_query(postgres_session, postgres_device):
    """PostgreSQL: usage-by-hour style query (date_expr, hour_expr) runs and returns correct types."""
    now = datetime.now(timezone.utc)
    for h in [8, 12, 20]:
        log = UsageLog(
            device_id=postgres_device.id,
            app_name="App",
            duration=300,
            timestamp=now.replace(hour=h, minute=0, second=0, microsecond=0)
        )
        postgres_session.add(log)
    postgres_session.commit()

    results = postgres_session.query(
        date_expr(postgres_session, UsageLog.timestamp).label("date"),
        hour_expr(postgres_session, UsageLog.timestamp).label("hour"),
        func.sum(UsageLog.duration).label("total_seconds"),
    ).filter(
        UsageLog.device_id == postgres_device.id,
        UsageLog.timestamp >= now - timedelta(days=1),
    ).group_by(
        date_expr(postgres_session, UsageLog.timestamp),
        hour_expr(postgres_session, UsageLog.timestamp),
    ).all()

    assert len(results) >= 1
    for row in results:
        assert row.date is not None
        assert row.hour is not None
        assert int(row.hour) in range(0, 24)
        assert row.total_seconds >= 0
