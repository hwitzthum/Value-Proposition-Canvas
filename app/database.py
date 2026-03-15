"""
Database configuration and session management.
Uses SQLAlchemy 2.0+ async-compatible patterns with PostgreSQL.
"""

import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vpc_dev.db")

# Render provides DATABASE_URL starting with "postgres://" but SQLAlchemy 2.0
# requires "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine configuration – tune pool for serverless-friendly behaviour.
_engine_kwargs: dict = {
    "echo": os.getenv("SQL_ECHO", "").lower() == "true",
    "future": True,
}

if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_pre_ping": True,
        "pool_recycle": 300,
    })

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# Enable WAL mode for SQLite (better concurrent reads).
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Session:
    """FastAPI dependency – yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@contextmanager
def get_db_context() -> Session:
    """Context manager for use outside FastAPI (scripts, tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all tables – used for development and testing only."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
