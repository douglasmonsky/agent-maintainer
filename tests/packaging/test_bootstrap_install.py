"""Tests bootstrap install and virtualenv behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.core import bootstrap as maintainer_bootstrap
from tests.support.callbacks import completed_process_callback, constant_callback

INSTALL_STATUS = 12
DEPENDENCY_FAILURE_STATUS = 7


def test_maintainer_install_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert maintainer_bootstrap.install_pre_commit(tmp_path) == 0

    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(maintainer_bootstrap, "find_pre_commit", constant_callback(None))
    assert maintainer_bootstrap.install_pre_commit(tmp_path) == 1

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "example"\n', encoding="utf-8")
    (tmp_path / "src" / "agent_maintainer").mkdir(parents=True)
    (tmp_path / "src" / "agent_maintainer" / "__init__.py").write_text("", encoding="utf-8")
    dependency_file = tmp_path / "config" / "dev-dependencies.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    calls: list[list[str]] = []
    repairs: list[tuple[Path, Path]] = []
    links: list[tuple[Path, Path]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    def record_repair(repo_root: Path, python_path_arg: Path) -> None:
        repairs.append((repo_root, python_path_arg))

    def record_link(repo_root: Path, python_path_arg: Path) -> None:
        links.append((repo_root, python_path_arg))

    monkeypatch.setattr(maintainer_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(
        maintainer_bootstrap,
        "repair_pth_visibility",
        record_repair,
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "ensure_editable_package_link",
        record_link,
    )
    assert maintainer_bootstrap.install_dependencies(tmp_path, python_path) == 0
    assert calls[0][-2:] == ["-r", "config/dev-dependencies.txt"]
    assert calls[1][-4:] == ["install", "-e", ".", "--no-deps"]
    assert repairs == [(tmp_path, python_path), (tmp_path, python_path)]
    assert links == [(tmp_path, python_path)]

    (tmp_path / "config" / "dev-lock.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
    calls.clear()
    repairs.clear()
    links.clear()
    assert maintainer_bootstrap.install_dependencies(tmp_path, python_path) == 0
    assert calls[0][-2:] == ["-r", "config/dev-lock.txt"]
    assert calls[1][-4:] == ["install", "-e", ".", "--no-deps"]
    assert repairs == [(tmp_path, python_path), (tmp_path, python_path)]
    assert links == [(tmp_path, python_path)]


def test_maintainer_dependency_install_returns_pip_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependency_file = tmp_path / "config" / "dev-dependencies.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"

    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        completed_process_callback(DEPENDENCY_FAILURE_STATUS),
    )

    assert (
        maintainer_bootstrap.install_dependencies(tmp_path, python_path)
        == DEPENDENCY_FAILURE_STATUS
    )


def test_maintainer_bootstrap_and_virtualenv_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    monkeypatch.setattr(
        maintainer_bootstrap.shutil,
        "which",
        constant_callback("/usr/bin/python3"),
    )

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        python_path.parent.mkdir(parents=True)
        python_path.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(maintainer_bootstrap.subprocess, "run", fake_run)

    assert maintainer_bootstrap.ensure_virtualenv(tmp_path) == python_path

    monkeypatch.setattr(
        maintainer_bootstrap,
        "ensure_virtualenv",
        constant_callback(python_path),
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "install_dependencies",
        constant_callback(0),
    )
    assert maintainer_bootstrap.bootstrap() == 0


def test_maintainer_bootstrap_failure_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(maintainer_bootstrap, "ensure_virtualenv", constant_callback(None))
    assert maintainer_bootstrap.bootstrap() == 1

    python_path = tmp_path / ".venv" / "bin" / "python"
    monkeypatch.setattr(
        maintainer_bootstrap,
        "ensure_virtualenv",
        constant_callback(python_path),
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "install_dependencies",
        constant_callback(DEPENDENCY_FAILURE_STATUS),
    )
    assert maintainer_bootstrap.bootstrap() == DEPENDENCY_FAILURE_STATUS


def test_maintainer_virtualenv_failure_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    existing = tmp_path / ".venv" / "bin" / "python"
    existing.parent.mkdir(parents=True)
    existing.write_text("", encoding="utf-8")
    assert maintainer_bootstrap.ensure_virtualenv(tmp_path) == existing

    missing_python_root = tmp_path / "missing-python"
    monkeypatch.setattr(maintainer_bootstrap.shutil, "which", constant_callback(None))
    assert maintainer_bootstrap.ensure_virtualenv(missing_python_root) is None
    assert "python3 command not found" in capsys.readouterr().err

    failed_venv_root = tmp_path / "failed-venv"
    monkeypatch.setattr(
        maintainer_bootstrap.shutil,
        "which",
        constant_callback("/usr/bin/python3"),
    )
    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        completed_process_callback(1),
    )
    assert maintainer_bootstrap.ensure_virtualenv(failed_venv_root) is None


def test_maintainer_source_checkout_dependency_install_requires_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "src" / "agent_maintainer").mkdir(parents=True)
    (tmp_path / "src" / "agent_maintainer" / "__init__.py").write_text("", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"

    assert maintainer_bootstrap.install_dependencies(tmp_path, python_path) == 1

    assert "dev-lock.txt or config/dev-dependencies.txt" in capsys.readouterr().err


def test_maintainer_consumer_dependency_install_skips_missing_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"

    assert maintainer_bootstrap.install_dependencies(tmp_path, python_path) == 0

    output = capsys.readouterr().out
    assert "leaving consumer repository dependencies unchanged" in output


def test_maintainer_consumer_editable_install_does_not_install_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "consumer"\n', encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    calls: list[list[str]] = []

    def record_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        record_run,
    )

    assert maintainer_bootstrap.install_editable_package(tmp_path, python_path) == 0

    assert calls == []


def test_maintainer_install_pre_commit_success_and_path_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(
        maintainer_bootstrap,
        "find_pre_commit",
        constant_callback("pre-commit"),
    )
    commands: list[list[str]] = []

    def record_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(maintainer_bootstrap.subprocess, "run", record_run)

    assert maintainer_bootstrap.install_pre_commit(tmp_path) == 0
    assert commands == [
        ["pre-commit", "install", "--hook-type", "pre-commit", "--hook-type", "pre-push"]
    ]


def test_maintainer_find_pre_commit_uses_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        maintainer_bootstrap.shutil,
        "which",
        constant_callback("/bin/pre-commit"),
    )

    assert maintainer_bootstrap.find_pre_commit(tmp_path) == "/bin/pre-commit"


def test_maintainer_dependency_install_explains_python_package_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "src" / "agent_maintainer").mkdir(parents=True)
    (tmp_path / "src" / "agent_maintainer" / "__init__.py").write_text("", encoding="utf-8")
    dependency_file = tmp_path / "config" / "dev-lock.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest==9.1.1\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        completed_process_callback(0),
    )

    assert maintainer_bootstrap.install_dependencies(tmp_path, python_path) == 0

    output = capsys.readouterr().out
    assert "Installing Python package Agent Maintainer tools" in output
    assert "External binaries, GitHub-only tools, and manual optional tools" in output
