"""Tests changed-source test intelligence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_maintainer.cli import main as maintainer_main
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.changed import changed_source_paths


def test_changed_source_paths_use_configured_source_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changed source discovery returns configured Python source paths."""

    create_git_repo(tmp_path)
    write_project(tmp_path)
    commit_all(tmp_path)
    (tmp_path / "src/example_pkg/widget.py").write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    paths = changed_source_paths(
        MaintainerConfig(source_roots=("src",), test_roots=("tests",)),
        base_ref="HEAD",
        staged=False,
    )

    assert paths == ("src/example_pkg/widget.py",)


def test_changed_command_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI emits stable JSON report."""

    create_git_repo(tmp_path)
    write_project(tmp_path)
    commit_all(tmp_path)
    (tmp_path / "src/example_pkg/widget.py").write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert maintainer_main(["test-intel", "changed", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_source"] == ["src/example_pkg/widget.py"]
    assert payload["likely_tests"][0]["test_path"] == "tests/test_widget.py"
    assert payload["likely_tests"][0]["confidence"] == "high"


def create_git_repo(path: Path) -> None:
    """Initialize a temp Git repository."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.invalid")
    run_git(path, "config", "user.name", "Agent Maintainer Test")


def write_project(path: Path) -> None:
    """Write minimal Python project fixture."""

    (path / "src/example_pkg").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
source_roots = ["src"]
test_roots = ["tests"]
""".lstrip(),
        encoding="utf-8",
    )
    (path / "src/example_pkg/widget.py").write_text("VALUE = 1\n", encoding="utf-8")
    (path / "tests/test_widget.py").write_text(
        (
            "from example_pkg import widget\n\n\n"
            "def test_widget() -> None:\n"
            "    assert widget.VALUE == 1\n"
        ),
        encoding="utf-8",
    )


def commit_all(path: Path) -> None:
    """Commit all fixture files."""

    run_git(path, "add", "pyproject.toml", "src", "tests")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run Git in temp repository."""

    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
