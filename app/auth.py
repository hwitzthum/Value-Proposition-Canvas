"""
Authentication and session management.
- Password hashing with bcrypt (12 rounds)
- Session-based auth with secure token generation
- Account lockout after 5 failed attempts (15-minute lock)
- FastAPI dependency for extracting current user from Bearer token
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password hashing – using bcrypt directly (passlib is incompatible with bcrypt 5.x)
# ---------------------------------------------------------------------------
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    # bcrypt only handles the first 72 bytes; truncate safely
    pw_bytes = password.encode("utf-8")[:72]
    salt = _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return _bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pw_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return _bcrypt.checkpw(pw_bytes, hashed_bytes)


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def create_session(db: Session, user: User, ip_address: Optional[str] = None) -> str:
    """Create a new session token for the user."""
    token = secrets.token_urlsafe(48)
    session = UserSession(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS),
        ip_address=ip_address,
    )
    db.add(session)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    logger.info("Session created for user %s", user.email)
    return token


def invalidate_session(db: Session, token: str) -> bool:
    """Delete a session by token."""
    result = db.execute(
        delete(UserSession).where(UserSession.token == token)
    )
    db.commit()
    return result.rowcount > 0


def get_session_user(db: Session, token: str) -> Optional[User]:
    """Look up a user by session token. Returns None if expired or missing."""
    session = (
        db.query(UserSession)
        .filter(UserSession.token == token)
        .first()
    )
    if not session:
        return None

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        # Expired – clean it up lazily
        db.delete(session)
        db.commit()
        return None

    return session.user


def cleanup_expired_sessions(db: Session) -> int:
    """Remove all expired sessions. Called lazily or via cron."""
    result = db.execute(
        delete(UserSession).where(UserSession.expires_at < datetime.now(timezone.utc))
    )
    db.commit()
    return result.rowcount


# ---------------------------------------------------------------------------
# Account lockout
# ---------------------------------------------------------------------------
def record_failed_login(db: Session, user: User) -> None:
    """Increment failed login counter; lock if threshold exceeded."""
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        logger.warning("Account locked for user %s after %d failed attempts",
                        user.email, user.failed_login_attempts)
    db.commit()


def is_account_locked(user: User) -> bool:
    """Check if the account is currently locked."""
    if user.locked_until is None:
        return False
    return user.locked_until.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# FastAPI dependency – extract current user from Bearer token
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)

# Uniform error to prevent user enumeration
_AUTH_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired authentication token.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: returns the authenticated user or raises 401."""
    if credentials is None:
        raise _AUTH_ERROR

    user = get_session_user(db, credentials.credentials)
    if user is None:
        raise _AUTH_ERROR

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Contact an administrator.",
        )

    return user


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency: returns the authenticated admin user or raises 403."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
