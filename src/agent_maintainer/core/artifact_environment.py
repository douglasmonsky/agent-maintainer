"""Scoped environment for generated verifier artifacts."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

COVERAGE_FILE_ENV = "COVERAGE_FILE"


@contextlib.contextmanager
def artifact_environment(log_dir: Path) -> Iterator[None]:
    """Scope generated tool artifacts to the verifier log directory."""

    if COVERAGE_FILE_ENV in os.environ:
        yield
        return

    os.environ[COVERAGE_FILE_ENV] = str(log_dir / ".coverage")
    try:
        yield
    finally:
        os.environ.pop(COVERAGE_FILE_ENV, None)
