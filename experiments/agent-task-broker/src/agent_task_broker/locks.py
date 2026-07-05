"""Task-scoped lock rules for the task broker incubator."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import PurePosixPath

LOCK_KIND_PATH = "path"
LOCK_KIND_PACKAGE = "package"
LOCK_KIND_DOC = "doc"
LOCK_KIND_CONFIG = "config"
LOCK_KIND_TACH = "tach"
LOCK_KINDS = (
    LOCK_KIND_PATH,
    LOCK_KIND_PACKAGE,
    LOCK_KIND_DOC,
    LOCK_KIND_CONFIG,
    LOCK_KIND_TACH,
)

LOCK_MODE_READ = "read"
LOCK_MODE_WRITE = "write"
LOCK_MODE_EXCLUSIVE = "exclusive"
LOCK_MODES = (LOCK_MODE_READ, LOCK_MODE_WRITE, LOCK_MODE_EXCLUSIVE)


@dataclass(frozen=True)
class LockRequest:
    """Requested task lock."""

    task_id: str
    kind: str
    target: str
    mode: str


@dataclass(frozen=True)
class LockConflict:
    """Conflict between a requested lock and an existing lock."""

    lock_id: str
    task_id: str
    kind: str
    target: str
    mode: str
    reason: str


class LockError(ValueError):
    """Lock operation failed."""


def lock_payload(lock_id: str, request: LockRequest) -> dict[str, object]:
    """Return validated lock payload."""
    validate_lock_request(request)
    return {
        "id": lock_id,
        "task_id": request.task_id,
        "kind": request.kind,
        "target": normalize_lock_target(request.target),
        "mode": request.mode,
    }


def validate_lock_request(request: LockRequest) -> None:
    """Validate one lock request."""
    if request.kind not in LOCK_KINDS:
        raise LockError(f"unknown lock kind: {request.kind}")
    if request.mode not in LOCK_MODES:
        raise LockError(f"unknown lock mode: {request.mode}")
    if not normalize_lock_target(request.target):
        raise LockError("lock target is required")


def find_lock_conflicts(
    existing_locks: list[dict[str, object]],
    request: LockRequest,
) -> list[LockConflict]:
    """Return existing locks that conflict with request."""
    validate_lock_request(request)
    target = normalize_lock_target(request.target)
    conflicts: list[LockConflict] = []
    for existing in existing_locks:
        if str(existing.get("task_id")) == request.task_id:
            continue
        if lock_modes_compatible(str(existing.get("mode")), request.mode):
            continue
        existing_target = str(existing.get("target", ""))
        if not targets_overlap(
            str(existing.get("kind")),
            existing_target,
            request.kind,
            target,
        ):
            continue
        conflicts.append(
            LockConflict(
                lock_id=str(existing.get("id")),
                task_id=str(existing.get("task_id")),
                kind=str(existing.get("kind")),
                target=existing_target,
                mode=str(existing.get("mode")),
                reason=f"{request.mode} {request.kind} lock overlaps {existing.get('mode')} lock",
            ),
        )
    return conflicts


def lock_modes_compatible(existing_mode: str, requested_mode: str) -> bool:
    """Return whether two overlapping lock modes can coexist."""
    return existing_mode == LOCK_MODE_READ and requested_mode == LOCK_MODE_READ


def targets_overlap(
    existing_kind: str,
    existing_target: str,
    requested_kind: str,
    requested_target: str,
) -> bool:
    """Return whether two lock resources overlap."""
    existing_pattern = target_pattern(existing_kind, existing_target)
    requested_pattern = target_pattern(requested_kind, requested_target)
    if pattern_matches(existing_pattern, requested_target):
        return True
    if pattern_matches(requested_pattern, existing_target):
        return True
    if LOCK_KIND_PACKAGE in {existing_kind, requested_kind}:
        return path_prefix_overlap(existing_target, requested_target)
    return False


def target_pattern(kind: str, target: str) -> str:
    """Return a glob-like target pattern for one lock."""
    normalized = normalize_lock_target(target)
    if kind == LOCK_KIND_PACKAGE and not has_glob(normalized):
        return f"{normalized.rstrip('/')}/**"
    return normalized


def pattern_matches(pattern: str, target: str) -> bool:
    """Return whether pattern matches target."""
    normalized_pattern = normalize_lock_target(pattern)
    normalized_target = normalize_lock_target(target)
    if normalized_pattern == normalized_target:
        return True
    return fnmatch.fnmatchcase(normalized_target, normalized_pattern)


def path_prefix_overlap(left: str, right: str) -> bool:
    """Return whether two path-like targets share a package prefix."""
    left_normalized = normalize_lock_target(left).rstrip("/")
    right_normalized = normalize_lock_target(right).rstrip("/")
    return (
        left_normalized == right_normalized
        or right_normalized.startswith(f"{left_normalized}/")
        or left_normalized.startswith(f"{right_normalized}/")
    )


def normalize_lock_target(target: str) -> str:
    """Return stable repo-relative lock target."""
    normalized = target.replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/") or ".." in PurePosixPath(normalized).parts:
        raise LockError(f"lock target must be repo-relative: {target}")
    return normalized.rstrip("/")


def has_glob(target: str) -> bool:
    """Return whether target contains glob characters."""
    return any(marker in target for marker in ("*", "?", "["))
