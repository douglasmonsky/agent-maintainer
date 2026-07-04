"""Typed models for repair-fact coverage assessment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairFactCheckCoverage:
    """Repair-fact coverage for one failed check."""

    check: str
    structured_facts: int
    fallback_facts: int
    log_bytes: int
    artifact_paths: tuple[str, ...]
    expansion_commands: tuple[str, ...]


@dataclass(frozen=True)
class RepairFactParserTarget:
    """Ranked parser improvement target."""

    check: str
    fallback_failures: int
    total_log_bytes: int
    priority: int
    artifact_paths: tuple[str, ...]
    recommendation: str


@dataclass(frozen=True)
class RepairFactCoverageReport:
    """Structured repair-fact coverage assessment."""

    target: str
    log_dir: str
    manifest_path: str | None
    run_id: str | None
    profile: str | None
    status: str
    failed_checks: int
    structured_checks: int
    fallback_checks: int
    coverage_percent: float
    checks: tuple[RepairFactCheckCoverage, ...]
    parser_targets: tuple[RepairFactParserTarget, ...]
    next_commands: tuple[str, ...]
