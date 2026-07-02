"""Content fingerprint helpers for DocSync."""

from __future__ import annotations

import hashlib


def sha256_text(text: str) -> str:
    """Return a stable SHA-256 fingerprint for text content."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
