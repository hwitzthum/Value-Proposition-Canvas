"""
SQLAlchemy ORM models for the Value Proposition Canvas application.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR, JSON
import uuid as _uuid

from .database import Base


# ---------------------------------------------------------------------------
# Portable UUID type – works on both PostgreSQL (native UUID) and SQLite.
# ---------------------------------------------------------------------------
class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses PostgreSQL UUID when available,
    otherwise stores as CHAR(36)."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, _uuid.UUID) else _uuid.UUID(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, _uuid.UUID):
            return value
        return _uuid.UUID(value)


# ---------------------------------------------------------------------------
# Portable JSONB type – uses native JSONB on PostgreSQL, JSON on SQLite.
# ---------------------------------------------------------------------------
class PortableJSON(TypeDecorator):
    """Uses JSONB on PostgreSQL, plain JSON elsewhere."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid():
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=_new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    approved_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    canvases = relationship("Canvas", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
    )


# ---------------------------------------------------------------------------
# UserSession
# ---------------------------------------------------------------------------
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(GUID(), primary_key=True, default=_new_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(45), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------
class Canvas(Base):
    __tablename__ = "canvases"

    id = Column(GUID(), primary_key=True, default=_new_uuid)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), default="Untitled Canvas", nullable=False)
    job_description = Column(Text, default="", nullable=False)
    pain_points = Column(PortableJSON(), default=list, nullable=False)
    gain_points = Column(PortableJSON(), default=list, nullable=False)
    wizard_step = Column(Integer, default=0, nullable=False)
    job_validated = Column(Boolean, default=False, nullable=False)
    pains_validated = Column(Boolean, default=False, nullable=False)
    gains_validated = Column(Boolean, default=False, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="canvases")

    __table_args__ = (
        Index("ix_canvases_user_current", "user_id", "is_current"),
    )
