"""Repository-confined file access for contract inputs and evidence."""

from __future__ import annotations

import os
import stat
from contextlib import ExitStack
from pathlib import Path

from agent_maintainer.contracts.limits import MAX_INPUT_BYTES
from agent_maintainer.contracts.models import ContractError
from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path

READ_CHUNK_BYTES = 65_536


def resolve_confined_path(repo_root: Path, value: str, *, label: str) -> Path:
    """Return a canonical repository-confined path without following the leaf."""

    try:
        relative = validate_repo_path(value, label=label)
    except RepoPathError as exc:
        raise ContractError(str(exc)) from exc
    try:
        root, parent = _resolved_parent(repo_root, relative)
    except OSError as exc:
        raise ContractError(f"{label} path is unavailable") from exc
    if not parent.is_relative_to(root):
        raise ContractError(f"{label} must be repository-relative")
    return parent / Path(relative).name


def _resolved_parent(repo_root: Path, relative: str) -> tuple[Path, Path]:
    root = repo_root.resolve(strict=True)
    parent = (root / relative).parent.resolve(strict=False)
    return root, parent


def read_confined_text(
    repo_root: Path,
    value: str,
    *,
    label: str,
    max_bytes: int = MAX_INPUT_BYTES,
) -> str:
    """Read bounded UTF-8 text from one nonsymlinked regular repository file."""

    path = resolve_confined_path(repo_root, value, label=label)
    expected_metadata = _regular_metadata(path, label=label, value=value, max_bytes=max_bytes)
    payload = _read_regular_file(
        path,
        expected_metadata,
        label=label,
        value=value,
        max_bytes=max_bytes,
    )
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{label} must be UTF-8 text: {value}") from exc


def _regular_metadata(
    path: Path,
    *,
    label: str,
    value: str,
    max_bytes: int,
) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} must be a readable regular file: {value}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ContractError(f"{label} must be a readable regular file: {value}")
    if metadata.st_size > max_bytes:
        raise ContractError(f"{label} is too large: {value}")
    return metadata


def _read_regular_file(
    path: Path,
    expected_metadata: os.stat_result,
    *,
    label: str,
    value: str,
    max_bytes: int,
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ContractError(f"{label} must be a readable regular file: {value}") from exc
    with ExitStack() as stack:
        stack.callback(os.close, descriptor)
        metadata = os.fstat(descriptor)
        _require(
            _same_regular_file(metadata, expected_metadata),
            f"{label} must be a readable regular file: {value}",
        )
        _require(metadata.st_size <= max_bytes, f"{label} is too large: {value}")
        payload = _read_bounded(descriptor, max_bytes=max_bytes)
    _require(len(payload) <= max_bytes, f"{label} is too large: {value}")
    return payload


def _same_regular_file(metadata: os.stat_result, expected: os.stat_result) -> bool:
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_dev == expected.st_dev
        and metadata.st_ino == expected.st_ino
    )


def _read_bounded(descriptor: int, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining:
        chunk = os.read(descriptor, min(READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)
