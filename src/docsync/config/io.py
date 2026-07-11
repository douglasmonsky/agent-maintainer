"""Bounded reads and atomic writes for preflighted DocSync paths."""

from __future__ import annotations

import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO

from docsync.config.errors import PathBoundaryError

DEFAULT_WRITE_MODE = 0o644
MAX_REPOSITORY_INPUT_BYTES = 8_388_608


def read_bounded_text(
    path: Path,
    *,
    label: str,
    max_bytes: int = MAX_REPOSITORY_INPUT_BYTES,
) -> str:
    """Read one UTF-8 regular file while enforcing a byte ceiling."""

    descriptor = _open_read_descriptor(path, label=label)
    with os.fdopen(descriptor, "rb") as stream:
        metadata = _descriptor_metadata(stream.fileno(), path=path, label=label)
        _require_bounded_regular(metadata, path=path, label=label, max_bytes=max_bytes)
        payload = _read_bounded(stream, limit=max_bytes + 1)
    if len(payload) > max_bytes:
        raise PathBoundaryError(f"{label} exceeds the {max_bytes}-byte limit: {path}")
    return _decode_text(payload, path=path, label=label)


def write_text_file(path: Path, content: str, *, label: str) -> None:
    """Atomically write UTF-8 text without following a final symlink."""

    mode = _safe_write_mode(path, label=label)
    temporary_path = _write_temporary(path, content, mode=mode, label=label)
    _replace_temporary(temporary_path, path, label=label)


def validate_write_target(path: Path, *, label: str) -> Path:
    """Require an existing write target to be a regular non-symlink file."""

    metadata = _optional_lstat(path, label=label)
    if metadata is None:
        return path
    if not stat.S_ISREG(metadata.st_mode):
        raise PathBoundaryError(f"{label} must be a regular file: {path}")
    return path


def _open_read_descriptor(path: Path, *, label: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        return os.open(path, flags)
    except OSError as exc:
        raise PathBoundaryError(f"Cannot read {label}: {path}") from exc


def _descriptor_metadata(descriptor: int, *, path: Path, label: str) -> os.stat_result:
    try:
        return os.fstat(descriptor)
    except OSError as exc:
        raise PathBoundaryError(f"Cannot inspect {label}: {path}") from exc


def _require_bounded_regular(
    metadata: os.stat_result,
    *,
    path: Path,
    label: str,
    max_bytes: int,
) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise PathBoundaryError(f"{label} must be a regular file: {path}")
    if metadata.st_size > max_bytes:
        raise PathBoundaryError(f"{label} exceeds the {max_bytes}-byte limit: {path}")


def _decode_text(payload: bytes, *, path: Path, label: str) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PathBoundaryError(f"{label} must be UTF-8 text: {path}") from exc


def _write_temporary(path: Path, content: str, *, mode: int, label: str) -> Path:
    descriptor, temporary_path = _create_temporary(path, label=label)
    try:
        _write_descriptor(descriptor, content, mode=mode)
    except OSError as exc:
        _remove_temporary(temporary_path)
        raise PathBoundaryError(f"Cannot write {label}: {path}") from exc
    return temporary_path


def _create_temporary(path: Path, *, label: str) -> tuple[int, Path]:
    try:
        created = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    except OSError as exc:
        raise PathBoundaryError(f"Cannot write {label}: {path}") from exc
    return created[0], Path(created[1])


def _write_descriptor(descriptor: int, content: str, *, mode: int) -> None:
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(content.encode("utf-8"))


def _replace_temporary(temporary_path: Path, path: Path, *, label: str) -> None:
    try:
        os.replace(temporary_path, path)
    except OSError as exc:
        _remove_temporary(temporary_path)
        raise PathBoundaryError(f"Cannot write {label}: {path}") from exc


def _remove_temporary(path: Path) -> None:
    with suppress(FileNotFoundError):
        path.unlink()


def _safe_write_mode(path: Path, *, label: str) -> int:
    parent_metadata = _required_lstat(path.parent, label=f"parent for {label}")
    if not stat.S_ISDIR(parent_metadata.st_mode):
        raise PathBoundaryError(f"Parent for {label} must be a directory: {path.parent}")
    metadata = _optional_lstat(path, label=label)
    if metadata is None:
        return DEFAULT_WRITE_MODE
    if not stat.S_ISREG(metadata.st_mode):
        raise PathBoundaryError(f"{label} must be a regular file: {path}")
    return stat.S_IMODE(metadata.st_mode)


def _required_lstat(path: Path, *, label: str) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise PathBoundaryError(f"Cannot inspect {label}: {path}") from exc


def _optional_lstat(path: Path, *, label: str) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PathBoundaryError(f"Cannot inspect {label}: {path}") from exc


def _read_bounded(stream: BinaryIO, *, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
