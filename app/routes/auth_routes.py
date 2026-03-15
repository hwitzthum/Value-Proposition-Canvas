"""
Authentication endpoints: register, login, logout, me.
Rate-limited at 5/min for auth actions, 3/hour for registration.
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import (
    bearer_scheme,
    create_session,
    get_current_user,
    hash_password,
    invalidate_session,
    is_account_locked,
    record_failed_login,
    verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserPublic,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiting — shared limiter from security module
from ..security import limiter  # noqa: E402

RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")
RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "3/hour")


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Account starts in 'pending' status until admin approval."""

    # Check if email already exists – use uniform message to prevent enumeration
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        # Don't reveal that the email exists
        logger.info("Registration attempt for existing email: %s", data.email)
        return MessageResponse(
            message="If this email is not already registered, you will receive approval notification."
        )

    user = User(
        email=data.email.lower(),
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        status="pending",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Race condition: another request registered this email concurrently
        logger.info("Registration race for email: %s", data.email)
        return MessageResponse(
            message="If this email is not already registered, you will receive approval notification."
        )

    logger.info("New user registered: %s (pending approval)", data.email)
    return MessageResponse(
        message="If this email is not already registered, you will receive approval notification."
    )


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=AuthResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a session token."""

    # Uniform error for all failure cases
    _login_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user:
        raise _login_error

    # Check lockout
    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed attempts. Try again later.",
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        record_failed_login(db, user)
        raise _login_error

    # Check account status
    if user.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is pending admin approval.",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Contact an administrator.",
        )

    # Create session — use X-Forwarded-For when behind a proxy
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )
    token = create_session(db, user, ip_address=ip)

    logger.info("User logged in: %s", user.email)
    return AuthResponse(
        token=token,
        user=UserPublic.model_validate(user),
    )


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invalidate the current session."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        invalidate_session(db, token)

    logger.info("User logged out: %s", user.email)
    return MessageResponse(message="Logged out successfully.")


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserPublic.model_validate(user)
