"""Tests bounded Git diff context."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import agent_context.reading.diff as diff_module
import agent_context.reading.diff_classify as diff_classify_module
import agent_context.reading.diff_git as diff_git_module
import agent_maintainer.context.reading.diff as old_diff
import agent_maintainer.context.reading.diff_classify as old_diff_classify
import agent_maintainer.context.reading.diff_git as old_diff_git
from agent_context.reading.diff import DiffRequest, render_diff
from agent_maintainer.context import cli as context_cli

LIMIT_ONE_PATH = 1


def test_old_context_diff_imports_delegate_to_agent_context() -> None:
    """Old diff reader import path delegates to extracted package."""

    assert old_diff.DEFAULT_DIFF_HUNKS == diff_module.DEFAULT_DIFF_HUNKS
    assert old_diff.DiffResult is diff_module.DiffResult
    assert old_diff.render_diff is diff_module.render_diff
    assert old_diff.render_patch is diff_module.render_patch
    assert old_diff.render_name_only is diff_module.render_name_only
    assert old_diff.render_diff_summary is diff_module.render_diff_summary


def test_old_context_diff_classify_imports_delegate_to_agent_context() -> None:
    """Old diff classification import path delegates to extracted package."""

    assert old_diff_classify.DOC_SUFFIXES == diff_classify_module.DOC_SUFFIXES
    assert old_diff_classify.GENERATED_PARTS == diff_classify_module.GENERATED_PARTS
    assert old_diff_classify.LOCK_FILE_NAMES == diff_classify_module.LOCK_FILE_NAMES
    assert old_diff_classify.is_python_path is diff_classify_module.is_python_path
    assert old_diff_classify.is_test_path is diff_classify_module.is_test_path
    assert old_diff_classify.is_docs_path is diff_classify_module.is_docs_path


def test_old_context_diff_git_imports_delegate_to_agent_context() -> None:
    """Old Git diff import path delegates to extracted package."""

    assert old_diff_git.DEFAULT_DIFF_CONTEXT_LINES == (diff_git_module.DEFAULT_DIFF_CONTEXT_LINES)
    assert old_diff_git.DEFAULT_DIFF_PATH_LIMIT == diff_git_module.DEFAULT_DIFF_PATH_LIMIT
    assert old_diff_git.DiffRequest is diff_git_module.DiffRequest
    assert old_diff_git.git_diff is diff_git_module.git_diff
    assert old_diff_git.changed_paths is diff_git_module.changed_paths
    assert old_diff_git.run_git is diff_git_module.run_git


def test_diff_summary_includes_categories(tmp_path: Path) -> None:
    """Diff summary includes changed path categories and expansion commands."""

    repo = init_repo(tmp_path)
    modify_standard_files(repo)

    result = render_diff(DiffRequest(repo=repo, summary=True))

    assert "files changed: 4" in result.text
    assert "Python files: 2" in result.text
    assert "test files: 1" in result.text
    assert "docs files: 1" in result.text
    assert "generated/lock files: 1" in result.text
    assert "expansion commands:" in result.text


def test_name_only_is_limited(tmp_path: Path) -> None:
    """Name-only output reports omitted path count."""

    repo = init_repo(tmp_path)
    modify_standard_files(repo)

    result = render_diff(DiffRequest(repo=repo, name_only=True, limit=LIMIT_ONE_PATH))

    assert "shown paths: 1" in result.text
    assert result.omitted_paths > 0


def test_path_specific_diff_only_shows_requested_path(tmp_path: Path) -> None:
    """Path-specific diff limits patch to requested path."""

    repo = init_repo(tmp_path)
    modify_standard_files(repo)

    result = render_diff(DiffRequest(repo=repo, path="src/pkg/app.py"))

    assert "src/pkg/app.py" in result.text
    assert "tests/test_app.py" not in result.text


def test_staged_mode_uses_cached_diff(tmp_path: Path) -> None:
    """Staged mode reads cached changes."""

    repo = init_repo(tmp_path)
    write_file(repo / "src/pkg/app.py", "import os\nvalue = 1\n")
    run_git(repo, "add", "src/pkg/app.py")

    result = render_diff(DiffRequest(repo=repo, staged=True, name_only=True))

    assert "src/pkg/app.py" in result.text


def test_diff_cli_summary_uses_current_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Diff subcommand uses current repository."""

    repo = init_repo(tmp_path)
    modify_standard_files(repo)
    monkeypatch.chdir(repo)

    assert context_cli.main(["diff", "--summary"]) == 0

    assert "Diff summary" in capsys.readouterr().out


def init_repo(tmp_path: Path) -> Path:
    """Create a small Git repository fixture."""

    repo = tmp_path / "repo"
    write_file(repo / "src/pkg/app.py", "value = 1\n")
    write_file(repo / "tests/test_app.py", "def test_app():\n    assert True\n# changed\n")
    write_file(repo / "docs/guide.md", "# Guide\n")
    write_file(repo / "package-lock.json", "{}\n")
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test User")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "initial")
    return repo


def modify_standard_files(repo: Path) -> None:
    """Modify standard fixture files."""

    write_file(repo / "src/pkg/app.py", "import os\nvalue = 1\n")
    write_file(repo / "tests/test_app.py", "def test_app():\n    assert True\n")
    write_file(repo / "docs/guide.md", "# Guide\nMore\n")
    write_file(repo / "package-lock.json", '{"lockfileVersion": 3}\n')


def write_file(path: Path, text: str) -> None:
    """Write text file and parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_git(repo: Path, *args: str) -> None:
    """Run Git command in repo fixture."""

    subprocess.run(("git", *args), cwd=repo, check=True, capture_output=True, text=True)
