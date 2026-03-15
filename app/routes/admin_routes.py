"""
Admin endpoints – user management and dashboard stats.
Requires admin authentication.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from sqlalchemy import delete

from ..auth import (
    get_current_admin,
    hash_password,
    invalidate_all_user_sessions,
    validate_status_transition,
)
from ..database import get_db
from ..models import Canvas, User, UserSession
from ..schemas import (
    AdminResetPasswordRequest,
    AdminStatsResponse,
    AdminUserDetail,
    AdminUserListItem,
    MessageResponse,
    StatusUpdateRequest,
)
from ..security import limiter

logger = logging.getLogger(__name__)

RATE_LIMIT_ADMIN = os.getenv("RATE_LIMIT_ADMIN", "30/minute")

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[AdminUserListItem])
@limiter.limit(RATE_LIMIT_ADMIN)
async def list_users(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", pattern=r"^(pending|active|paused|declined)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all users with canvas counts, paginated."""
    # Subquery for canvas counts — avoids N+1
    canvas_counts = (
        db.query(Canvas.user_id, func.count(Canvas.id).label("canvas_count"))
        .group_by(Canvas.user_id)
        .subquery()
    )

    query = (
        db.query(User, func.coalesce(canvas_counts.c.canvas_count, 0).label("canvas_count"))
        .outerjoin(canvas_counts, User.id == canvas_counts.c.user_id)
    )
    if status_filter:
        query = query.filter(User.status == status_filter)
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)

    result = []
    for user, count in query.all():
        item = AdminUserListItem(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            canvas_count=count,
        )
        result.append(item)

    return result


# ---------------------------------------------------------------------------
# GET /api/admin/users/{user_id}
# ---------------------------------------------------------------------------
@router.get("/users/{user_id}", response_model=AdminUserDetail)
@limiter.limit(RATE_LIMIT_ADMIN)
async def get_user_detail(
    request: Request,
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    canvas_count = db.query(func.count(Canvas.id)).filter(Canvas.user_id == user.id).scalar()

    return AdminUserDetail(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        approved_by=user.approved_by,
        approved_at=user.approved_at,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until,
        canvas_count=canvas_count or 0,
        must_change_password=user.must_change_password,
    )


# ---------------------------------------------------------------------------
# PATCH /api/admin/users/{user_id}/status
# ---------------------------------------------------------------------------
@router.patch("/users/{user_id}/status", response_model=MessageResponse)
@limiter.limit(RATE_LIMIT_ADMIN)
async def update_user_status(
    request: Request,
    user_id: UUID,
    data: StatusUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Approve, pause, or decline a user. Enforces valid transitions."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status.")

    # Block admin-on-admin changes
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot change another admin's status.")

    # Enforce valid transitions
    old_status = user.status
    if not validate_status_transition(old_status, data.status):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {old_status} -> {data.status}.",
        )

    user.status = data.status

    if data.status == "active" and old_status == "pending":
        user.approved_by = admin.id
        user.approved_at = datetime.now(timezone.utc)

    # Reset lockout when approving
    if data.status == "active":
        user.failed_login_attempts = 0
        user.locked_until = None

    # Invalidate sessions on paused/declined
    if data.status in ("paused", "declined"):
        invalidate_all_user_sessions(db, user.id)

    db.commit()

    logger.info(
        "Admin %s changed user %s status: %s -> %s",
        admin.email, user.email, old_status, data.status,
    )
    return MessageResponse(message=f"User status changed to {data.status}.")


# ---------------------------------------------------------------------------
# POST /api/admin/users/{user_id}/reset-password
# ---------------------------------------------------------------------------
@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
@limiter.limit(RATE_LIMIT_ADMIN)
async def reset_user_password(
    request: Request,
    user_id: UUID,
    data: AdminResetPasswordRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Admin resets a user's password. Sets must_change_password and invalidates sessions."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot reset your own password via admin endpoint.")

    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot reset another admin's password.")

    user.password_hash = hash_password(data.new_password)
    user.must_change_password = True
    user.failed_login_attempts = 0
    user.locked_until = None

    # Invalidate all sessions atomically with password change
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()

    logger.info("Admin %s reset password for user %s", admin.email, user.email)
    return MessageResponse(message="Password reset. User must change password on next login.")


# ---------------------------------------------------------------------------
# GET /api/admin/stats
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=AdminStatsResponse)
@limiter.limit(RATE_LIMIT_ADMIN)
async def get_stats(
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Dashboard statistics — collapsed to 2 queries instead of 6."""
    stats = db.query(
        func.count(User.id).label("total"),
        func.sum(case((User.status == "pending", 1), else_=0)).label("pending"),
        func.sum(case((User.status == "active", 1), else_=0)).label("active"),
        func.sum(case((User.status == "paused", 1), else_=0)).label("paused"),
        func.sum(case((User.status == "declined", 1), else_=0)).label("declined"),
    ).one()

    canvas_total = db.query(func.count(Canvas.id)).scalar()

    return AdminStatsResponse(
        total_users=stats.total or 0,
        pending_users=int(stats.pending or 0),
        active_users=int(stats.active or 0),
        paused_users=int(stats.paused or 0),
        declined_users=int(stats.declined or 0),
        total_canvases=canvas_total or 0,
    )
