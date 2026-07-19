"""Provider-aware changed-file classification helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.models import (
    ChangeKind,
    FileChangeClassification,
    FileClassification,
    FileRole,
)
from agent_maintainer.ecosystems.registry import classification_candidates

HIGH_CONFIDENCE_ROLES = frozenset(
    (
        FileRole.SOURCE,
        FileRole.HEADER,
        FileRole.TEST,
        FileRole.GENERATED,
        FileRole.DEPENDENCY,
        FileRole.IGNORED,
    ),
)


@dataclass(frozen=True)
class ChangedPath:
    """Repository path plus its observed change kind."""

    path: str
    change_kind: ChangeKind = ChangeKind.UNKNOWN


def classify_changed_paths(
    changes: Iterable[ChangedPath],
    config: MaintainerConfig,
    *,
    repo_root: Path | None = None,
) -> tuple[FileChangeClassification, ...]:
    """Classify changed paths across enabled built-in ecosystem providers."""
    return tuple(
        classification
        for change in changes
        if (
            classification := classify_changed_path(
                change.path,
                change.change_kind,
                config,
                repo_root=repo_root,
            )
        )
        is not None
    )


def classify_changed_path(
    path: str | Path,
    change_kind: ChangeKind | str,
    config: MaintainerConfig,
    *,
    repo_root: Path | None = None,
) -> FileChangeClassification | None:
    """Classify one changed path without applying reviewability policy."""
    selected = _select_classification(
        _classify_path_candidates(path, config, repo_root=repo_root),
    )
    if selected is None:
        return None
    return FileChangeClassification.from_file_classification(
        selected,
        change_kind=_coerce_change_kind(change_kind),
    )


def _classify_path_candidates(
    path: str | Path,
    config: MaintainerConfig,
    *,
    repo_root: Path | None,
) -> tuple[FileClassification, ...]:
    """Return classifications from providers active for this repository."""
    return classification_candidates(path, config, repo_root=repo_root)


def _select_classification(
    candidates: tuple[FileClassification, ...],
) -> FileClassification | None:
    """Pick the strongest provider classification for shared repo files."""
    for candidate in candidates:
        if candidate.role in HIGH_CONFIDENCE_ROLES:
            return candidate
    return candidates[0] if candidates else None


def _coerce_change_kind(change_kind: ChangeKind | str) -> ChangeKind:
    """Normalize external change kind strings to the internal enum."""
    if isinstance(change_kind, ChangeKind):
        return change_kind
    normalized = change_kind.strip().lower()
    try:
        return ChangeKind(normalized)
    except ValueError:
        return ChangeKind.UNKNOWN
