"""Explicit Java findings baseline lifecycle from bounded runner evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from agent_maintainer.assess import baseline_repository, java_baseline_evidence
from agent_maintainer.ecosystems.java import baseline


class JavaBaselineLifecycleError(ValueError):
    """One invalid or unsafe Java baseline lifecycle request."""


def create_from_artifact(
    target: Path,
    configured_path: str,
    artifact_path: Path,
) -> tuple[Path, baseline.JavaFindingsBaseline]:
    """Build a new baseline candidate from successful, current evidence."""
    root = baseline_repository.repository_root(target)
    baseline_repository.require_clean_worktree(root, operation="Java baseline")
    evidence = java_baseline_evidence.read_evidence(root, artifact_path)
    destination = baseline_repository.confined_path(
        root,
        Path(configured_path),
        label="Java baseline",
    )
    candidate = baseline.create_baseline(
        evidence.findings,
        source_commit=evidence.source_commit,
    )
    return destination, candidate


def prune_from_artifact(
    target: Path,
    configured_path: str,
    artifact_path: Path,
) -> tuple[Path, baseline.JavaFindingsBaseline]:
    """Build a candidate that only removes or lowers recorded debt."""
    root = baseline_repository.repository_root(target)
    baseline_repository.require_clean_worktree(root, operation="Java baseline")
    evidence = java_baseline_evidence.read_evidence(root, artifact_path)
    destination = baseline_repository.confined_path(
        root,
        Path(configured_path),
        label="Java baseline",
    )
    stored = _read_baseline(destination)
    comparison = baseline.compare_baseline(stored, evidence.findings)
    if not comparison.passed:
        raise JavaBaselineLifecycleError("prune evidence contains new or regressed Java findings")
    candidate = baseline.prune_baseline(
        stored,
        evidence.findings,
        source_commit=evidence.source_commit,
    )
    return destination, candidate


def inspect_configured(
    target: Path,
    configured_path: str,
) -> baseline.JavaBaselineSummary:
    """Read and summarize the configured baseline without changing repository state."""
    root = baseline_repository.repository_root(target)
    destination = baseline_repository.confined_path(
        root,
        Path(configured_path),
        label="Java baseline",
    )
    return baseline.inspect_baseline(_read_baseline(destination))


def render_summary(summary: baseline.JavaBaselineSummary, *, json_output: bool) -> str:
    """Render a deterministic machine or human baseline summary."""
    values = asdict(summary)
    if json_output:
        return f"{json.dumps(values, indent=2, sort_keys=True)}\n"
    rendered = "\n".join(f"{key}: {value}" for key, value in values.items())
    return f"{rendered}\n"


def render_candidate(candidate: baseline.JavaFindingsBaseline) -> str:
    """Render one lifecycle candidate through the canonical baseline codec."""
    return baseline.render_baseline(candidate)


def write_candidate(
    path: Path,
    candidate: baseline.JavaFindingsBaseline,
    *,
    overwrite: bool,
) -> None:
    """Persist one reviewed lifecycle candidate at its confined destination."""
    baseline.write_baseline(path, candidate, force=overwrite)


def _read_baseline(path: Path) -> baseline.JavaFindingsBaseline:
    try:
        return baseline.read_baseline(path)
    except (OSError, ValueError) as exc:
        raise JavaBaselineLifecycleError(f"invalid Java findings baseline: {exc}") from exc
