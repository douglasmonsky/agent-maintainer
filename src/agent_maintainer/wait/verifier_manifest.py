"""Verifier manifest parsing for quiet wait commands."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

PASSED = "passed"
SKIPPED = "skipped"
WARNING = "warning"
NON_FAILED_STATUSES = frozenset((PASSED, SKIPPED, WARNING))


def _empty_checks() -> tuple[VerifierCheck, ...]:
    return ()


@dataclass(frozen=True)
class VerifierCheck:
    """One check entry in a verifier manifest."""

    name: str
    status: str
    log_path: str = ""
    expansion_commands: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerifierManifest:
    """Small manifest view needed by the local waiter."""

    run_id: str
    profile: str
    checks: tuple[VerifierCheck, ...] = field(default_factory=_empty_checks)
    duration_seconds: float | None = None
    expected_duration_hint: str = ""
    failure_snapshot: str = ""

    @property
    def failed_checks(self) -> tuple[VerifierCheck, ...]:
        """Return checks that should make the verifier run fail."""
        return tuple(check for check in self.checks if check.status not in NON_FAILED_STATUSES)

    @property
    def succeeded(self) -> bool:
        """Return whether all manifest checks passed or skipped."""
        return not self.failed_checks


def parse_verifier_manifest(path: Path) -> VerifierManifest:
    """Parse the small manifest fields used by wait output."""
    parsed = json.loads(path.read_text(encoding="utf-8"))
    payload = _json_object(parsed)
    if payload is None:
        raise ValueError(f"verifier manifest is not an object: {path}")
    return VerifierManifest(
        run_id=str(payload.get("run_id") or path.parent.name),
        profile=str(payload.get("profile", "")),
        checks=_parse_checks(payload.get("checks", ())),
        duration_seconds=_duration_seconds(payload),
        expected_duration_hint=str(payload.get("expected_duration_hint", "")),
        failure_snapshot=str(payload.get("failure_snapshot", "")),
    )


def _parse_checks(raw_checks: object) -> tuple[VerifierCheck, ...]:
    if not isinstance(raw_checks, Sequence) or isinstance(raw_checks, (str, bytes)):
        return ()
    checks = cast(Sequence[object], raw_checks)
    return tuple(
        _parse_check(check) for value in checks if (check := _json_object(value)) is not None
    )


def _parse_check(check: dict[str, object]) -> VerifierCheck:
    return VerifierCheck(
        name=str(check.get("name", "")),
        status=str(check.get("status", "")),
        log_path=str(check.get("log_path", "")),
        expansion_commands=_string_tuple(check.get("expansion_commands", ())),
    )


def _string_tuple(raw_values: object) -> tuple[str, ...]:
    if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)):
        return ()
    values = cast(Sequence[object], raw_values)
    return tuple(str(value) for value in values)


def _duration_seconds(payload: dict[str, object]) -> float | None:
    timing = _json_object(payload.get("timing"))
    if timing is None:
        return None
    duration = timing.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        return None
    seconds = float(duration)
    return seconds if math.isfinite(seconds) else None


def _json_object(value: object) -> dict[str, object] | None:
    """Return a JSON object with string keys, or ``None`` when malformed."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}
