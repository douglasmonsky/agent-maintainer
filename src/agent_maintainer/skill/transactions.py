"""Atomic skill-directory replacement with rollback."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path


class SkillMutationError(RuntimeError):
    """Raised when a staged skill-directory mutation cannot complete."""


def replace_destination(destination: Path, mutation: Callable[[Path], None]) -> None:
    """Apply one mutation to a staged sibling and atomically replace its target."""
    staged = _staged_copy(destination)
    try:
        _mutate_and_swap(destination, staged, mutation)
    except OSError as exc:
        raise SkillMutationError(f"skill mutation failed before replacement: {exc}") from exc
    finally:
        _cleanup_staged(staged)


def _staged_copy(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.stage-",
            dir=destination.parent,
        )
    )
    if destination.exists():
        shutil.copytree(destination, staged, dirs_exist_ok=True, symlinks=True)
    return staged


def _mutate_and_swap(
    destination: Path,
    staged: Path,
    mutation: Callable[[Path], None],
) -> None:
    mutation(staged)
    if not destination.exists():
        os.replace(staged, destination)
        return
    backup = _backup_path(destination)
    os.replace(destination, backup)
    _install_or_restore(staged, destination, backup)
    shutil.rmtree(backup)


def _backup_path(destination: Path) -> Path:
    suffix = uuid.uuid4().hex
    return destination.parent / f".{destination.name}.backup-{suffix}"


def _install_or_restore(staged: Path, destination: Path, backup: Path) -> None:
    try:
        os.replace(staged, destination)
    except OSError as exc:
        _restore_backup(backup, destination, cause=exc)


def _restore_backup(backup: Path, destination: Path, *, cause: OSError) -> None:
    try:
        os.replace(backup, destination)
    except OSError as rollback_error:
        detail = f"rollback incomplete ({rollback_error}): {cause}"
        raise SkillMutationError(f"skill mutation failed; {detail}") from cause
    raise SkillMutationError(f"skill mutation failed and was rolled back: {cause}") from cause


def _cleanup_staged(staged: Path) -> None:
    if staged.exists():
        shutil.rmtree(staged, ignore_errors=True)
