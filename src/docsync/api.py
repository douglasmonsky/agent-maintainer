"""Stable public API for DocSync."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docsync.attestations.create import create_attestation_file
from docsync.checks.doctor import run_doctor
from docsync.checks.repo import run_check
from docsync.core.models import CheckResult, IndexResult
from docsync.indexer import build_docsync_index
from docsync.reports.review_packet import review_packet_for_result


@dataclass(frozen=True)
class CheckOptions:
    """Options for DocSync repository checks."""

    repo_root: Path
    base_ref: str = "origin/main"
    config_path: Path | None = None
    trace_path: Path | None = None


@dataclass(frozen=True)
class IndexOptions:
    """Options for resolving a DocSync index."""

    repo_root: Path
    config_path: Path | None = None
    trace_path: Path | None = None


def build_index(options: IndexOptions) -> IndexResult:
    """Build the current trace-backed DocSync index."""
    return build_docsync_index(
        options.repo_root,
        config_path=options.config_path,
        trace_path=options.trace_path,
    )


def check_repo(options: CheckOptions) -> CheckResult:
    """Run DocSync structural checks for a repository."""
    return run_check(
        repo_root=options.repo_root,
        config_path=options.config_path,
        trace_path=options.trace_path,
        base_ref=options.base_ref,
    )


def doctor_repo(options: CheckOptions) -> CheckResult:
    """Run DocSync structural validation without Git diff checks."""
    return run_doctor(
        repo_root=options.repo_root,
        config_path=options.config_path,
        trace_path=options.trace_path,
        command="doctor",
        base_ref=options.base_ref,
    )


def create_review_packet(check_result: CheckResult) -> dict[str, Any]:
    """Return a compact agent review packet for DocSync findings."""
    return review_packet_for_result(check_result)


def create_attestation(
    repo_root: Path,
    claim_id: str,
    evidence_ids: Sequence[str],
    reason: str,
) -> Path:
    """Create an attestation for current evidence fingerprints."""
    return create_attestation_file(repo_root, claim_id, tuple(evidence_ids), reason)
