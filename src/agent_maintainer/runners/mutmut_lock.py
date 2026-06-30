"""Cross-process lock for Mutmut generated artifacts."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

MUTMUT_LOCK_PATH = Path(".verify-logs") / "mutmut.lock"


@contextmanager
def mutmut_run_lock() -> Iterator[None]:
    """Serialize Mutmut runs that share the generated mutants directory."""
    MUTMUT_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MUTMUT_LOCK_PATH.open("a+", encoding="utf-8") as lock_file:
        if fcntl is None:
            yield
            return
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
