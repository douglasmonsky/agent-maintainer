"""Shared bounded attention signal inputs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MAX_TRACKED_FILES = 5_000
DEFAULT_ARTIFACT_READ_LIMIT_BYTES = 200_000
TrackedFilesProvider = Callable[[Path], tuple[str, ...]]


def _empty_performance_notes() -> list[str]:
    return []


@dataclass
class AttentionSignalContext:
    """Shared bounded inputs for one attention ledger build."""

    repo_root: Path
    tracked_paths: tuple[str, ...]
    all_tracked_file_count: int
    artifact_read_limit_bytes: int = DEFAULT_ARTIFACT_READ_LIMIT_BYTES
    performance_notes: list[str] = field(default_factory=_empty_performance_notes)

    @classmethod
    def build(
        cls,
        repo_root: Path,
        *,
        tracked_files: TrackedFilesProvider,
        max_tracked_files: int = DEFAULT_MAX_TRACKED_FILES,
        artifact_read_limit_bytes: int = DEFAULT_ARTIFACT_READ_LIMIT_BYTES,
    ) -> AttentionSignalContext:
        """Collect tracked files once and apply a deterministic cap."""

        paths = tracked_files(repo_root)
        sampled_paths = _sample_paths(paths, max_tracked_files)
        notes: list[str] = []
        if len(sampled_paths) < len(paths):
            notes.append(
                "tracked file set capped "
                f"{len(sampled_paths)}/{len(paths)} using deterministic sampling",
            )
        return cls(
            repo_root=repo_root,
            tracked_paths=sampled_paths,
            all_tracked_file_count=len(paths),
            artifact_read_limit_bytes=artifact_read_limit_bytes,
            performance_notes=notes,
        )

    @property
    def known_paths(self) -> set[str]:
        """Return sampled tracked paths set."""

        return set(self.tracked_paths)


def _sample_paths(paths: tuple[str, ...], limit: int) -> tuple[str, ...]:
    """Return deterministic sampled paths within limit."""

    if limit <= 0 or len(paths) <= limit:
        return paths
    if limit == 1:
        return (paths[0],)
    step = (len(paths) - 1) / (limit - 1)
    indexes = {round(index * step) for index in range(limit)}
    return tuple(paths[index] for index in sorted(indexes))
