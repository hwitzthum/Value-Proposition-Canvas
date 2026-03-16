"""
Authentication endpoints: register, login, logout, me, change-password.
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
    get_current_user_allow_password_change,
    hash_password,
    invalidate_all_user_sessions,
    invalidate_other_sessions,
    invalidate_session,
    is_account_locked,
    record_failed_login,
    verify_password,
)
from ..database import get_db
from ..models import User
from ..schemas import (
    AuthResponse,
    ChangePasswordRequest,
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
    """Register a new user. Account starts in 'pending' status until admin approval.
    If email belongs to a declined user, resets the record to pending."""

    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        if existing.status == "declined":
            # Allow re-registration: reset the declined record
            existing.password_hash = hash_password(data.password)
            existing.display_name = data.display_name
            existing.status = "pending"
            existing.must_change_password = False
            existing.approved_by = None
            existing.approved_at = None
            existing.failed_login_attempts = 0
            existing.locked_until = None
            existing.updated_at = datetime.now(timezone.utc)
            # Invalidate any stale sessions
            invalidate_all_user_sessions(db, existing.id)
            db.commit()
            logger.info("Declined user re-registered: %s", data.email)
        else:
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

    # Check account status — use the same error message for all non-active
    # states to prevent account enumeration (attacker can't distinguish
    # pending vs paused vs declined).
    if user.status != "active":
        raise _login_error

    # Create session — use spoofing-resistant IP extraction
    from ..security import get_real_ip
    ip = get_real_ip(request)
    token = create_session(db, user, ip_address=ip)

    logger.info("User logged in: %s", user.email)
    return AuthResponse(
        token=token,
        user=UserPublic.model_validate(user),
        must_change_password=user.must_change_password,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    user: User = Depends(get_current_user_allow_password_change),
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
async def me(user: User = Depends(get_current_user_allow_password_change)):
    """Return the currently authenticated user."""
    return UserPublic.model_validate(user)


# ---------------------------------------------------------------------------
# POST /api/auth/change-password
# ---------------------------------------------------------------------------
@router.post("/change-password", response_model=MessageResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user_allow_password_change),
    db: Session = Depends(get_db),
):
    """Change the current user's password. Invalidates other sessions."""
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    db.commit()

    # Invalidate all other sessions (keep the current one)
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if current_token:
        invalidate_other_sessions(db, user.id, current_token)

    logger.info("Password changed for user %s", user.email)
    return MessageResponse(message="Password changed successfully.")
