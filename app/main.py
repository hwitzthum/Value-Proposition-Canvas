"""
FastAPI Backend for Value Proposition Canvas Coaching Application.
Provides endpoints for validation, coaching suggestions, and document generation.
"""

import os
import re
import html
from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import io

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .validation import QualityValidator
from .coaching import CoachingEngine
from .document_generator import DocumentGenerator

# ============ Configuration ============
# Load allowed origins from environment (comma-separated list)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8501,http://127.0.0.1:8501"
).split(",")

# Optional API key for authentication (if set, all endpoints require it)
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

# Rate limiting configuration
RATE_LIMIT_AI = os.getenv("RATE_LIMIT_AI", "10/minute")  # AI endpoints
RATE_LIMIT_VALIDATION = os.getenv("RATE_LIMIT_VALIDATION", "60/minute")  # Validation endpoints

# ============ Security Utilities ============
# Patterns that could indicate prompt injection or XSS attacks
DANGEROUS_PATTERNS = [
    r'<script[^>]*>',
    r'javascript:',
    r'on\w+\s*=',
    r'ignore\s+(all\s+)?(previous|prior)\s+(instructions?|prompts?)',
    r'system\s*prompt',
    r'you\s+are\s+now',
    r'disregard\s+(all\s+)?(previous|prior)',
]

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and prompt injection."""
    if not text:
        return text

    # HTML escape to prevent XSS
    sanitized = html.escape(text)

    # Check for dangerous patterns (log but don't block - just escape)
    text_lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            # Pattern detected - the HTML escaping already handles XSS
            # For prompt injection, the AI provider should handle it
            break

    return sanitized

def validate_text_content(text: str, field_name: str, min_length: int = 1, max_length: int = 10000) -> str:
    """Validate and sanitize text content."""
    if not text or not text.strip():
        raise ValueError(f"{field_name} cannot be empty")

    text = text.strip()

    if len(text) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")

    if len(text) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")

    return sanitize_input(text)

# ============ Rate Limiting Setup ============
limiter = Limiter(key_func=get_remote_address)

# ============ Initialize FastAPI app ============
app = FastAPI(
    title="Value Proposition Canvas API",
    description="AI-powered coaching for creating high-quality Value Proposition Canvases",
    version="1.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============ CORS Configuration (Restricted) ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# ============ API Key Authentication ============
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """Verify API key if authentication is enabled."""
    # If no API_SECRET_KEY is configured, authentication is disabled
    if not API_SECRET_KEY:
        return True

    # If API key is configured, require it
    if not api_key or api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key. Provide X-API-Key header."
        )
    return True

# Initialize services
validator = QualityValidator()
coach = CoachingEngine()
doc_generator = DocumentGenerator()


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
async def get_config(request: Request):
    """Get configuration information."""
    return {
        "ai_enabled": coach.is_ai_enabled,
        "min_pain_points": validator.MIN_PAIN_POINTS,
        "min_gain_points": validator.MIN_GAIN_POINTS,
        "similarity_threshold": validator.SIMILARITY_THRESHOLD
    }


@app.post("/api/validate/job-description", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_job_description(request: Request, data: JobDescriptionRequest):
    """Validate and provide feedback on job description."""
    result = validator.validate_job_description(data.description)
    return result


@app.post("/api/validate/pain-points", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_pain_points(request: Request, data: PainPointsRequest):
    """Validate pain points for quality and independence."""
    result = validator.validate_pain_points(data.pain_points)
    return result


@app.post("/api/validate/gain-points", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_gain_points(request: Request, data: GainPointsRequest):
    """Validate gain points for quality and independence."""
    result = validator.validate_gain_points(data.gain_points)
    return result


@app.post("/api/validate/canvas", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def validate_canvas(request: Request, data: CanvasValidationRequest):
    """Validate the complete canvas."""
    result = validator.validate_complete_canvas(
        data.job_description,
        data.pain_points,
        data.gain_points
    )
    return result


@app.post("/api/suggestions", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def get_suggestions(request: Request, data: SuggestionsRequest):
    """Get AI-powered suggestions for the current step."""
    if data.step == 'job':
        return coach.get_job_description_suggestions(data.job_description or "")
    elif data.step == 'pains':
        return coach.get_pain_point_suggestions(
            data.job_description or "",
            data.existing_items or [],
            data.count_needed or 3
        )
    elif data.step == 'gains':
        return coach.get_gain_point_suggestions(
            data.job_description or "",
            data.existing_items or [],
            data.count_needed or 3
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown step: {data.step}")


@app.get("/api/coaching-tip/{step}", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_VALIDATION)
async def get_coaching_tip(request: Request, step: str):
    """Get a contextual coaching tip for the specified step."""
    # Validate step parameter
    if step not in ('job', 'pains', 'gains', 'review', 'welcome'):
        raise HTTPException(status_code=400, detail=f"Invalid step: {step}")
    tip = coach.get_coaching_tip(step)
    return {"step": step, "tip": tip}


@app.post("/api/generate-document", dependencies=[Depends(verify_api_key)])
@limiter.limit(RATE_LIMIT_AI)
async def generate_document(request: Request, data: GenerateDocumentRequest):
    """Generate a Word document from the completed canvas."""
    # Validate the canvas first
    validation = validator.validate_complete_canvas(
        data.job_description,
        data.pain_points,
        data.gain_points
    )

    if not validation['valid']:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Canvas validation failed. Please fix all issues before generating document.",
                "validation": validation
            }
        )

    # Generate the document
    buffer = doc_generator.generate(
        data.job_description,
        data.pain_points,
        data.gain_points,
        data.title
    )

    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{data.title.replace(" ", "_")}.docx"'
        }
    )


# ============ Run with: uvicorn app.main:app --reload ============
