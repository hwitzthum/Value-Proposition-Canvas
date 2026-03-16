"""
Security middleware and utilities.
- Security headers (HSTS, X-Frame-Options, CSP, etc.)
- Structured JSON logging configuration
- Request body size limiting (with chunked-encoding protection)
- Rate limiter with spoofing-resistant IP extraction
"""

import logging
import os
import sys
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from slowapi import Limiter

logger = logging.getLogger(__name__)

IS_PRODUCTION = os.getenv("PYTHON_ENV", "development") == "production"
MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", str(1 * 1024 * 1024)))  # 1 MB


# ---------------------------------------------------------------------------
# Spoofing-resistant IP extraction
# ---------------------------------------------------------------------------
def get_real_ip(request: Request) -> str:
    """Extract the client IP for rate limiting.

    Only trusts X-Forwarded-For in production (behind a reverse proxy).
    In development, always uses the direct connection IP to prevent
    attackers from spoofing arbitrary IPs via the header.
    """
    if IS_PRODUCTION:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            # First entry is the client IP set by the trusted proxy
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


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
_BODY_METHODS = {"POST", "PUT", "PATCH"}
_TOO_LARGE = Response(
    content='{"detail":"Request body too large."}',
    status_code=413,
    media_type="application/json",
)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than MAX_BODY_SIZE.

    Checks Content-Length header when present, and for methods that carry
    a body also reads the actual body when Content-Length is missing
    (e.g. chunked transfer encoding) to prevent bypass.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                if int(content_length) > MAX_BODY_SIZE:
                    return _TOO_LARGE
            except (ValueError, OverflowError):
                # Malformed Content-Length
                return Response(
                    content='{"detail":"Invalid Content-Length header."}',
                    status_code=400,
                    media_type="application/json",
                )
        elif request.method in _BODY_METHODS:
            # No Content-Length — read body to enforce limit
            body = await request.body()
            if len(body) > MAX_BODY_SIZE:
                return _TOO_LARGE

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
limiter = Limiter(key_func=get_real_ip)
