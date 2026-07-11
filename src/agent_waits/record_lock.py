"""Short-lived cross-process locks for durable wait record transitions."""

from __future__ import annotations

import contextlib
import hashlib
import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Final

LOCK_WAIT_SECONDS: Final = 5.0
LOCK_STALE_SECONDS: Final = 30.0
LOCK_POLL_SECONDS: Final = 0.05


@contextlib.contextmanager
def wait_record_lock(
    waits_dir: Path,
    wait_id: str,
    *,
    wait_seconds: float = LOCK_WAIT_SECONDS,
) -> Generator[None, None, None]:
    """Serialize one brief read-modify-write transition for a wait record."""

    waits_dir.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path(waits_dir, wait_id)
    deadline = time.monotonic() + wait_seconds
    acquired = False
    while not acquired:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            _break_stale_lock(lock_path)
            if time.monotonic() >= deadline:
                raise TimeoutError("wait record transition is already in progress") from None
            time.sleep(LOCK_POLL_SECONDS)
            continue
        os.close(descriptor)
        acquired = True
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.unlink()


def _lock_path(waits_dir: Path, wait_id: str) -> Path:
    digest = hashlib.sha256(wait_id.encode("utf-8")).hexdigest()
    return waits_dir / f".{digest}.lock"


def _break_stale_lock(lock_path: Path) -> None:
    with contextlib.suppress(OSError):
        if time.time() - lock_path.stat().st_mtime > LOCK_STALE_SECONDS:
            lock_path.unlink()
