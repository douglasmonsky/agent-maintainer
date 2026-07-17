"""Explicit safe lifecycle for provider-neutral per-path file ceilings."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.assess import (
    baseline_repository,
    file_baseline_codec,
    file_baseline_state,
    file_baselines,
)
from agent_maintainer.config.schema import MaintainerConfig


def create_candidate(
    target: Path,
    config: MaintainerConfig,
) -> tuple[Path, file_baseline_state.FileCeilingBaseline]:
    """Build a new deterministic ceiling baseline from one clean Git state."""
    root = baseline_repository.repository_root(target)
    _require_config(config)
    baseline_repository.require_clean_worktree(root, operation="file ceiling baseline")
    destination = file_baselines.configured_baseline_path(
        root,
        config.file_baselines_baseline,
    )
    if destination.exists():
        raise file_baselines.FileBaselineLifecycleError(f"baseline already exists: {destination}")
    candidate = file_baseline_state.create_baseline(
        file_baselines.collect_observations(root, config.file_baselines),
        source_commit=baseline_repository.repository_head(root),
    )
    return destination, candidate


def prune_candidate(
    target: Path,
    config: MaintainerConfig,
) -> tuple[Path, file_baseline_state.FileCeilingBaseline]:
    """Build a candidate that only removes or lowers established ceilings."""
    root = baseline_repository.repository_root(target)
    _require_config(config)
    baseline_repository.require_clean_worktree(root, operation="file ceiling baseline")
    destination = file_baselines.configured_baseline_path(
        root,
        config.file_baselines_baseline,
    )
    stored = _read_baseline(destination)
    candidate = file_baseline_state.prune_baseline(
        stored,
        file_baselines.collect_observations(root, config.file_baselines),
        source_commit=baseline_repository.repository_head(root),
    )
    return destination, candidate


def inspect_configured(
    target: Path,
    config: MaintainerConfig,
) -> file_baseline_state.FileCeilingBaselineSummary:
    """Read and summarize the configured ceiling baseline without mutation."""
    root = baseline_repository.repository_root(target)
    destination = file_baselines.configured_baseline_path(
        root,
        config.file_baselines_baseline,
    )
    return file_baseline_state.inspect_baseline(_read_baseline(destination))


def render_candidate(candidate: file_baseline_state.FileCeilingBaseline) -> str:
    """Render one lifecycle candidate through the canonical codec."""
    return file_baseline_codec.render_baseline(candidate)


def render_summary(
    summary: file_baseline_state.FileCeilingBaselineSummary,
    *,
    json_output: bool,
) -> str:
    """Render deterministic machine or human inspect output."""
    values = {
        "version": summary.version,
        "source_commit": summary.source_commit,
        "entry_count": summary.entry_count,
        "group_count": summary.group_count,
    }
    if json_output:
        return f"{json.dumps(values, indent=2, sort_keys=True)}\n"
    rendered = "\n".join(f"{key}: {value}" for key, value in values.items())
    return f"{rendered}\n"


def write_candidate(
    path: Path,
    candidate: file_baseline_state.FileCeilingBaseline,
    *,
    overwrite: bool,
) -> None:
    """Persist one reviewed lifecycle candidate."""
    file_baseline_codec.write_baseline(path, candidate, force=overwrite)


def _read_baseline(path: Path) -> file_baseline_state.FileCeilingBaseline:
    try:
        return file_baseline_codec.read_baseline(path)
    except (OSError, ValueError) as exc:
        raise file_baselines.FileBaselineLifecycleError(
            f"invalid file ceiling baseline: {exc}"
        ) from exc


def _require_config(config: MaintainerConfig) -> None:
    if not config.file_baselines_enabled or not config.file_baselines:
        raise file_baselines.FileBaselineLifecycleError(
            "file ceiling lifecycle requires enabled file_baselines groups"
        )
