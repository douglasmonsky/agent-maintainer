"""Scoped environment for generated verifier artifacts."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Generator
from pathlib import Path

COVERAGE_FILE_ENV = "COVERAGE_FILE"
DIAGNOSTIC_ARTIFACTS_DIR_ENV = "AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"


@contextlib.contextmanager
def artifact_environment(log_dir: Path) -> Generator[None, None, None]:
    """Scope generated tool artifacts to the verifier log directory."""

    previous_coverage_file = os.environ.get(COVERAGE_FILE_ENV)
    previous_diagnostics_dir = os.environ.get(DIAGNOSTIC_ARTIFACTS_DIR_ENV)

    if previous_coverage_file is None:
        os.environ[COVERAGE_FILE_ENV] = str(log_dir / ".coverage")
    os.environ[DIAGNOSTIC_ARTIFACTS_DIR_ENV] = str(log_dir)
    try:
        yield
    finally:
        restore_environment_value(COVERAGE_FILE_ENV, previous_coverage_file)
        restore_environment_value(DIAGNOSTIC_ARTIFACTS_DIR_ENV, previous_diagnostics_dir)


def restore_environment_value(name: str, value: str | None) -> None:
    """Restore one environment variable after scoped artifact execution."""

    if value is None:
        os.environ.pop(name, None)
        return
    os.environ[name] = value
