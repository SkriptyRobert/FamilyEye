"""
Shared pytest fixtures for backend tests.
"""
import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.database import Base, get_db
from app.models import User, Device, Rule, UsageLog, PairingToken


@pytest.fixture(scope="function")
def db_engine():
    """Engine with temp file so TestClient (other thread) can open a new connection to same DB."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test. Data committed here is visible to get_db in request thread."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


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
