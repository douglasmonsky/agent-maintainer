"""Transactional filesystem writes for managed hook installation."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agent_client_hooks.adapters import PlannedWrite

BACKUP_ROOT = Path(".agent-maintainer/backups/hooks")
GIT_BACKUP_ROOT = Path("agent-maintainer/backups/hooks")
BACKUP_MANIFEST = "rollback.json"
DEFAULT_FILE_MODE = 0o644


def _empty_written_paths() -> list[Path]:
    return []


class HookMutationError(RuntimeError):
    """Raised after a hook mutation fails and rollback is attempted."""


@dataclass(frozen=True)
class PreparedHookWrite:
    """Rendered hook write with its pre-mutation state."""

    plan: PlannedWrite
    content: str | None
    existed: bool
    changed: bool


@dataclass(frozen=True)
class HookBackup:
    """Backup mapping for one existing destination."""

    original: Path
    backup: Path


@dataclass(frozen=True)
class HookMutationResult:
    """Applied transaction paths and recovery metadata."""

    written: tuple[Path, ...]
    backups: tuple[HookBackup, ...]
    rollback_manifest: Path | None


@dataclass
class HookTransactionState:
    """Mutable recovery state retained when an apply step raises."""

    backups: tuple[HookBackup, ...] = ()
    written: list[Path] = field(default_factory=_empty_written_paths)


def prepare_write(plan: PlannedWrite, content: str) -> PreparedHookWrite:
    """Capture whether one rendered plan would change its destination."""

    if not plan.path.exists():
        return PreparedHookWrite(plan, content, existed=False, changed=True)
    current = plan.path.read_text(encoding="utf-8")
    return PreparedHookWrite(plan, content, existed=True, changed=current != content)


def prepare_delete(plan: PlannedWrite) -> PreparedHookWrite:
    """Prepare removal of one preflighted managed destination."""

    return PreparedHookWrite(
        plan,
        None,
        existed=plan.path.exists(),
        changed=plan.path.exists(),
    )


def apply_transaction(
    prepared: tuple[PreparedHookWrite, ...],
    *,
    ownership_root: Path,
    git_private: bool = False,
) -> HookMutationResult:
    """Back up, atomically apply, and roll back one complete write set."""

    changes = tuple(item for item in prepared if item.changed)
    if not changes:
        return HookMutationResult((), (), None)
    transaction_root = _transaction_root(ownership_root, git_private=git_private)
    state = HookTransactionState()
    try:
        rollback_manifest = _apply_changes(
            changes,
            ownership_root=ownership_root,
            transaction_root=transaction_root,
            state=state,
        )
    except (OSError, ValueError) as exc:
        rollback_errors = _rollback(
            tuple(state.written),
            state.backups,
            changes=changes,
        )
        raise HookMutationError(_mutation_error(exc, rollback_errors)) from exc
    return HookMutationResult(tuple(state.written), state.backups, rollback_manifest)


def atomic_write_text(path: Path, content: str) -> None:
    """Replace one UTF-8 file atomically while retaining its prior mode."""

    path.parent.mkdir(parents=True, exist_ok=True)
    mode = _target_mode(path)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        _replace_with_content(path, temporary, descriptor, content, mode=mode)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def backup_root(ownership_root: Path, *, git_private: bool) -> Path:
    """Return Git-private recovery storage when the target is a repository."""

    git_directory = _git_directory(ownership_root) if git_private else None
    if git_directory is not None:
        return git_directory / GIT_BACKUP_ROOT
    return ownership_root / BACKUP_ROOT


def _transaction_root(ownership_root: Path, *, git_private: bool) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    unique_id = uuid.uuid4().hex
    transaction_id = f"{timestamp}-{unique_id}"
    return backup_root(ownership_root, git_private=git_private) / transaction_id


def _apply_changes(
    changes: tuple[PreparedHookWrite, ...],
    *,
    ownership_root: Path,
    transaction_root: Path,
    state: HookTransactionState,
) -> Path:
    """Create recovery data and apply every prepared change."""

    state.backups = _backup_existing(
        changes,
        ownership_root=ownership_root,
        root=transaction_root,
    )
    rollback_manifest = _write_rollback_manifest(
        transaction_root,
        changes,
        state.backups,
        ownership_root=ownership_root,
    )
    for item in changes:
        if item.content is None:
            item.plan.path.unlink()
        else:
            atomic_write_text(item.plan.path, item.content)
        state.written.append(item.plan.path)
    return rollback_manifest


def _replace_with_content(
    path: Path,
    temporary: Path,
    descriptor: int,
    content: str,
    *,
    mode: int,
) -> None:
    """Populate one temporary file and atomically replace its destination."""

    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(content.encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _backup_existing(
    changes: tuple[PreparedHookWrite, ...],
    *,
    ownership_root: Path,
    root: Path,
) -> tuple[HookBackup, ...]:
    backups: list[HookBackup] = []
    for item in changes:
        if not item.existed:
            continue
        relative = item.plan.path.relative_to(ownership_root)
        backup = root / "files" / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.plan.path, backup)
        backups.append(HookBackup(item.plan.path, backup))
    return tuple(backups)


def _write_rollback_manifest(
    transaction_root: Path,
    changes: tuple[PreparedHookWrite, ...],
    backups: tuple[HookBackup, ...],
    *,
    ownership_root: Path,
) -> Path:
    transaction_root.mkdir(parents=True, exist_ok=True)
    backup_by_path = {item.original: item.backup for item in backups}
    payload = {
        "version": 1,
        "ownership_root": str(ownership_root),
        "files": [
            {
                "path": str(item.plan.path.relative_to(ownership_root)),
                "action": "restore" if item.existed else "remove",
                "backup": str(backup_by_path[item.plan.path].relative_to(transaction_root))
                if item.existed
                else None,
            }
            for item in changes
        ],
    }
    manifest_path = transaction_root / BACKUP_MANIFEST
    atomic_write_text(manifest_path, f"{json.dumps(payload, indent=2, sort_keys=True)}\n")
    return manifest_path


def _rollback(
    written: tuple[Path, ...],
    backups: tuple[HookBackup, ...],
    *,
    changes: tuple[PreparedHookWrite, ...],
) -> tuple[str, ...]:
    backup_by_path = {item.original: item.backup for item in backups}
    change_by_path = {item.plan.path: item for item in changes}
    errors: list[str] = []
    for path in reversed(written):
        item = change_by_path[path]
        try:
            if item.existed:
                shutil.copy2(backup_by_path[path], path)
            else:
                path.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    return tuple(errors)


def _mutation_error(exc: Exception, rollback_errors: tuple[str, ...]) -> str:
    """Return a failure message that states whether rollback completed."""

    if not rollback_errors:
        return f"hook mutation failed and was rolled back: {exc}"
    detail = "; ".join(rollback_errors)
    return f"hook mutation failed; rollback incomplete ({detail}): {exc}"


def _git_directory(root: Path) -> Path | None:
    """Return the real Git directory for a repository or linked worktree."""

    marker = root / ".git"
    if marker.is_dir():
        return marker
    if not marker.is_file():
        return None
    try:
        reference = marker.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    prefix = "gitdir:"
    if not reference.lower().startswith(prefix):
        return None
    candidate = Path(reference[len(prefix) :].strip())
    if not candidate.is_absolute():
        candidate = marker.parent / candidate
    resolved = candidate.resolve()
    return resolved if resolved.is_dir() else None


def _target_mode(path: Path) -> int:
    try:
        metadata = path.stat()
    except FileNotFoundError:
        return DEFAULT_FILE_MODE
    return stat.S_IMODE(metadata.st_mode)
