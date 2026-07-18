"""Fail-closed repository-relative path validation."""

from __future__ import annotations

import re

WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class RepoPathError(ValueError):
    """Raised when repository-relative path text is unsafe or ambiguous."""


def validate_repo_path(value: str, *, label: str) -> str:
    """Return validated POSIX repository-relative path text."""
    reason = _invalid_reason(value)
    if reason is not None:
        raise RepoPathError(f"{label} {reason}")
    return value


def _invalid_reason(value: str) -> str | None:
    parts = value.split("/")
    checks = (
        (not value, "must be non-empty text"),
        ("\0" in value, "must not contain NUL"),
        ("\\" in value, "must use POSIX separators"),
        (
            any((value.startswith("/"), value.startswith("./"), bool(WINDOWS_DRIVE.match(value)))),
            "must be repository-relative",
        ),
        (
            any(part in {"", ".", ".."} for part in parts),
            "contains an unsafe or ambiguous segment",
        ),
    )
    return next((reason for invalid, reason in checks if invalid), None)
