"""
BYOK (Bring Your Own Key) routes for managing user OpenAI API keys.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..encryption import encrypt_api_key, decrypt_api_key
from ..models import User
from ..schemas import SaveOpenAIKeyRequest, OpenAIKeyStatusResponse, OpenAIKeyTestResponse
from ..security import limiter

logger = logging.getLogger(__name__)

RATE_LIMIT_BYOK = os.getenv("RATE_LIMIT_BYOK", "10/minute")
RATE_LIMIT_BYOK_TEST = os.getenv("RATE_LIMIT_BYOK_TEST", "3/minute")

router = APIRouter(prefix="/api/byok", tags=["byok"])


def _key_hint(api_key: str) -> str:
    """Format a masked key hint showing only the last 4 characters."""
    return f"sk-...{api_key[-4:]}"


@router.get("/status", response_model=OpenAIKeyStatusResponse)
@limiter.limit(RATE_LIMIT_BYOK)
async def get_key_status(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Check if the user has a stored OpenAI API key."""
    if not user.encrypted_openai_key:
        return OpenAIKeyStatusResponse(has_key=False)

    plaintext = decrypt_api_key(user.encrypted_openai_key)
    if plaintext:
        return OpenAIKeyStatusResponse(
            has_key=True, key_hint=_key_hint(plaintext), key_valid=True,
        )
    # Key exists but can't be decrypted (e.g. API_SECRET_KEY rotated)
    return OpenAIKeyStatusResponse(
        has_key=True, key_hint="(unreadable — please re-enter)",
    )


@router.post("/save", response_model=OpenAIKeyStatusResponse)
@limiter.limit(RATE_LIMIT_BYOK)
async def save_key(
    request: Request,
    body: SaveOpenAIKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Encrypt and store the user's OpenAI API key."""
    user.encrypted_openai_key = encrypt_api_key(body.openai_api_key)
    db.commit()
    logger.info("BYOK key saved for user %s", user.email)

    return OpenAIKeyStatusResponse(
        has_key=True, key_hint=_key_hint(body.openai_api_key), key_valid=True,
    )


@router.delete("/delete")
@limiter.limit(RATE_LIMIT_BYOK)
async def delete_key(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove the user's stored OpenAI API key."""
    user.encrypted_openai_key = None
    db.commit()
    logger.info("BYOK key deleted for user %s", user.email)
    return {"message": "API key deleted."}


@router.post("/test", response_model=OpenAIKeyTestResponse)
@limiter.limit(RATE_LIMIT_BYOK_TEST)
async def test_key(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Test the user's stored OpenAI API key by making a lightweight API call."""
    if not user.encrypted_openai_key:
        raise HTTPException(status_code=404, detail="No API key stored.")

    plaintext = decrypt_api_key(user.encrypted_openai_key)
    if not plaintext:
        return OpenAIKeyTestResponse(
            valid=False,
            message="Key cannot be decrypted. Please re-enter your API key.",
        )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=plaintext)
        # Lightweight call: list models (no tokens consumed)
        client.models.list()
        return OpenAIKeyTestResponse(valid=True, message="Key is valid!")
    except ImportError:
        return OpenAIKeyTestResponse(
            valid=False,
            message="OpenAI library not available on server.",
        )
    except Exception as e:
        logger.warning("BYOK key test failed for user %s: %s", user.email, e)
        return OpenAIKeyTestResponse(
            valid=False,
            message="Key is invalid or does not have access.",
        )
