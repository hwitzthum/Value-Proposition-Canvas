"""
FastAPI Backend for Value Proposition Canvas Coaching Application.
Provides endpoints for validation, coaching suggestions, and document generation.
"""

import io
import logging
import os
import secrets

from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .validation import QualityValidator
from .coaching import CoachingEngine
from .document_generator import DocumentGenerator
from .pdf_generator import CanvasPDFGenerator
from .sanitization import sanitize_input, sanitize_filename
from .schemas import PASSWORD_MIN_LENGTH, PASSWORD_RULES
from .security import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    configure_logging,
    limiter,
)
from .auth import get_optional_user
from .encryption import decrypt_api_key
from .models import User
from .routes.auth_routes import router as auth_router
from .routes.canvas_routes import router as canvas_router
from .routes.admin_routes import router as admin_router
from .routes.share_routes import router as share_router
from .routes.byok_routes import router as byok_router

# Configure structured logging before anything else
configure_logging()
logger = logging.getLogger(__name__)

# ============ Configuration ============
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8501,http://127.0.0.1:8501"
).split(",")

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

IS_PRODUCTION = os.getenv("PYTHON_ENV", "development") == "production"

# Rate limiting configuration
RATE_LIMIT_AI = os.getenv("RATE_LIMIT_AI", "10/minute")
RATE_LIMIT_VALIDATION = os.getenv("RATE_LIMIT_VALIDATION", "60/minute")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")

# ============ Initialize FastAPI app ============
app = FastAPI(
    title="Value Proposition Canvas API",
    description="AI-powered coaching for creating high-quality Value Proposition Canvases",
    version="1.0.0",
    # Disable Swagger/ReDoc in production
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============ Middleware (order matters: last added = first executed) ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)


# ============ Custom Error Handlers ============
@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Don't leak Pydantic validation details in production."""
    if IS_PRODUCTION:
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request data."},
        )
    # In development, return the full error
    from fastapi.exceptions import RequestValidationError
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )
    return JSONResponse(status_code=422, content={"detail": "Validation error."})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Never leak stack traces in production."""
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


# ============ API Key Authentication (timing-safe) ============
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """Verify API key using timing-safe comparison."""
    if not API_SECRET_KEY:
        return True
    if not api_key or not secrets.compare_digest(api_key, API_SECRET_KEY):
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key."
        )
    return True


# Initialize services
validator = QualityValidator()
coach = CoachingEngine()
doc_generator = DocumentGenerator()
pdf_generator = CanvasPDFGenerator()

# ============ Include Routers ============
app.include_router(auth_router)
app.include_router(canvas_router)
app.include_router(admin_router)
app.include_router(share_router)
app.include_router(byok_router)


# ============ BYOK helpers ============


def _resolve_openai_client(user: Optional[User]) -> Optional[object]:
    """Resolve an OpenAI client from the user's BYOK key, if available."""
    if user is None or not user.encrypted_openai_key:
        return None
    plaintext = decrypt_api_key(user.encrypted_openai_key)
    if not plaintext:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=plaintext)
    except Exception:
        return None


# ============ Request/Response Models ============

class JobDescriptionRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=5000)

    @field_validator('description')
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        return sanitize_input(v.strip())


class PainPointsRequest(BaseModel):
    pain_points: List[str] = Field(..., max_length=50)
    job_description: Optional[str] = Field(default="", max_length=5000)

    @field_validator('pain_points')
    @classmethod
    def sanitize_pain_points(cls, v: List[str]) -> List[str]:
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 pain points")
        return [sanitize_input(p.strip()) for p in v if p.strip()]

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: Optional[str]) -> str:
        return sanitize_input(v.strip()) if v else ""


class GainPointsRequest(BaseModel):
    gain_points: List[str] = Field(..., max_length=50)
    job_description: Optional[str] = Field(default="", max_length=5000)

    @field_validator('gain_points')
    @classmethod
    def sanitize_gain_points(cls, v: List[str]) -> List[str]:
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 gain points")
        return [sanitize_input(g.strip()) for g in v if g.strip()]

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: Optional[str]) -> str:
        return sanitize_input(v.strip()) if v else ""


class SuggestionsRequest(BaseModel):
    step: str = Field(..., pattern=r'^(job|pains|gains)$')
    job_description: Optional[str] = Field(default="", max_length=5000)
    existing_items: Optional[List[str]] = Field(default_factory=list, max_length=50)
    count_needed: Optional[int] = Field(default=3, ge=1, le=10)

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: Optional[str]) -> str:
        return sanitize_input(v.strip()) if v else ""

    @field_validator('existing_items')
    @classmethod
    def sanitize_items(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        return [sanitize_input(item.strip()) for item in v if item.strip()]


class JobSuggestionsRequest(BaseModel):
    current_description: str = Field(default="", max_length=5000)
    count: int = Field(default=3, ge=1, le=5)

    @field_validator('current_description')
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        return sanitize_input(v.strip()) if v else ""


class GenerateDocumentRequest(BaseModel):
    job_description: str = Field(..., min_length=1, max_length=5000)
    pain_points: List[str] = Field(..., min_length=1, max_length=50)
    gain_points: List[str] = Field(..., min_length=1, max_length=50)
    title: Optional[str] = Field(default="Value Proposition Canvas", max_length=200)

    @field_validator('job_description', 'title')
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return sanitize_input(v.strip()) if v else ""

    @field_validator('pain_points', 'gain_points')
    @classmethod
    def sanitize_points(cls, v: List[str]) -> List[str]:
        return [sanitize_input(p.strip()) for p in v if p.strip()]


class CanvasValidationRequest(BaseModel):
    job_description: str = Field(..., min_length=1, max_length=5000)
    pain_points: List[str] = Field(..., max_length=50)
    gain_points: List[str] = Field(..., max_length=50)

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: str) -> str:
        return sanitize_input(v.strip())

    @field_validator('pain_points', 'gain_points')
    @classmethod
    def sanitize_points(cls, v: List[str]) -> List[str]:
        return [sanitize_input(p.strip()) for p in v if p.strip()]


class ImproveItemRequest(BaseModel):
    item: str = Field(..., min_length=1, max_length=2000)
    item_type: str = Field(..., pattern=r'^(pain|gain)$')
    job_description: Optional[str] = Field(default="", max_length=5000)
    context_items: Optional[List[str]] = Field(default_factory=list, max_length=20)

    @field_validator('item')
    @classmethod
    def sanitize_item(cls, v: str) -> str:
        return sanitize_input(v.strip())

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: Optional[str]) -> str:
        return sanitize_input(v.strip()) if v else ""

    @field_validator('context_items')
    @classmethod
    def sanitize_context(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        return [sanitize_input(item.strip()) for item in v if item.strip()]


class MergeItemsRequest(BaseModel):
    item1: str = Field(..., min_length=1, max_length=2000)
    item2: str = Field(..., min_length=1, max_length=2000)
    item_type: str = Field(..., pattern=r'^(pain|gain)$')
    job_description: Optional[str] = Field(default="", max_length=5000)

    @field_validator('item1', 'item2')
    @classmethod
    def sanitize_items(cls, v: str) -> str:
        return sanitize_input(v.strip())

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: Optional[str]) -> str:
        return sanitize_input(v.strip()) if v else ""


class RelevanceCheckRequest(BaseModel):
    items: List[str] = Field(..., min_length=1, max_length=50)
    job_description: str = Field(..., min_length=1, max_length=5000)
    item_type: str = Field(..., pattern=r'^(pain|gain)$')

    @field_validator('items')
    @classmethod
    def sanitize_items(cls, v: List[str]) -> List[str]:
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 items")
        return [sanitize_input(item.strip()) for item in v if item.strip()]

    @field_validator('job_description')
    @classmethod
    def sanitize_job_desc(cls, v: str) -> str:
        return sanitize_input(v.strip())


# ============ API Endpoints ============

@app.get("/")
async def root():
    """Health check endpoint (no auth required)."""
    return {
        "status": "healthy",
        "service": "Value Proposition Canvas API"
    }


@app.get("/api/config", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def get_config(
    request: Request,
    user: Optional[User] = Depends(get_optional_user),
):
    """Get configuration information."""
    # Determine AI source without instantiating an OpenAI client
    has_user_key = (
        user is not None
        and user.encrypted_openai_key
        and decrypt_api_key(user.encrypted_openai_key) is not None
    )
    if has_user_key:
        ai_source = "user_key"
    elif coach.is_ai_enabled:
        ai_source = "server_key"
    else:
        ai_source = "none"

    return {
        "ai_enabled": coach.is_ai_enabled or has_user_key,
        "ai_source": ai_source,
        "min_pain_points": validator.MIN_PAIN_POINTS,
        "min_gain_points": validator.MIN_GAIN_POINTS,
        "similarity_threshold": validator.SIMILARITY_THRESHOLD,
        "password_min_length": PASSWORD_MIN_LENGTH,
        "password_rules_text": PASSWORD_RULES,
    }


@app.post("/api/validate/job-description", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_job_description(request: Request, data: JobDescriptionRequest):
    """Validate and provide feedback on job description."""
    return validator.validate_job_description(data.description)


@app.post("/api/validate/pain-points", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_pain_points(request: Request, data: PainPointsRequest):
    """Validate pain points for quality and independence."""
    result = validator.validate_pain_points(data.pain_points)
    result['priority_level'] = validator.compute_priority_level(result)
    result['positive_feedback'] = validator.compute_positive_feedback(result, "pain point")
    return result


@app.post("/api/validate/gain-points", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_gain_points(request: Request, data: GainPointsRequest):
    """Validate gain points for quality and independence."""
    result = validator.validate_gain_points(data.gain_points)
    result['priority_level'] = validator.compute_priority_level(result)
    result['positive_feedback'] = validator.compute_positive_feedback(result, "gain point")
    return result


@app.post("/api/validate/canvas", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_canvas(request: Request, data: CanvasValidationRequest):
    """Validate the complete canvas and return proactive nudges."""
    result = validator.validate_complete_canvas(
        data.job_description,
        data.pain_points,
        data.gain_points
    )
    result['nudges'] = validator.compute_nudges(
        data.job_description,
        data.pain_points,
        data.gain_points,
    )
    return result


@app.post("/api/suggestions", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def get_suggestions(
    request: Request,
    data: SuggestionsRequest,
    user: Optional[User] = Depends(get_optional_user),
):
    """Get AI-powered suggestions for the current step."""
    oc = _resolve_openai_client(user)
    if data.step == 'job':
        return coach.get_job_description_suggestions(
            data.job_description or "", openai_client=oc)
    elif data.step == 'pains':
        return coach.get_pain_point_suggestions(
            data.job_description or "",
            data.existing_items or [],
            data.count_needed or 3,
            openai_client=oc,
        )
    elif data.step == 'gains':
        return coach.get_gain_point_suggestions(
            data.job_description or "",
            data.existing_items or [],
            data.count_needed or 3,
            openai_client=oc,
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown step.")


@app.post("/api/suggestions/job-statement", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def get_job_statement_suggestions(
    request: Request,
    data: JobSuggestionsRequest,
    user: Optional[User] = Depends(get_optional_user),
):
    """Get concrete, clickable job statement alternatives."""
    return coach.get_job_statement_suggestions(
        current_description=data.current_description,
        count=data.count,
        openai_client=_resolve_openai_client(user),
    )


@app.get("/api/coaching-tip/{step}", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def get_coaching_tip(request: Request, step: str):
    """Get a contextual coaching tip for the specified step."""
    if step not in ('job', 'pains', 'gains', 'review', 'welcome'):
        raise HTTPException(status_code=400, detail="Invalid step.")
    tip = coach.get_coaching_tip(step)
    return {"step": step, "tip": tip}


@app.post("/api/improve-item", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def improve_item(
    request: Request,
    data: ImproveItemRequest,
    user: Optional[User] = Depends(get_optional_user),
):
    """Improve a single pain/gain point using AI coaching."""
    return coach.improve_item(
        item=data.item,
        item_type=data.item_type,
        job_description=data.job_description or "",
        context_items=data.context_items or [],
        openai_client=_resolve_openai_client(user),
    )


@app.post("/api/merge-items", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def merge_items(
    request: Request,
    data: MergeItemsRequest,
    user: Optional[User] = Depends(get_optional_user),
):
    """Merge two similar items into one stronger item."""
    return coach.merge_items(
        item1=data.item1,
        item2=data.item2,
        item_type=data.item_type,
        job_description=data.job_description or "",
        openai_client=_resolve_openai_client(user),
    )


@app.post("/api/validate/relevance", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def check_relevance(request: Request, data: RelevanceCheckRequest):
    """Check if items are relevant to the job description."""
    return validator.check_relevance(
        items=data.items,
        job_description=data.job_description,
    )


@app.post("/api/generate-document", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def generate_document(request: Request, data: GenerateDocumentRequest):
    """Generate a Word document from the completed canvas."""
    validation = validator.validate_complete_canvas(
        data.job_description,
        data.pain_points,
        data.gain_points
    )

    if not validation['valid']:
        raise HTTPException(
            status_code=400,
            detail="Canvas validation failed. Please fix all issues before generating."
        )

    buffer = doc_generator.generate(
        data.job_description,
        data.pain_points,
        data.gain_points,
        data.title
    )

    # Sanitize filename to prevent Content-Disposition header injection
    safe_filename = sanitize_filename(data.title or "canvas")

    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}.docx"'
        }
    )


@app.post("/api/generate-pdf", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def generate_pdf(request: Request, data: GenerateDocumentRequest):
    """Generate a PDF document from the completed canvas."""
    validation = validator.validate_complete_canvas(
        data.job_description,
        data.pain_points,
        data.gain_points
    )

    if not validation['valid']:
        raise HTTPException(
            status_code=400,
            detail="Canvas validation failed. Please fix all issues before generating."
        )

    buffer = pdf_generator.generate(
        data.job_description,
        data.pain_points,
        data.gain_points,
        data.title
    )

    safe_filename = sanitize_filename(data.title or "canvas")

    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}.pdf"'
        }
    )


@app.post("/api/generate-csv", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def generate_csv(request: Request, data: GenerateDocumentRequest):
    """Generate a CSV export of the canvas data."""
    import csv

    validation = validator.validate_complete_canvas(
        data.job_description,
        data.pain_points,
        data.gain_points
    )

    if not validation['valid']:
        raise HTTPException(
            status_code=400,
            detail="Canvas validation failed. Please fix all issues before generating."
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "item_number", "content"])
    writer.writerow(["job_description", 1, data.job_description])
    for i, pain in enumerate(data.pain_points, 1):
        writer.writerow(["pain_point", i, pain])
    for i, gain in enumerate(data.gain_points, 1):
        writer.writerow(["gain_point", i, gain])

    safe_filename = sanitize_filename(data.title or "canvas")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}.csv"'
        }
    )
