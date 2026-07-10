"""Shared values and primitives for release evidence validation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

PROFILE_MANIFEST_VERSION = 1
RELEASE_EVIDENCE_VERSION = 1
RELEASE_EVIDENCE_KIND = "agent-maintainer-release-evidence"
REQUIRED_PROFILES = ("full", "ci", "security", "manual", "release")
SUCCESS_CHECK_STATUSES = frozenset(("passed", "warning", "skipped-disabled"))
MAX_EVIDENCE_AGE = timedelta(hours=24)
MAX_CLOCK_SKEW = timedelta(minutes=5)
FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
FULL_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
ZERO_SECONDS = 0


class ReleaseEvidenceError(ValueError):
    """Raised when release evidence fails its trust contract."""


@dataclass(frozen=True)
class ValidatedProfile:
    """Trusted fields extracted from one profile manifest."""

    profile: str
    generated_at: datetime


@dataclass(frozen=True)
class CommandProfileRun:
    """Inputs captured around one external profile command."""

    profile: str
    command: tuple[str, ...]
    exit_code: int
    git: Mapping[str, object]
    started_at: datetime
    ended_at: datetime


@dataclass(frozen=True)
class ProfileRecord:
    """One profile manifest paired with its validated identity."""

    manifest: dict[str, object]
    validated: ValidatedProfile


def manifest_sha256(manifest: Mapping[str, object]) -> str:
    """Return the canonical SHA-256 for one embedded profile manifest."""

    encoded = json.dumps(
        dict(manifest),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def required_mapping(value: object, label: str) -> Mapping[str, object]:
    """Return one JSON object or raise a labeled evidence error."""

    if not isinstance(value, dict):
        raise ReleaseEvidenceError(f"{label} must be an object")
    return cast(dict[str, object], value)


def required_text(value: object, label: str) -> str:
    """Return one non-empty string or raise a labeled evidence error."""

    if not isinstance(value, str) or not value:
        raise ReleaseEvidenceError(f"{label} must be a non-empty string")
    return value


def validate_sha(value: str, *, label: str) -> None:
    """Require a full lowercase SHA-1 or SHA-256 Git object identity."""

    if FULL_GIT_SHA.fullmatch(value) is None:
        raise ReleaseEvidenceError(f"{label} must be a full lowercase Git SHA")


def parse_time(value: object, *, label: str) -> datetime:
    """Parse one timezone-aware ISO-8601 timestamp."""

    text = required_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseEvidenceError(f"{label} must be an ISO-8601 timestamp") from exc
    return checked_datetime(parsed, label=label)


def checked_now(value: datetime | None) -> datetime:
    """Return an explicit or current timezone-aware UTC timestamp."""

    return checked_datetime(value or datetime.now(UTC), label="current time")


def checked_datetime(value: datetime, *, label: str) -> datetime:
    """Normalize one timezone-aware timestamp to UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ReleaseEvidenceError(f"{label} must include a timezone")
    return value.astimezone(UTC)


def format_time(value: datetime) -> str:
    """Render one UTC timestamp in stable ISO-8601 form."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
