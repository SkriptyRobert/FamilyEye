"""Database initialization and session management."""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from .config import settings

# SQLite database path
DATABASE_URL = settings.DATABASE_URL

# Configure engine with WAL mode for SQLite
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 20.0  # busy_timeout v sekundách (20000ms)
        }
    )
    
    # Zapnout WAL mode při každém připojení
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Nastavit SQLite PRAGMA při každém připojení."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=20000")  # 20 sekund
        cursor.close()
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

