"""Channel-agnostic compliance filter.

Extracted from the legacy ``processors/wechat.py:AISCore.safety_filter`` so
all Publishers can share the same safety net regardless of delivery target.
Patterns target crypto-pump and obvious shilling phrases that we never want
to forward to subscribers.

Drop semantics: returning ``None`` means the caller MUST silently drop the
content (do not surface a sanitized version). Keep this conservative — easier
to lose one signal than to lose an account.
"""

from __future__ import annotations

import re
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


# Pump-and-dump and shill patterns. ``token`` itself is intentionally allowed
# (legitimate technical contexts use it).
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    r"buy \$?\w+",
    r"pump and dump",
    r"100x gem",
    r"moon soon",
    r"airdrop alert",
    r"presale",
    r"initial coin offering",
)


def safety_filter(text: str) -> Optional[str]:
    """Return ``text`` if it passes all filters, else ``None`` to drop.

    The function is intentionally non-mutating: callers either get the exact
    input back or get ``None``. Sanitization would mask compliance issues.
    """
    if not text:
        return None
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Safety filter triggered for pattern: {pattern}")
            return None
    return text
