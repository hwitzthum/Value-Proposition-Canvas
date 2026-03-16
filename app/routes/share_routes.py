"""
Shareable read-only canvas link endpoints.

- POST   /api/canvases/{canvas_id}/share        — generate a share link (auth required)
- DELETE  /api/canvases/{canvas_id}/share/{id}   — revoke a share link (auth required)
- GET     /api/shared/{share_token}              — view a shared canvas (public, no auth)
- POST    /api/shared/{share_token}              — view a password-protected shared canvas (public)
"""

import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import Canvas, CanvasShareLink, User
from ..schemas import (
    CreateShareLinkRequest,
    ShareLinkResponse,
    SharePasswordRequest,
    SharedCanvasResponse,
)
from ..security import limiter

logger = logging.getLogger(__name__)

RATE_LIMIT_CANVAS = os.getenv("RATE_LIMIT_CANVAS", "60/minute")
RATE_LIMIT_SHARED = os.getenv("RATE_LIMIT_SHARED", "30/minute")
MAX_SHARE_LINKS_PER_CANVAS = 10

# Pre-computed dummy hash for constant-time responses on invalid tokens.
# This ensures verify_password is always called, preventing timing oracles.
_DUMMY_HASH = hash_password("dummy-constant-time-padding")

router = APIRouter(prefix="/api", tags=["sharing"])


# ---------------------------------------------------------------------------
# POST /api/canvases/{canvas_id}/share
# ---------------------------------------------------------------------------
@router.post(
    "/canvases/{canvas_id}/share",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(RATE_LIMIT_CANVAS)
async def create_share_link(
    request: Request,
    canvas_id: UUID,
    body: CreateShareLinkRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a shareable read-only link for a canvas the user owns."""
    canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
    if canvas is None or canvas.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canvas not found.",
        )

    # Cap active share links per canvas
    active_count = (
        db.query(func.count(CanvasShareLink.id))
        .filter(
            CanvasShareLink.canvas_id == canvas.id,
            CanvasShareLink.is_active == True,
        )
        .scalar()
    )
    if active_count >= MAX_SHARE_LINKS_PER_CANVAS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum of {MAX_SHARE_LINKS_PER_CANVAS} active share links reached. Revoke an existing link first.",
        )

    token = secrets.token_urlsafe(32)

    pw_hash = None
    if body.password:
        pw_hash = hash_password(body.password)

    expires_at = None
    if body.expires_in_hours is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)

    link = CanvasShareLink(
        canvas_id=canvas.id,
        share_token=token,
        password_hash=pw_hash,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    logger.info("Share link created for canvas %s by user %s", canvas_id, user.email)

    return ShareLinkResponse(
        id=link.id,
        share_token=link.share_token,
        has_password=link.password_hash is not None,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


# ---------------------------------------------------------------------------
# DELETE /api/canvases/{canvas_id}/share/{link_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/canvases/{canvas_id}/share/{link_id}",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(RATE_LIMIT_CANVAS)
async def revoke_share_link(
    request: Request,
    canvas_id: UUID,
    link_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate (soft-delete) a share link. Only the canvas owner may do this."""
    canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
    if canvas is None or canvas.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canvas not found.",
        )

    link = (
        db.query(CanvasShareLink)
        .filter(
            CanvasShareLink.id == link_id,
            CanvasShareLink.canvas_id == canvas_id,
        )
        .first()
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found.",
        )

    link.is_active = False
    db.commit()

    logger.info("Share link %s revoked for canvas %s", link_id, canvas_id)
    return {"message": "Share link revoked."}


# ---------------------------------------------------------------------------
# Shared helper — constant-time share link resolution
# ---------------------------------------------------------------------------
def _resolve_share_link(
    share_token: str,
    password: Optional[str],
    db: Session,
) -> Canvas:
    """Look up a share link and return the canvas.

    Always runs verify_password to prevent timing oracles that leak
    whether a token exists or is password-protected.
    """
    link = (
        db.query(CanvasShareLink)
        .filter(CanvasShareLink.share_token == share_token)
        .first()
    )

    # Always perform a password check to normalise response timing.
    # If the link is missing or has no password, check against a dummy hash.
    incoming_pw = password or ""
    reference_hash = (
        link.password_hash
        if (link and link.is_active and link.password_hash)
        else _DUMMY_HASH
    )
    password_ok = verify_password(incoming_pw, reference_hash)

    # Now evaluate the result
    if link is None or not link.is_active:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This share link is no longer active.",
        )

    # Check expiration (SQLite returns naive datetimes — treat as UTC)
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This share link has expired.",
            )

    # Check password if the link is protected
    if link.password_hash is not None:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This shared canvas requires a password.",
            )
        if not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password.",
            )

    canvas = db.query(Canvas).filter(Canvas.id == link.canvas_id).first()
    if canvas is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The shared canvas no longer exists.",
        )

    return canvas


# ---------------------------------------------------------------------------
# GET /api/shared/{share_token}  — public, no password
# ---------------------------------------------------------------------------
@router.get(
    "/shared/{share_token}",
    response_model=SharedCanvasResponse,
)
@limiter.limit(RATE_LIMIT_SHARED)
async def get_shared_canvas(
    request: Request,
    share_token: str,
    db: Session = Depends(get_db),
):
    """View a shared canvas via its token. No authentication required.

    For password-protected links, use POST /api/shared/{share_token} instead.
    """
    canvas = _resolve_share_link(share_token, password=None, db=db)
    return SharedCanvasResponse(
        title=canvas.title,
        job_description=canvas.job_description,
        pain_points=canvas.pain_points or [],
        gain_points=canvas.gain_points or [],
        created_at=canvas.created_at,
    )


# ---------------------------------------------------------------------------
# POST /api/shared/{share_token}  — public, with password in body
# ---------------------------------------------------------------------------
@router.post(
    "/shared/{share_token}",
    response_model=SharedCanvasResponse,
)
@limiter.limit(RATE_LIMIT_SHARED)
async def get_shared_canvas_with_password(
    request: Request,
    share_token: str,
    body: SharePasswordRequest,
    db: Session = Depends(get_db),
):
    """View a password-protected shared canvas. Password is sent in the request body,
    not as a query parameter, to avoid logging in server access logs and browser history."""
    canvas = _resolve_share_link(share_token, password=body.password, db=db)
    return SharedCanvasResponse(
        title=canvas.title,
        job_description=canvas.job_description,
        pain_points=canvas.pain_points or [],
        gain_points=canvas.gain_points or [],
        created_at=canvas.created_at,
    )
