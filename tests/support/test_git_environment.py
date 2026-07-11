"""Tests for repository-local Git environment isolation."""

from __future__ import annotations

import os

from tests.support.git_environment import (
    REPOSITORY_LOCAL_GIT_ENVIRONMENT,
    remove_repository_local_git_environment,
)


def test_parent_repository_git_environment_is_not_visible_to_tests() -> None:
    """Synthetic repositories must not inherit a parent hook's Git index."""

    inherited = [name for name in REPOSITORY_LOCAL_GIT_ENVIRONMENT if name in os.environ]

    assert inherited == []


def test_environment_isolation_preserves_non_repository_git_settings() -> None:
    """Pager and unrelated process settings remain available to tests."""

    environment = {
        "GIT_INDEX_FILE": "/parent/index",
        "GIT_PAGER": "cat",
        "PATH": "/usr/bin",
    }

    remove_repository_local_git_environment(environment)

    assert environment == {"GIT_PAGER": "cat", "PATH": "/usr/bin"}
