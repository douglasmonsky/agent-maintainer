"""Segment-aware matching for repository path-risk policy."""

from __future__ import annotations

import fnmatch

from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path


class PathPatternError(ValueError):
    """Raised when a path-risk pattern or candidate path is invalid."""


def validate_repo_pattern(value: str, *, label: str) -> str:
    """Return validated repository-relative glob text."""
    try:
        validate_repo_path(value, label=label)
    except RepoPathError as exc:
        raise PathPatternError(str(exc)) from exc
    if any("**" in segment and segment != "**" for segment in value.split("/")):
        raise PathPatternError(f"{label} must use ** only as a complete segment")
    return value


def path_matches(pattern: str, path: str) -> bool:
    """Return whether one repository path matches a validated policy glob."""
    pattern_parts = tuple(validate_repo_pattern(pattern, label="pattern").split("/"))
    try:
        path_parts = tuple(validate_repo_path(path, label="path").split("/"))
    except RepoPathError as exc:
        raise PathPatternError(str(exc)) from exc
    return _match_segments(pattern_parts, path_parts)


def _match_segments(patterns: tuple[str, ...], parts: tuple[str, ...]) -> bool:
    reachable: set[int] = {0}
    for pattern in patterns:
        if pattern == "**":
            reachable = set(range(min(reachable), len(parts) + 1)) if reachable else set()
            continue
        reachable = {
            index + 1
            for index in reachable
            if index < len(parts) and fnmatch.fnmatchcase(parts[index], pattern)
        }
    return len(parts) in reachable
