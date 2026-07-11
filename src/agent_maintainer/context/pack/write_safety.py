"""Safe context-pack output preflight and atomic writes."""

from __future__ import annotations

import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path

from agent_context.reading import file_safety

PACK_CONTEXT_DIR = "context"
PACK_MARKDOWN_NAME = "PACK.md"
PACK_JSON_NAME = "PACK.json"
DEFAULT_FILE_MODE = 0o644


def safe_pack_write_targets(log_dir: Path) -> tuple[Path, Path]:
    """Return preflighted pack destinations within the selected log directory."""

    workspace_root = log_dir.parent if log_dir.is_absolute() else Path.cwd()
    confined_log_dir = file_safety.confined_path(log_dir, workspace_root=workspace_root)
    if isinstance(confined_log_dir, file_safety.FileSafety):
        raise ValueError(f"unsafe context-pack log directory: {confined_log_dir.reason}")
    context_dir = confined_log_dir / PACK_CONTEXT_DIR
    targets = (context_dir / PACK_MARKDOWN_NAME, context_dir / PACK_JSON_NAME)
    for target in targets:
        validate_pack_write_target(target, workspace_root=workspace_root)
    return targets


def validate_pack_write_target(path: Path, *, workspace_root: Path) -> None:
    """Reject symlink, special-file, and non-directory output components."""

    root = workspace_root.resolve(strict=True)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"context-pack output escapes workspace root: {path}") from exc
    _validate_pack_parent_components(root, relative)
    _validate_pack_leaf(path)


def _validate_pack_parent_components(root: Path, relative: Path) -> None:
    """Require every existing pack-output parent to be a real directory."""

    current = root
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise ValueError(f"cannot inspect context-pack output parent: {current}") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"context-pack output parent must be a real directory: {current}")


def _validate_pack_leaf(path: Path) -> None:
    """Require an existing pack-output leaf to be a regular file."""

    try:
        target_metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ValueError(f"cannot inspect context-pack output: {path}") from exc
    if not stat.S_ISREG(target_metadata.st_mode):
        raise ValueError(f"context-pack output must be a regular file: {path}")


def atomic_write_text(path: Path, content: str) -> None:
    """Replace one preflighted context-pack file atomically."""

    mode = _existing_pack_mode(path)
    temporary_path = _write_temporary(path, content, mode=mode)
    try:
        os.replace(temporary_path, path)
    except OSError:
        _remove_temporary(temporary_path)
        raise


def _write_temporary(path: Path, content: str, *, mode: int) -> Path:
    """Write and close one temporary file beside its final destination."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(content.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        _remove_temporary(temporary_path)
        raise
    return temporary_path


def _remove_temporary(path: Path) -> None:
    """Remove an abandoned temporary file if it still exists."""

    with suppress(FileNotFoundError):
        path.unlink()


def _existing_pack_mode(path: Path) -> int:
    """Return a safe mode for one context-pack destination."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return DEFAULT_FILE_MODE
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"context-pack output must be a regular file: {path}")
    return stat.S_IMODE(metadata.st_mode)
