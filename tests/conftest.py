"""Global test-process isolation hooks."""

from __future__ import annotations

import os

import pytest

from tests.support.git_environment import remove_repository_local_git_environment


def pytest_configure(config: pytest.Config) -> None:
    """Detach tests from repository-local Git overrides inherited from hooks."""

    del config
    remove_repository_local_git_environment(os.environ)
