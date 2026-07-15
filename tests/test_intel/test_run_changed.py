"""Tests for executing tests affected by staged Python changes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.cli import main as maintainer_main
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.run_changed import run_selected_tests, selected_test_paths


def test_source_change_selects_likely_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A staged source edit runs its mapped test file."""

    create_project(tmp_path)
    (tmp_path / "src/example/widget.py").write_text("VALUE = 2\n", encoding="utf-8")
    run_git(tmp_path, "add", "src/example/widget.py")
    monkeypatch.chdir(tmp_path)

    selected = selected_test_paths(config(), base_ref="HEAD", staged=True, repo_root=tmp_path)

    assert selected == ("tests/test_widget.py",)


def test_test_only_change_runs_changed_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directly edited test is not lost when no source file changed."""

    create_project(tmp_path)
    test_path = tmp_path / "tests/test_widget.py"
    test_path.write_text(f"{test_path.read_text()}\n# staged\n", encoding="utf-8")
    run_git(tmp_path, "add", "tests/test_widget.py")
    monkeypatch.chdir(tmp_path)

    selected = selected_test_paths(config(), base_ref="HEAD", staged=True, repo_root=tmp_path)

    assert selected == ("tests/test_widget.py",)


def test_documentation_only_change_selects_no_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Documentation commits avoid starting pytest."""

    create_project(tmp_path)
    (tmp_path / "README.md").write_text("updated\n", encoding="utf-8")
    run_git(tmp_path, "add", "README.md")
    monkeypatch.chdir(tmp_path)

    selected = selected_test_paths(config(), base_ref="HEAD", staged=True, repo_root=tmp_path)

    assert selected == ()


def test_run_changed_cli_skips_pytest_for_documentation_only_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The installed command exposes the no-test fast path."""

    create_project(tmp_path)
    (tmp_path / "README.md").write_text("updated\n", encoding="utf-8")
    run_git(tmp_path, "add", "README.md")
    monkeypatch.chdir(tmp_path)

    status = maintainer_main(["test-intel", "run-changed", "--base-ref", "HEAD", "--staged"])

    assert status == 0
    assert capsys.readouterr().out == "PASS: no affected Python tests\n"


def test_runner_executes_selected_tests_without_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commit-time tests stay focused and leave coverage to the pre-push gate."""

    commands: list[list[str]] = []
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    def record_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("agent_maintainer.test_intel.run_changed.subprocess.run", record_run)

    status = run_selected_tests(("tests/test_widget.py",), repo_root=tmp_path)

    assert status == 0
    assert commands == [
        [
            ".venv/bin/python",
            "-m",
            "pytest",
            "-q",
            "--tb=short",
            "--disable-warnings",
            "-p",
            "no:tach",
            "tests/test_widget.py",
        ]
    ]
    assert not any(argument.startswith("--cov") for argument in commands[0])


def config() -> MaintainerConfig:
    """Return the minimal project classification config."""

    return MaintainerConfig(source_roots=("src",), test_roots=("tests",))


def create_project(path: Path) -> None:
    """Create and commit a minimal mapped source/test project."""

    run_git(path, "init")
    run_git(path, "config", "user.email", "agent-maintainer@example.invalid")
    run_git(path, "config", "user.name", "Agent Maintainer Test")
    (path / "src/example").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "src/example/widget.py").write_text("VALUE = 1\n", encoding="utf-8")
    (path / "tests/test_widget.py").write_text(
        (
            "from example import widget\n\n\n"
            "def test_widget() -> None:\n"
            "    assert widget.VALUE == 1\n"
        ),
        encoding="utf-8",
    )
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    run_git(path, "add", "src", "tests", "README.md")
    run_git(path, "commit", "-m", "initial")


def run_git(path: Path, *args: str) -> None:
    """Run one fixture Git command."""

    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
