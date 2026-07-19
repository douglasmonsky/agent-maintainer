"""Atomic repository-confined writes for generated contract baselines."""

from __future__ import annotations

import os
import stat
import tempfile
from contextlib import ExitStack
from pathlib import Path

from agent_maintainer.contracts import paths as contract_paths
from agent_maintainer.contracts.models import BaselineError

PRIVATE_FILE_MODE = 0o600


def write_atomic(repo_root: Path, path: Path, content: str) -> None:
    """Atomically replace one exact confined nonsymlinked baseline path."""

    destination = _prepare_destination(repo_root, path)
    try:
        _replace(repo_root, path, destination, content)
    except OSError as exc:
        raise BaselineError("could not atomically write contract baseline") from exc


def _replace(repo_root: Path, path: Path, destination: Path, content: str) -> None:
    with ExitStack() as cleanup:
        temporary_name = _write_temporary(destination, content)
        cleanup.callback(Path(temporary_name).unlink, missing_ok=True)
        _revalidate_destination(repo_root, path, destination)
        os.replace(temporary_name, destination)


def _prepare_destination(repo_root: Path, path: Path) -> Path:
    try:
        destination = contract_paths.resolve_confined_path(
            repo_root,
            path.as_posix(),
            label="contract baseline",
        )
    except ValueError as exc:
        raise BaselineError(str(exc)) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        metadata = destination.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as exc:
        raise BaselineError("contract baseline destination is unavailable") from exc
    if metadata is not None and not stat.S_ISREG(metadata.st_mode):
        raise BaselineError("contract baseline destination must be a regular file")
    return destination


def _write_temporary(destination: Path, content: str) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    ) as temporary:
        os.chmod(temporary.name, PRIVATE_FILE_MODE)
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        return temporary.name


def _revalidate_destination(repo_root: Path, path: Path, destination: Path) -> None:
    try:
        revalidated = contract_paths.resolve_confined_path(
            repo_root,
            path.as_posix(),
            label="contract baseline",
        )
    except ValueError as exc:
        raise BaselineError(str(exc)) from exc
    if revalidated != destination:
        raise BaselineError("contract baseline destination changed during write")
