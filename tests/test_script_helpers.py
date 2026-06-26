"""Tests for standalone helper scripts and guardrail entrypoint."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import (
    guardrail,
)
from scripts.guardrail_core import args as guardrail_args

BOOTSTRAP_STATUS = 11
DOCTOR_STATUS = 14
INSTALL_STATUS = 12
VERIFY_STATUS = 13
GUIDANCE_STATUS = 15
UNKNOWN_COMMAND_STATUS = 2
DEPENDENCY_FAILURE_STATUS = 7


def test_justfile_full_output_recipe_uses_repo_roots() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    justfile = (repo_root / "justfile").read_text(encoding="utf-8")
    recipe = justfile.split("verify-full-output:", maxsplit=1)[1].split(
        "clean-verify-logs:",
        maxsplit=1,
    )[0]

    assert " --cov=src" not in recipe
    assert "--cov-fail-under=90" in recipe
    assert "--cov-fail-under=80" not in recipe
    assert "radon cc src" not in recipe
    assert "pylint src" not in recipe
    assert "bandit -q -r src" not in recipe


def test_scripted_entrypoints_disable_python_bytecode_writes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pre_commit = (repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    justfile = (repo_root / "justfile").read_text(encoding="utf-8")

    assert "env PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.guardrail" in pre_commit
    assert 'export PYTHONDONTWRITEBYTECODE := "1"' in justfile


def test_guardrail_main_routes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardrail, "bootstrap", lambda: BOOTSTRAP_STATUS)
    monkeypatch.setattr(guardrail, "doctor_main", lambda args: DOCTOR_STATUS)
    monkeypatch.setattr(guardrail, "guidance_main", lambda args: GUIDANCE_STATUS)
    monkeypatch.setattr(guardrail, "install", lambda: INSTALL_STATUS)
    monkeypatch.setattr(guardrail, "verify_main", lambda args: VERIFY_STATUS)

    assert guardrail.main(["bootstrap"]) == BOOTSTRAP_STATUS
    assert guardrail.main(["doctor", "--strict"]) == DOCTOR_STATUS
    assert guardrail.main(["guidance", "--check"]) == GUIDANCE_STATUS
    assert guardrail.main(["install"]) == INSTALL_STATUS
    assert guardrail.main(["verify", "--profile", "fast"]) == VERIFY_STATUS
    assert guardrail.main(["unknown"]) == UNKNOWN_COMMAND_STATUS


def test_verify_parser_accepts_manual_profile() -> None:
    args = guardrail_args.parse_args(["--profile", "manual"])

    assert args.profile == "manual"


def test_guardrail_file_entrypoint_help_remains_supported() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(  # nosec B603
        ["python3", "scripts/guardrail.py", "--help"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "python -m scripts.guardrail doctor" in result.stdout


def test_guardrail_install_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert guardrail.install_pre_commit(tmp_path) == 0

    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(guardrail, "find_pre_commit", lambda repo_root: None)
    assert guardrail.install_pre_commit(tmp_path) == 1

    dependency_file = tmp_path / "config" / "dev-dependencies.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(guardrail.subprocess, "run", fake_run)
    assert guardrail.install_dependencies(tmp_path, python_path) == 0
    assert calls[0][-2:] == ["-r", "config/dev-dependencies.txt"]

    (tmp_path / "config" / "dev-lock.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
    calls.clear()
    assert guardrail.install_dependencies(tmp_path, python_path) == 0
    assert calls[0][-2:] == ["-r", "config/dev-lock.txt"]


def test_guardrail_bootstrap_and_virtualenv_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    monkeypatch.setattr(guardrail.shutil, "which", lambda name: "/usr/bin/python3")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        python_path.parent.mkdir(parents=True)
        python_path.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(guardrail.subprocess, "run", fake_run)

    assert guardrail.ensure_virtualenv(tmp_path) == python_path

    monkeypatch.setattr(guardrail, "ensure_virtualenv", lambda repo_root: python_path)
    monkeypatch.setattr(guardrail, "install_dependencies", lambda repo_root, path: 0)
    monkeypatch.setattr(guardrail, "install", lambda: 0)
    assert guardrail.bootstrap() == 0


def test_guardrail_bootstrap_failure_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(guardrail, "ensure_virtualenv", lambda repo_root: None)
    assert guardrail.bootstrap() == 1

    python_path = tmp_path / ".venv" / "bin" / "python"
    monkeypatch.setattr(guardrail, "ensure_virtualenv", lambda repo_root: python_path)
    monkeypatch.setattr(
        guardrail,
        "install_dependencies",
        lambda repo_root, path: DEPENDENCY_FAILURE_STATUS,
    )
    assert guardrail.bootstrap() == DEPENDENCY_FAILURE_STATUS


def test_guardrail_virtualenv_failure_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    existing = tmp_path / ".venv" / "bin" / "python"
    existing.parent.mkdir(parents=True)
    existing.write_text("", encoding="utf-8")
    assert guardrail.ensure_virtualenv(tmp_path) == existing

    missing_python_root = tmp_path / "missing-python"
    monkeypatch.setattr(guardrail.shutil, "which", lambda name: None)
    assert guardrail.ensure_virtualenv(missing_python_root) is None
    assert "python3 command not found" in capsys.readouterr().err

    failed_venv_root = tmp_path / "failed-venv"
    monkeypatch.setattr(guardrail.shutil, "which", lambda name: "/usr/bin/python3")
    monkeypatch.setattr(
        guardrail.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, "", ""),
    )
    assert guardrail.ensure_virtualenv(failed_venv_root) is None


def test_guardrail_dependency_install_requires_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"

    assert guardrail.install_dependencies(tmp_path, python_path) == 1
    assert "dev-lock.txt or config/dev-dependencies.txt" in capsys.readouterr().err


def test_guardrail_dependency_install_explains_python_package_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dependency_file = tmp_path / "config" / "dev-lock.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest==9.1.1\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        guardrail.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )

    assert guardrail.install_dependencies(tmp_path, python_path) == 0

    output = capsys.readouterr().out
    assert "Installing Python package guardrail tools" in output
    assert "External binaries, GitHub-only tools, and manual optional tools" in output


def test_guardrail_reports_codex_hooks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")

    guardrail.report_codex_hooks(tmp_path)

    assert "Codex hooks are configured" in capsys.readouterr().out
