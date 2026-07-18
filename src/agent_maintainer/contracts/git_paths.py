"""Structured parsing for bounded NUL-delimited Git path facts."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

SINGLE_PATH_KINDS = MappingProxyType(
    {
        "A": "added",
        "D": "deleted",
        "M": "modified",
        "T": "type-changed",
        "U": "unmerged",
    }
)


@dataclass(frozen=True)
class GitPathChange:
    """One structured current or destination Git path fact."""

    path: str
    kind: str
    old_path: str | None = None


def parse_name_status(output: bytes) -> tuple[GitPathChange, ...]:
    """Parse one bounded ``git diff --name-status -z`` payload."""

    tokens = _path_tokens(output)
    changes: list[GitPathChange] = []
    index = 0
    while index < len(tokens):
        status = tokens[index].decode("ascii")
        if status.startswith(("R", "C")):
            change, index = _paired_change(tokens, index, status)
        else:
            change, index = _single_change(tokens, index, status)
        changes.append(change)
    return tuple(changes)


def _path_tokens(output: bytes) -> list[bytes]:
    if not output:
        return []
    if not output.endswith(b"\0"):
        raise ValueError("Git path changes must end with NUL")
    return output[:-1].split(b"\0")


def _paired_change(
    tokens: list[bytes],
    index: int,
    status: str,
) -> tuple[GitPathChange, int]:
    path_index = index + 1
    if not status[1:].isdigit() or path_index + 1 >= len(tokens):
        raise ValueError("invalid paired Git path change")
    old_path = _git_path(tokens[path_index])
    path = _git_path(tokens[path_index + 1])
    kind = "renamed" if status.startswith("R") else "copied"
    return GitPathChange(path, kind, old_path), path_index + 2


def _single_change(
    tokens: list[bytes],
    index: int,
    status: str,
) -> tuple[GitPathChange, int]:
    path_index = index + 1
    kind = SINGLE_PATH_KINDS.get(status)
    if kind is None or path_index >= len(tokens):
        raise ValueError("invalid Git path change")
    return GitPathChange(_git_path(tokens[path_index]), kind), path_index + 1


def _git_path(value: bytes) -> str:
    try:
        return validate_repo_path(value.decode("utf-8"), label="Git path")
    except (UnicodeDecodeError, RepoPathError) as exc:
        raise ValueError("invalid Git path") from exc
