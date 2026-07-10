"""Transactional application for preflighted initializer plans."""

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

from agent_maintainer.core.scaffold.planning import InitPlanItem

BACKUP_ROOT = Path(".agent-maintainer/backups/init")
DEFAULT_FILE_MODE = 0o644


class InitTransactionError(RuntimeError):
    """Raised when initializer apply cannot preserve a coherent state."""


@dataclass(frozen=True)
class InitBackup:
    """Backup mapping for one replaced initializer destination."""

    original: Path
    backup: Path


@dataclass
class InitTransactionState:
    """Mutable recovery state retained across an interrupted apply."""

    backups: tuple[InitBackup, ...] = ()
    written: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class InitTransactionResult:
    """Applied destinations and their rollback metadata."""

    written: tuple[Path, ...]
    backups: tuple[InitBackup, ...]
    rollback_manifest: Path | None


def apply_transaction(
    items: tuple[InitPlanItem, ...],
    *,
    target: Path,
) -> InitTransactionResult:
    """Back up and atomically apply all selected initializer items."""

    if not items:
        return InitTransactionResult((), (), None)
    transaction_root = _transaction_root(target)
    state = InitTransactionState()
    try:
        rollback_manifest = _apply_items(
            items,
            target=target,
            transaction_root=transaction_root,
            state=state,
        )
    except (OSError, ValueError) as exc:
        rollback_errors = _rollback(state, items=items)
        raise InitTransactionError(_failure_message(exc, rollback_errors)) from exc
    return InitTransactionResult(tuple(state.written), state.backups, rollback_manifest)


def atomic_write_text(path: Path, content: str) -> None:
    """Write one UTF-8 destination through same-directory atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    mode = _target_mode(path)
    try:
        _replace_with_content(path, temporary, descriptor, content, mode=mode)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _apply_items(
    items: tuple[InitPlanItem, ...],
    *,
    target: Path,
    transaction_root: Path,
    state: InitTransactionState,
) -> Path:
    state.backups = _backup_existing(items, target=target, root=transaction_root)
    manifest = _write_rollback_manifest(
        transaction_root,
        items,
        state.backups,
        target=target,
    )
    for item in items:
        if item.content is None:
            continue
        atomic_write_text(item.destination, item.content)
        state.written.append(item.destination)
    return manifest


def _backup_existing(
    items: tuple[InitPlanItem, ...],
    *,
    target: Path,
    root: Path,
) -> tuple[InitBackup, ...]:
    backups: list[InitBackup] = []
    for item in items:
        if not item.destination.exists():
            continue
        relative = item.destination.relative_to(target)
        backup = root / "files" / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.destination, backup)
        backups.append(InitBackup(item.destination, backup))
    return tuple(backups)


def _write_rollback_manifest(
    transaction_root: Path,
    items: tuple[InitPlanItem, ...],
    backups: tuple[InitBackup, ...],
    *,
    target: Path,
) -> Path:
    transaction_root.mkdir(parents=True, exist_ok=True)
    backup_by_path = {item.original: item.backup for item in backups}
    payload = {
        "version": 1,
        "target": str(target),
        "files": [
            _rollback_entry(item, target, transaction_root, backup_by_path) for item in items
        ],
    }
    path = transaction_root / "rollback.json"
    atomic_write_text(path, f"{json.dumps(payload, indent=2, sort_keys=True)}\n")
    return path


def _rollback_entry(
    item: InitPlanItem,
    target: Path,
    transaction_root: Path,
    backup_by_path: dict[Path, Path],
) -> dict[str, object]:
    backup = backup_by_path.get(item.destination)
    if backup is None:
        action = "remove"
        backup_path = None
    else:
        action = "restore"
        backup_path = str(backup.relative_to(transaction_root))
    return {
        "path": str(item.destination.relative_to(target)),
        "action": action,
        "backup": backup_path,
    }


def _rollback(
    state: InitTransactionState,
    *,
    items: tuple[InitPlanItem, ...],
) -> tuple[str, ...]:
    backup_by_path = {item.original: item.backup for item in state.backups}
    existing_paths = {item.original for item in state.backups}
    item_paths = {item.destination for item in items}
    errors: list[str] = []
    for path in reversed(state.written):
        try:
            if path in existing_paths:
                shutil.copy2(backup_by_path[path], path)
            elif path in item_paths:
                path.unlink(missing_ok=True)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    return tuple(errors)


def _replace_with_content(
    path: Path,
    temporary: Path,
    descriptor: int,
    content: str,
    *,
    mode: int,
) -> None:
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(content.encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _transaction_root(target: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    unique_id = uuid.uuid4().hex
    return target / BACKUP_ROOT / f"{timestamp}-{unique_id}"


def _failure_message(exc: Exception, rollback_errors: tuple[str, ...]) -> str:
    if not rollback_errors:
        return f"initializer failed and was rolled back: {exc}"
    detail = "; ".join(rollback_errors)
    return f"initializer failed; rollback incomplete ({detail}): {exc}"


def _target_mode(path: Path) -> int:
    try:
        metadata = path.stat()
    except FileNotFoundError:
        return DEFAULT_FILE_MODE
    return stat.S_IMODE(metadata.st_mode)
