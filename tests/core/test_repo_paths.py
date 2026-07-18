"""Repository-relative path validation tests."""

from __future__ import annotations

import pytest

from agent_maintainer.core.repo_paths import RepoPathError, validate_repo_path


@pytest.mark.parametrize(
    "path",
    (
        "tach.toml",
        "src/agent_maintainer/core/repo_paths.py",
        ".github/workflows/verify.yml",
    ),
)
def test_validate_repo_path_accepts_normalized_relative_paths(path: str) -> None:
    assert validate_repo_path(path, label="changed path") == path


@pytest.mark.parametrize(
    "path",
    (
        "",
        "/root",
        "./src/app.py",
        "src\\app.py",
        "src//app.py",
        "src/./app.py",
        "src/../app.py",
        "src/\0app.py",
    ),
)
def test_validate_repo_path_rejects_unsafe_or_ambiguous_paths(path: str) -> None:
    with pytest.raises(RepoPathError, match="changed path"):
        validate_repo_path(path, label="changed path")
