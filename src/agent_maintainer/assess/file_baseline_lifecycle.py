"""Explicit safe lifecycle for provider-neutral per-path file ceilings."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed local Git inspection commands only
from dataclasses import asdict
from pathlib import Path

from agent_maintainer.assess import file_baseline_state, file_baselines
from agent_maintainer.config.schema import MaintainerConfig


def create_candidate(
    target: Path,
    config: MaintainerConfig,
) -> tuple[Path, file_baseline_state.FileCeilingBaseline]:
    """Build a new deterministic ceiling baseline from one clean Git state."""
    root = _repository_root(target)
    _require_config(config)
    _require_clean_worktree(root)
    destination = file_baselines.configured_baseline_path(
        root,
        config.file_baselines_baseline,
    )
    if destination.exists():
        raise file_baselines.FileBaselineLifecycleError(f"baseline already exists: {destination}")
    candidate = file_baseline_state.create_baseline(
        file_baselines.collect_observations(root, config.file_baselines),
        source_commit=_repository_head(root),
    )
    return destination, candidate


def prune_candidate(
    target: Path,
    config: MaintainerConfig,
) -> tuple[Path, file_baseline_state.FileCeilingBaseline]:
    """Build a candidate that only removes or lowers established ceilings."""
    root = _repository_root(target)
    _require_config(config)
    _require_clean_worktree(root)
    destination = file_baselines.configured_baseline_path(
        root,
        config.file_baselines_baseline,
    )
    try:
        stored = file_baseline_state.read_baseline(destination)
        candidate = file_baseline_state.prune_baseline(
            stored,
            file_baselines.collect_observations(root, config.file_baselines),
            source_commit=_repository_head(root),
        )
    except (OSError, ValueError) as exc:
        raise file_baselines.FileBaselineLifecycleError(
            f"invalid file ceiling baseline: {exc}"
        ) from exc
    return destination, candidate


def inspect_configured(
    target: Path,
    config: MaintainerConfig,
) -> file_baseline_state.FileCeilingBaselineSummary:
    """Read and summarize the configured ceiling baseline without mutation."""
    root = _repository_root(target)
    destination = file_baselines.configured_baseline_path(
        root,
        config.file_baselines_baseline,
    )
    try:
        stored = file_baseline_state.read_baseline(destination)
    except (OSError, ValueError) as exc:
        raise file_baselines.FileBaselineLifecycleError(
            f"invalid file ceiling baseline: {exc}"
        ) from exc
    return file_baseline_state.inspect_baseline(stored)


def render_candidate(candidate: file_baseline_state.FileCeilingBaseline) -> str:
    """Render one lifecycle candidate through the canonical codec."""
    return file_baseline_state.render_baseline(candidate)


def render_summary(
    summary: file_baseline_state.FileCeilingBaselineSummary,
    *,
    json_output: bool,
) -> str:
    """Render deterministic machine or human inspect output."""
    values = asdict(summary)
    if json_output:
        return f"{json.dumps(values, indent=2, sort_keys=True)}\n"
    return "\n".join(f"{key}: {value}" for key, value in values.items()) + "\n"


def write_candidate(
    path: Path,
    candidate: file_baseline_state.FileCeilingBaseline,
    *,
    overwrite: bool,
) -> None:
    """Persist one reviewed lifecycle candidate."""
    file_baseline_state.write_baseline(path, candidate, force=overwrite)


def _repository_root(target: Path) -> Path:
    try:
        root = target.resolve(strict=True)
    except OSError as exc:
        raise file_baselines.FileBaselineLifecycleError(
            f"invalid target repository: {exc}"
        ) from exc
    if not root.is_dir():
        raise file_baselines.FileBaselineLifecycleError(
            f"target repository is not a directory: {root}"
        )
    _repository_head(root)
    return root


def _repository_head(target: Path) -> str:
    completed = _run_git(target, "rev-parse", "HEAD")
    head = completed.stdout.strip().lower()
    if completed.returncode != 0 or file_baseline_state.COMMIT_PATTERN.fullmatch(head) is None:
        raise file_baselines.FileBaselineLifecycleError(
            "target must be a Git repository with a valid HEAD"
        )
    return head


def _require_clean_worktree(target: Path) -> None:
    completed = _run_git(target, "status", "--porcelain", "--untracked-files=all")
    if completed.returncode != 0:
        raise file_baselines.FileBaselineLifecycleError("could not inspect target Git worktree")
    if completed.stdout:
        raise file_baselines.FileBaselineLifecycleError(
            "file ceiling baseline changes require a clean Git worktree"
        )


def _require_config(config: MaintainerConfig) -> None:
    if not config.file_baselines_enabled or not config.file_baselines:
        raise file_baselines.FileBaselineLifecycleError(
            "file ceiling lifecycle requires enabled file_baselines groups"
        )


def _run_git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # nosec B603
            ("git", "-C", str(target), *args),
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
    except OSError as exc:
        raise file_baselines.FileBaselineLifecycleError(f"could not run Git: {exc}") from exc
