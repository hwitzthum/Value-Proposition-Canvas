"""
Shared sanitization utilities.
Extracted from main.py so schemas.py and other modules can import without
circular dependencies.
"""

import html
import logging
import re

logger = logging.getLogger(__name__)

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
    """Sanitize user input to prevent XSS and prompt injection.

    Strips null bytes before pattern matching to prevent bypass via
    embedded NUL characters (e.g. ``<scr\\x00ipt>``).
    """
    if not text:
        return text

    # Strip null bytes to prevent bypass
    text = text.replace("\x00", "")

    text_lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning("Dangerous input pattern detected and blocked")
            raise ValueError("Input contains disallowed content.")
    return html.escape(text)


def sanitize_filename(name: str) -> str:
    """Sanitize a filename to prevent Content-Disposition header injection.

    Uses ASCII-only allowlist — ``\\w`` would let Unicode through.
    """
    # Only allow ASCII alphanumeric, space, hyphen, underscore
    safe = re.sub(r'[^a-zA-Z0-9_\s\-]', '', name)
    safe = safe.replace(' ', '_')
    return safe[:100] if safe else "document"
