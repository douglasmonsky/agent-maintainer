"""Tests for doctor environment diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.doctor.support import environment as doctor_environment
from agent_maintainer.doctor.support import models as doctor_models

GIT_FATAL_EXIT = 128


def test_repo_root_missing_paths(tmp_path: Path) -> None:
    result = doctor_environment.check_repo_root(tmp_path)

    assert result.status == doctor_models.ERROR
    assert result.state == doctor_models.MISSING
    assert ".git" in result.message
    assert "src/agent_maintainer/__main__.py" not in result.message


def test_repo_root_accepts_configured_consumer_repo(tmp_path: Path) -> None:
    """Doctor supports repos that consume agent-maintainer as tooling."""

    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        "[tool.agent_maintainer]\n",
        encoding="utf-8",
    )

    result = doctor_environment.check_repo_root(tmp_path)

    assert result.status == doctor_models.OK


def test_repo_root_missing_pyproject(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    package_path = tmp_path / "src" / "agent_maintainer"
    package_path.mkdir(parents=True)
    (package_path / "__main__.py").write_text("", encoding="utf-8")

    result = doctor_environment.check_repo_root(tmp_path)

    assert result.status == doctor_models.WARNING
    assert result.state == doctor_models.MISSING
    assert "pyproject.toml" in result.message


def test_virtualenv_prefers_dot_venv_python(tmp_path: Path) -> None:
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    fallback_python = tmp_path / "venv" / "bin" / "python"
    fallback_python.parent.mkdir(parents=True)
    fallback_python.write_text("", encoding="utf-8")

    result = doctor_environment.check_virtualenv(tmp_path)

    assert result.status == doctor_models.OK
    assert result.message == ".venv/bin/python"


def test_git_state_reports_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        ["git"],
        GIT_FATAL_EXIT,
        stdout="",
        stderr="fatal: not a git repository",
    )

    def git_path(_name: str) -> str:
        return "/usr/bin/git"

    def run_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed

    monkeypatch.setattr(doctor_environment.shutil, "which", git_path)
    monkeypatch.setattr(doctor_environment.subprocess, "run", run_git)

    result = doctor_environment.check_git_state(tmp_path)

    assert result.status == doctor_models.WARNING
    assert result.message == "fatal: not a git repository"


def test_git_state_ahead_dirty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout="## main...origin/main [ahead 1]\n M README.md\n?? scratch.txt\n",
        stderr="",
    )

    def git_path(_name: str) -> str:
        return "/usr/bin/git"

    def run_git(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed

    monkeypatch.setattr(doctor_environment.shutil, "which", git_path)
    monkeypatch.setattr(doctor_environment.subprocess, "run", run_git)

    result = doctor_environment.check_git_state(tmp_path)

    assert result.status == doctor_models.WARNING
    assert result.message == "main...origin/main [ahead 1]; 2 changed path(s)"


def test_git_state_warns_when_upstream_is_gone() -> None:
    """Deleted tracking branches are actionable instead of healthy."""

    result = doctor_environment.git_status_result(
        "## feature...origin/feature [gone]\n",
    )

    assert result.status == doctor_models.WARNING
    assert result.message == "feature...origin/feature [gone]"
    assert result.hint == "Set a new upstream or unset the stale tracking branch."
