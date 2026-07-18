"""Fail-closed repository-relative path validation."""

from __future__ import annotations

import re

WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class RepoPathError(ValueError):
    """Raised when repository-relative path text is unsafe or ambiguous."""


def validate_repo_path(value: str, *, label: str) -> str:
    """Return validated POSIX repository-relative path text."""
    if not isinstance(value, str) or not value:
        raise RepoPathError(f"{label} must be non-empty text")
    if "\0" in value:
        raise RepoPathError(f"{label} must not contain NUL")
    if "\\" in value:
        raise RepoPathError(f"{label} must use POSIX separators")
    if value.startswith("/") or value.startswith("./") or WINDOWS_DRIVE.match(value):
        raise RepoPathError(f"{label} must be repository-relative")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RepoPathError(f"{label} contains an unsafe or ambiguous segment")
    return value
