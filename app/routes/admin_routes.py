"""
Admin endpoints – user management and dashboard stats.
Requires admin authentication.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import Canvas, User
from ..schemas import (
    AdminStatsResponse,
    AdminUserDetail,
    AdminUserListItem,
    MessageResponse,
    StatusUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[AdminUserListItem])
async def list_users(
    status_filter: Optional[str] = Query(None, alias="status", pattern=r"^(pending|active|paused|declined)$"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all users, optionally filtered by status."""
    query = db.query(User)
    if status_filter:
        query = query.filter(User.status == status_filter)
    query = query.order_by(User.created_at.desc())

    users = query.all()

    # Attach canvas counts
    result = []
    for u in users:
        canvas_count = db.query(func.count(Canvas.id)).filter(Canvas.user_id == u.id).scalar()
        item = AdminUserListItem(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            status=u.status,
            is_admin=u.is_admin,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
            canvas_count=canvas_count or 0,
        )
        result.append(item)

    return result


# ---------------------------------------------------------------------------
# GET /api/admin/users/{user_id}
# ---------------------------------------------------------------------------
@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
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
    )


# ---------------------------------------------------------------------------
# PATCH /api/admin/users/{user_id}/status
# ---------------------------------------------------------------------------
@router.patch("/users/{user_id}/status", response_model=MessageResponse)
async def update_user_status(
    user_id: UUID,
    data: StatusUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Approve, pause, or decline a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status.")

    old_status = user.status
    user.status = data.status

    if data.status == "active" and old_status == "pending":
        user.approved_by = admin.id
        user.approved_at = datetime.now(timezone.utc)

    # Reset lockout when approving
    if data.status == "active":
        user.failed_login_attempts = 0
        user.locked_until = None

    db.commit()

    logger.info(
        "Admin %s changed user %s status: %s -> %s",
        admin.email, user.email, old_status, data.status,
    )
    return MessageResponse(message=f"User status changed to {data.status}.")


# ---------------------------------------------------------------------------
# GET /api/admin/stats
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Dashboard statistics."""
    total = db.query(func.count(User.id)).scalar()
    pending = db.query(func.count(User.id)).filter(User.status == "pending").scalar()
    active = db.query(func.count(User.id)).filter(User.status == "active").scalar()
    paused = db.query(func.count(User.id)).filter(User.status == "paused").scalar()
    declined = db.query(func.count(User.id)).filter(User.status == "declined").scalar()
    canvases = db.query(func.count(Canvas.id)).scalar()

    return AdminStatsResponse(
        total_users=total or 0,
        pending_users=pending or 0,
        active_users=active or 0,
        paused_users=paused or 0,
        declined_users=declined or 0,
        total_canvases=canvases or 0,
    )
