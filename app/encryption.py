"""
Fernet encryption for BYOK API keys.
Derives an encryption key from API_SECRET_KEY via PBKDF2.
"""

import base64
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_SALT = b"vpc-byok-encryption-salt-v1"
_ITERATIONS = 100_000

# Cache: (secret, Fernet) — avoids re-running 100k PBKDF2 iterations per call
_cached_fernet: tuple[str, Fernet] | None = None


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from a secret string via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))


def _get_fernet() -> Fernet:
    """Get a cached Fernet instance using the current API_SECRET_KEY."""
    global _cached_fernet
    secret = os.getenv("API_SECRET_KEY", "")
    if not secret:
        raise RuntimeError("API_SECRET_KEY is not set; cannot encrypt BYOK keys")
    if _cached_fernet is None or _cached_fernet[0] != secret:
        _cached_fernet = (secret, Fernet(_derive_key(secret)))
    return _cached_fernet[1]


def encrypt_api_key(plaintext_key: str) -> str:
    """Encrypt an API key. Returns a base64-encoded ciphertext string."""
    f = _get_fernet()
    return f.encrypt(plaintext_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str) -> str | None:
    """Decrypt an API key. Returns None if decryption fails (e.g. rotated secret)."""
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, RuntimeError) as e:
        logger.warning("Failed to decrypt BYOK key: %s", type(e).__name__)
        return None
