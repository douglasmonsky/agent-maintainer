"""Safely discover and read bounded attention signal artifacts."""

from __future__ import annotations

import heapq
import json
import stat
from pathlib import Path

from agent_context.reading import file_safety
from agent_maintainer.attention import signal_context
from agent_maintainer.runtime_events.read import DEFAULT_RUNTIME_EVENT_FILE_LIMIT

DEFAULT_SIGNAL_ARTIFACT_FILE_LIMIT = DEFAULT_RUNTIME_EVENT_FILE_LIMIT


def artifact_limit(context: signal_context.AttentionSignalContext | None) -> int:
    """Return the active artifact byte ceiling."""

    if context is None:
        return signal_context.DEFAULT_ARTIFACT_READ_LIMIT_BYTES
    return context.artifact_read_limit_bytes


def read_text(
    path: Path,
    *,
    repo_root: Path,
    context: signal_context.AttentionSignalContext | None,
) -> str | None:
    """Read one bounded repository-confined text artifact."""

    safe_read = file_safety.read_bounded_utf8_file(
        path,
        workspace_root=repo_root,
        max_bytes=artifact_limit(context),
    )
    if safe_read.safety.allowed and safe_read.text is not None:
        return safe_read.text
    _record_oversize_refusal(path, safe_read.safety.reason, context=context)
    return None


def read_json(
    path: Path,
    *,
    repo_root: Path,
    context: signal_context.AttentionSignalContext | None = None,
) -> object | None:
    """Read one repository-confined JSON artifact when valid."""

    text = read_text(path, repo_root=repo_root, context=context)
    if text is None:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        return None


def manifest_paths(repo_root: Path, *, log_dir: Path) -> tuple[Path, ...]:
    """Return the bounded newest safe verifier manifest paths."""

    runs_dir = _safe_repository_directory(log_dir / "runs", repo_root=repo_root)
    if runs_dir is None:
        return ()
    manifests: list[tuple[int, str, Path]] = []
    try:
        for run_dir in runs_dir.iterdir():
            candidate = _manifest_candidate(run_dir, repo_root=repo_root)
            if candidate is not None:
                heapq.heappush(manifests, candidate)
                if len(manifests) > DEFAULT_SIGNAL_ARTIFACT_FILE_LIMIT:
                    heapq.heappop(manifests)
    except OSError:
        return ()
    return tuple(item[2] for item in sorted(manifests))


def _record_oversize_refusal(
    path: Path,
    reason: str,
    *,
    context: signal_context.AttentionSignalContext | None,
) -> None:
    """Record one performance refusal without exposing unrelated failures."""

    if context is not None and "exceeds" in reason:
        name = path.name
        context.performance_notes.append(f"artifact refused {name}: {reason}")


def _manifest_candidate(
    run_dir: Path,
    *,
    repo_root: Path,
) -> tuple[int, str, Path] | None:
    """Return one safe run's sortable manifest candidate."""

    safe_run_dir = _safe_repository_directory(run_dir, repo_root=repo_root)
    if safe_run_dir is None:
        return None
    try:
        metadata = safe_run_dir.lstat()
    except OSError:
        return None
    if not stat.S_ISDIR(metadata.st_mode):
        return None
    return metadata.st_mtime_ns, safe_run_dir.name, safe_run_dir / "manifest.json"


def _safe_repository_directory(path: Path, *, repo_root: Path) -> Path | None:
    """Return a confined regular directory without following symlinks."""

    confined = file_safety.confined_path(path, workspace_root=repo_root)
    if isinstance(confined, file_safety.FileSafety):
        return None
    if (
        file_safety.refused_path(confined)
        or file_safety.sensitive_path(confined)
        or file_safety.has_symlink_parent(confined)
    ):
        return None
    try:
        metadata = confined.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        return None
    return confined
