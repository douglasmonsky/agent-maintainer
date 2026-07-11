"""POSIX advisory lock for Mutmut generated artifacts."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

DIAGNOSTIC_ARTIFACTS_DIR_ENV = "AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"
DEFAULT_DIAGNOSTIC_ARTIFACTS_DIR = Path(".verify-logs")
MUTMUT_LOCK_NAME = "mutmut.lock"


@contextmanager
def mutmut_run_lock() -> Generator[None, None, None]:
    """Serialize Mutmut runs that share the generated mutants directory."""

    lock_path = mutmut_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is None:
            yield
            return
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def mutmut_lock_path() -> Path:
    """Return lock path inside the active diagnostic artifact directory."""

    artifact_dir = os.environ.get(DIAGNOSTIC_ARTIFACTS_DIR_ENV)
    if artifact_dir:
        return Path(artifact_dir) / MUTMUT_LOCK_NAME
    return DEFAULT_DIAGNOSTIC_ARTIFACTS_DIR / MUTMUT_LOCK_NAME
