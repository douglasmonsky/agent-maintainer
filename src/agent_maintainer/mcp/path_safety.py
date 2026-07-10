"""Repository-confined path validation for MCP tool arguments."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_context.reading.file_safety import MAX_FILE_BYTES, sensitive_path

PathKind = Literal["any", "directory", "file"]
MAX_CONTEXT_FILE_BYTES = MAX_FILE_BYTES
MCP_GENERATED_ROOT = Path(".verify-logs")


@dataclass(frozen=True)
class WorkspacePathPolicy:
    """Expected kind and disclosure limits for one MCP path argument."""

    kind: PathKind = "any"
    allow_missing: bool = True
    reject_sensitive: bool = False
    max_bytes: int | None = None


ANY_PATH = WorkspacePathPolicy()
DIRECTORY_PATH = WorkspacePathPolicy(kind="directory")
EXISTING_DIRECTORY_PATH = WorkspacePathPolicy(kind="directory", allow_missing=False)
BOUNDED_INPUT_FILE_PATH = WorkspacePathPolicy(
    kind="file",
    allow_missing=False,
    reject_sensitive=True,
    max_bytes=MAX_FILE_BYTES,
)
OUTPUT_FILE_PATH = WorkspacePathPolicy(kind="file")
CONTEXT_FILE_PATH = WorkspacePathPolicy(
    kind="file",
    allow_missing=False,
    reject_sensitive=True,
    max_bytes=MAX_CONTEXT_FILE_BYTES,
)


def resolve_workspace_root(workspace_root: Path) -> Path:
    """Return one canonical existing MCP workspace directory."""

    try:
        resolved = workspace_root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"workspace root is unavailable: {workspace_root}: {exc}") from exc
    if not resolved.is_dir():
        raise ValueError(f"workspace root is not a directory: {workspace_root}")
    return resolved


def validate_workspace_path(
    value: str,
    *,
    workspace_root: Path,
    label: str,
    policy: WorkspacePathPolicy = ANY_PATH,
) -> str:
    """Validate and normalize one model-controlled path below a workspace root."""

    root = resolve_workspace_root(workspace_root)
    relative = _validated_relative_value(value, label=label)
    if policy.reject_sensitive and sensitive_path(relative):
        raise ValueError(f"{label} is a sensitive path and cannot be read")
    return _validated_existing_path(root, relative, label=label, policy=policy)


def _validated_relative_value(value: str, *, label: str) -> Path:
    """Return normalized relative model input after lexical checks."""

    candidate = Path(value)
    if not value.strip():
        raise ValueError(f"{label} must not be empty")
    if candidate.is_absolute():
        raise ValueError(f"{label} must be relative to the workspace root")
    if ".." in candidate.parts:
        raise ValueError(f"{label} must not contain parent traversal")
    return _normalized_relative_path(candidate)


def _validated_existing_path(
    root: Path,
    relative: Path,
    *,
    label: str,
    policy: WorkspacePathPolicy,
) -> str:
    """Apply kind and size policy to one normalized workspace path."""

    existing_stat = _inspect_components(root, relative, label=label)
    if existing_stat is None:
        if not policy.allow_missing:
            raise ValueError(f"{label} does not exist inside the workspace")
        return str(relative)
    _validate_kind(existing_stat.st_mode, label=label, kind=policy.kind)
    if (
        policy.max_bytes is not None
        and stat.S_ISREG(existing_stat.st_mode)
        and existing_stat.st_size > policy.max_bytes
    ):
        raise ValueError(f"{label} exceeds the {policy.max_bytes} byte limit")
    return str(relative)


def validate_generated_workspace_path(
    value: str,
    *,
    workspace_root: Path,
    label: str,
    policy: WorkspacePathPolicy = DIRECTORY_PATH,
) -> str:
    """Validate one path inside the MCP-dedicated generated-artifact root."""

    normalized = Path(
        validate_workspace_path(
            value,
            workspace_root=workspace_root,
            label=label,
            policy=policy,
        )
    )
    try:
        normalized.relative_to(MCP_GENERATED_ROOT)
    except ValueError as exc:
        raise ValueError(f"{label} must remain under {MCP_GENERATED_ROOT}") from exc
    return str(normalized)


def _normalized_relative_path(path: Path) -> Path:
    """Return a stable relative path without no-op components."""

    parts = tuple(part for part in path.parts if part not in ("", "."))
    return Path(*parts) if parts else Path(".")


def _inspect_components(
    root: Path,
    relative: Path,
    *,
    label: str,
) -> os.stat_result | None:
    """Inspect existing components without following repository symlinks."""

    current = root
    current_stat = root.lstat()
    parts = relative.parts
    if relative == Path("."):
        return current_stat
    for index, part in enumerate(parts):
        current /= part
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ValueError(f"{label} cannot be inspected safely: {exc}") from exc
        if stat.S_ISLNK(current_stat.st_mode):
            raise ValueError(f"{label} must not contain symlink components")
        if index < len(parts) - 1 and not stat.S_ISDIR(current_stat.st_mode):
            raise ValueError(f"{label} has a non-directory parent component")
    return current_stat


def _validate_kind(mode: int, *, label: str, kind: PathKind) -> None:
    """Require an existing path to match the tool's expected path kind."""

    if kind == "file" and not stat.S_ISREG(mode):
        raise ValueError(f"{label} must be a regular file")
    if kind == "directory" and not stat.S_ISDIR(mode):
        raise ValueError(f"{label} must be a directory")
    if kind == "any" and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        raise ValueError(f"{label} must be a regular file or directory")
