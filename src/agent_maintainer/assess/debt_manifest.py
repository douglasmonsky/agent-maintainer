"""Verifier manifest evidence used by advisory debt scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

FAILED_CHECK_PENALTY = 16
WARNING_CHECK_PENALTY = 6
MAX_MANIFEST_CATEGORY_PENALTY = 32
MANIFEST_JSON = "manifest.json"

FAILED_STATUSES = frozenset(("failed", "error", "timeout"))
WARNING_STATUSES = frozenset(("warning", "warn", "skipped-required"))


@dataclass(frozen=True)
class ManifestCheck:
    """One verifier check from the latest manifest."""

    name: str
    status: str


@dataclass(frozen=True)
class ManifestSignals:
    """Verifier manifest evidence used to calibrate debt categories."""

    present: bool
    malformed: bool
    checks: tuple[ManifestCheck, ...]


def manifest_signals(log_dir: Path) -> ManifestSignals:
    """Read latest verifier manifest status evidence."""

    path = log_dir / MANIFEST_JSON
    if not path.exists():
        return ManifestSignals(present=False, malformed=False, checks=())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ManifestSignals(present=True, malformed=True, checks=())
    if not isinstance(payload, dict):
        return ManifestSignals(present=True, malformed=True, checks=())
    return ManifestSignals(
        present=True,
        malformed=False,
        checks=manifest_checks(payload.get("checks")),
    )


def manifest_checks(value: object) -> tuple[ManifestCheck, ...]:
    """Return typed checks from raw manifest JSON."""

    if not isinstance(value, list):
        return ()
    checks: list[ManifestCheck] = []
    for entry in value:
        if isinstance(entry, dict):
            checks.extend(_manifest_check(entry))
    return tuple(checks)


def with_manifest_penalty(
    score: int,
    evidence_lines: list[str],
    manifest: ManifestSignals,
    keywords: tuple[str, ...],
) -> int:
    """Return score adjusted by matching failed or warning verifier checks."""

    if manifest.malformed:
        evidence_lines.append("latest verifier manifest is unreadable")
        return min(score + WARNING_CHECK_PENALTY, MAX_MANIFEST_CATEGORY_PENALTY)
    failed = status_names(manifest, keywords, FAILED_STATUSES)
    warnings = status_names(manifest, keywords, WARNING_STATUSES)
    if failed:
        evidence_lines.append(f"manifest failed checks = {csv(failed)}")
    if warnings:
        evidence_lines.append(f"manifest warning checks = {csv(warnings)}")
    penalty = min(
        MAX_MANIFEST_CATEGORY_PENALTY,
        len(failed) * FAILED_CHECK_PENALTY + len(warnings) * WARNING_CHECK_PENALTY,
    )
    return score + penalty


def status_names(
    manifest: ManifestSignals,
    keywords: tuple[str, ...],
    statuses: frozenset[str],
) -> tuple[str, ...]:
    """Return manifest check names matching category keywords and statuses."""

    return tuple(
        check.name
        for check in manifest.checks
        if check.status.lower() in statuses and matches_keywords(check.name, keywords)
    )


def matches_keywords(name: str, keywords: tuple[str, ...]) -> bool:
    """Return whether a check name belongs to a category keyword set."""

    normalized = name.lower()
    return any(keyword in normalized for keyword in keywords)


def csv(values: tuple[str, ...]) -> str:
    """Return comma-separated values or a placeholder."""

    return ", ".join(values) if values else "none"


def _manifest_check(entry: dict[object, object]) -> tuple[ManifestCheck, ...]:
    """Return one manifest check when fields are valid."""

    name = entry.get("name")
    status = entry.get("status")
    if isinstance(name, str) and isinstance(status, str):
        return (ManifestCheck(name=name, status=status),)
    return ()
