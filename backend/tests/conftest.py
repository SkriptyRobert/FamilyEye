"""
Shared pytest fixtures for backend tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.database import Base, get_db
from app.models import User, Device, Rule, UsageLog, PairingToken


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    Uses in-memory SQLite for fast test execution.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password_here",
        role="parent"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_device(db_session: Session, test_user: User) -> Device:
    """Create a test device."""
    device = Device(
        name="Test Device",
        device_id="test-device-id",
        device_type="android",
        parent_id=test_user.id,
        mac_address="AA:BB:CC:DD:EE:FF",
        api_key="test-api-key"
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


@pytest.fixture
def override_get_db(db_session: Session):
    """Override get_db dependency for FastAPI tests."""
    def _get_db():
        try:
            yield db_session
        finally:
            pass
    
    return _get_db
