"""Bounded filesystem I/O for release evidence manifests."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import ExitStack, suppress
from pathlib import Path
from typing import cast

from agent_run_artifacts import release_evidence as contracts

MAX_MANIFEST_BYTES = 5 * 1024 * 1024
OUTPUT_MODE = 0o644


def read_payload(path: Path) -> dict[str, object]:
    """Read one bounded regular JSON object without following symlinks."""

    metadata = _regular_metadata(path)
    if metadata.st_size > MAX_MANIFEST_BYTES:
        raise contracts.ReleaseEvidenceError(
            f"manifest {path} exceeds byte limit {MAX_MANIFEST_BYTES}"
        )
    raw_payload = _json_payload(path)
    if not isinstance(raw_payload, dict):
        raise contracts.ReleaseEvidenceError(f"manifest {path} must contain an object")
    return cast(dict[str, object], raw_payload)


def write_payload(path: Path, payload: dict[str, object]) -> None:
    """Atomically write one deterministic evidence document."""

    encoded = f"{json.dumps(payload, indent=2, sort_keys=True)}\n"
    try:
        _write_payload(path, encoded)
    except OSError as exc:
        raise contracts.ReleaseEvidenceError(
            f"cannot write release evidence {path}: {exc}"
        ) from exc


def _regular_metadata(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise contracts.ReleaseEvidenceError(f"cannot inspect manifest {path}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise contracts.ReleaseEvidenceError(f"manifest {path} must not be a symlink")
    if not stat.S_ISREG(metadata.st_mode):
        raise contracts.ReleaseEvidenceError(f"manifest {path} must be a regular file")
    return metadata


def _json_payload(path: Path) -> object:
    try:
        return cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise contracts.ReleaseEvidenceError(f"cannot read manifest {path}: {exc}") from exc


def _write_payload(path: Path, encoded: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise contracts.ReleaseEvidenceError(f"output {path} must not be a symlink")
    _atomic_replace(path, encoded)


def _atomic_replace(path: Path, encoded: str) -> None:
    with ExitStack() as cleanup:
        handle = cleanup.enter_context(
            tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            )
        )
        temporary = Path(handle.name)
        cleanup.callback(_remove_temporary, temporary)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.chmod(temporary, OUTPUT_MODE)
        os.replace(temporary, path)


def _remove_temporary(path: Path) -> None:
    with suppress(OSError):
        path.unlink(missing_ok=True)
