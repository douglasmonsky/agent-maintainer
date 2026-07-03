"""Deterministic redaction helpers for untrusted context text."""

from __future__ import annotations

import re

AUTHORIZATION_HEADER_RE = re.compile(r"(?im)^(authorization\s*:\s*)(?:bearer|basic|token)\s+\S+")
DOTENV_SECRET_RE = re.compile(
    r"(?im)^([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY)[A-Z0-9_]*\s*=\s*).+$"
)
PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?"
    r"-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
API_KEY_LIKE_RE = re.compile(r"(?<![A-Za-z0-9_-])(?:sk|sk-proj)-[A-Za-z0-9_-]{16,}")


def sanitize_text(text: str) -> str:
    """Redact common secret shapes from repository or tool output."""

    sanitized = PRIVATE_KEY_BLOCK_RE.sub("[REDACTED PRIVATE KEY]", text)
    sanitized = AUTHORIZATION_HEADER_RE.sub(r"\1[REDACTED]", sanitized)
    sanitized = DOTENV_SECRET_RE.sub(r"\1[REDACTED]", sanitized)
    return API_KEY_LIKE_RE.sub("[REDACTED API KEY]", sanitized)
