"""Tests core config path helpers."""

from __future__ import annotations

from agent_maintainer.core.config import normalize_repo_path, path_matches_roots


def test_normalize_repo_path_preserves_dot_directories() -> None:
    """Repository path normalization strips relative prefixes, not dot dirs."""

    assert normalize_repo_path("./.codex/hooks/post_edit.py") == ".codex/hooks/post_edit.py"
    assert normalize_repo_path(".docsync/trace.yml") == ".docsync/trace.yml"


def test_path_matches_roots_preserves_dot_directory_roots() -> None:
    """Configured dot-directory roots match dot-directory paths."""

    assert path_matches_roots(".codex/hooks/post_edit.py", (".codex/hooks",))
    assert path_matches_roots("./.docsync/trace.yml", (".docsync",))
