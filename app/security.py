"""
Security middleware and utilities.
- Security headers (HSTS, X-Frame-Options, CSP, etc.)
- Structured JSON logging configuration
- Request body size limiting
"""

import logging
import os
import sys
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

IS_PRODUCTION = os.getenv("PYTHON_ENV", "development") == "production"
MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", str(1 * 1024 * 1024)))  # 1 MB


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )

        return response


# ---------------------------------------------------------------------------
# Request Body Size Middleware
# ---------------------------------------------------------------------------
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than MAX_BODY_SIZE."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            return Response(
                content='{"detail":"Request body too large."}',
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
def configure_logging():
    """Set up structured logging for the application."""
    log_level = logging.DEBUG if not IS_PRODUCTION else logging.INFO
    log_format = (
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
        if not IS_PRODUCTION
        else '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Shared Rate Limiter (importable by route modules without circular deps)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
