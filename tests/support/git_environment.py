"""Repository-local Git environment names used by test isolation."""

from __future__ import annotations

from collections.abc import MutableMapping

REPOSITORY_LOCAL_GIT_ENVIRONMENT = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE",
    "GIT_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
)


def remove_repository_local_git_environment(
    environment: MutableMapping[str, str],
) -> None:
    """Remove parent-repository overrides from a test-process environment."""

    for name in REPOSITORY_LOCAL_GIT_ENVIRONMENT:
        environment.pop(name, None)
