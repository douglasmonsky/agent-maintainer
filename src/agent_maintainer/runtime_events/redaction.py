"""Runtime event redaction helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final, cast

MAX_STRING_VALUE_LENGTH: Final = 500
REDACTED: Final = "[redacted]"
OMITTED_RAW_VALUE: Final = "[omitted-runtime-event-raw-value]"
SENSITIVE_KEY_FRAGMENTS: Final = (
    "api_key",
    "authorization",
    "bearer",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)
RAW_VALUE_KEYS: Final = frozenset(
    (
        "environment",
        "env",
        "file_content",
        "file_contents",
        "prompt",
        "stderr",
        "stdout",
        "traceback",
    ),
)
SECRET_PATTERNS: Final = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{12,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)((?:password|token|secret|api[_-]?key)=)[^\s,;]+"),
)


def sanitize_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Return small JSON-safe attributes with sensitive values redacted."""
    return {str(key): sanitize_value(str(key), value) for key, value in attributes.items()}


def sanitize_value(key: str, value: Any) -> Any:
    """Return JSON-safe event value for one attribute."""
    normalized_key = key.lower()
    if _is_raw_value_key(normalized_key):
        return OMITTED_RAW_VALUE
    if _is_sensitive_key(normalized_key):
        return REDACTED
    if isinstance(value, str):
        return _sanitize_text(value)
    return _sanitize_structured_value(key, value)


def _sanitize_structured_value(key: str, value: Any) -> Any:
    if isinstance(value, bool | int | float) or value is None:
        return value
    if isinstance(value, Mapping):
        raw_mapping = cast(Mapping[object, Any], value)
        return sanitize_attributes(
            {str(inner_key): inner_value for inner_key, inner_value in raw_mapping.items()},
        )
    if _is_sequence(value):
        return [sanitize_value(key, item) for item in value]
    return _sanitize_text(str(value))


def _is_raw_value_key(normalized_key: str) -> bool:
    return normalized_key in RAW_VALUE_KEYS


def _is_sensitive_key(normalized_key: str) -> bool:
    return any(fragment in normalized_key for fragment in SENSITIVE_KEY_FRAGMENTS)


def _sanitize_text(value: str) -> str:
    sanitized = value
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(_redacted_match, sanitized)
    if len(sanitized) > MAX_STRING_VALUE_LENGTH:
        return "".join((sanitized[:MAX_STRING_VALUE_LENGTH], "...[truncated]"))
    return sanitized


def _redacted_match(match: re.Match[str]) -> str:
    if match.lastindex:
        return f"{match.group(1)}{REDACTED}"
    return REDACTED


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray)
