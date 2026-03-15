"""
Canvas CRUD endpoints – authenticated, per-user data isolation.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Canvas, User
from ..schemas import CanvasListResponse, CanvasResponse, CanvasSaveRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/canvases", tags=["canvases"])


def _get_or_create_current(db: Session, user: User) -> Canvas:
    """Return the user's current canvas, creating one if none exists."""
    canvas = (
        db.query(Canvas)
        .filter(Canvas.user_id == user.id, Canvas.is_current == True)
        .first()
    )
    if canvas is None:
        canvas = Canvas(user_id=user.id, is_current=True)
        db.add(canvas)
        db.commit()
        db.refresh(canvas)
        logger.info("Created new canvas for user %s", user.email)
    return canvas


# ---------------------------------------------------------------------------
# GET /api/canvases/current
# ---------------------------------------------------------------------------
@router.get("/current", response_model=CanvasResponse)
async def get_current_canvas(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the user's current active canvas (creates one if needed)."""
    canvas = _get_or_create_current(db, user)
    return CanvasResponse.model_validate(canvas)


# ---------------------------------------------------------------------------
# PUT /api/canvases/current
# ---------------------------------------------------------------------------
@router.put("/current", response_model=CanvasResponse)
async def save_current_canvas(
    data: CanvasSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save/update the user's current canvas."""
    canvas = _get_or_create_current(db, user)

    # Apply only provided fields
    if data.title is not None:
        canvas.title = data.title
    if data.job_description is not None:
        canvas.job_description = data.job_description
    if data.pain_points is not None:
        canvas.pain_points = data.pain_points
    if data.gain_points is not None:
        canvas.gain_points = data.gain_points
    if data.wizard_step is not None:
        canvas.wizard_step = data.wizard_step
    if data.job_validated is not None:
        canvas.job_validated = data.job_validated
    if data.pains_validated is not None:
        canvas.pains_validated = data.pains_validated
    if data.gains_validated is not None:
        canvas.gains_validated = data.gains_validated

    db.commit()
    db.refresh(canvas)
    return CanvasResponse.model_validate(canvas)


# ---------------------------------------------------------------------------
# POST /api/canvases/
# ---------------------------------------------------------------------------
@router.post("/", response_model=CanvasResponse, status_code=status.HTTP_201_CREATED)
async def create_canvas(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new canvas and make it the current one."""
    # Un-current all existing
    db.query(Canvas).filter(
        Canvas.user_id == user.id, Canvas.is_current == True
    ).update({"is_current": False})

    canvas = Canvas(user_id=user.id, is_current=True)
    db.add(canvas)
    db.commit()
    db.refresh(canvas)
    return CanvasResponse.model_validate(canvas)


# ---------------------------------------------------------------------------
# GET /api/canvases/
# ---------------------------------------------------------------------------
@router.get("/", response_model=CanvasListResponse)
async def list_canvases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all canvases for the current user."""
    canvases = (
        db.query(Canvas)
        .filter(Canvas.user_id == user.id)
        .order_by(Canvas.updated_at.desc())
        .all()
    )
    return CanvasListResponse(
        canvases=[CanvasResponse.model_validate(c) for c in canvases]
    )


# ---------------------------------------------------------------------------
# DELETE /api/canvases/{canvas_id}
# ---------------------------------------------------------------------------
@router.delete("/{canvas_id}", response_model=dict)
async def delete_canvas(
    canvas_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a canvas (ownership-checked)."""
    canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
    if canvas is None or canvas.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canvas not found.",
        )

    db.delete(canvas)
    db.commit()
    return {"message": "Canvas deleted."}
