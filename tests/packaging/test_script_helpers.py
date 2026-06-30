"""Tests for standalone helper scripts and maintainer entrypoint."""

from __future__ import annotations

import runpy
import subprocess
import sys
import tomllib

import pytest

from agent_maintainer import cli as maintainer_cli
from agent_maintainer.core import args as maintainer_args
from tests.support.paths import REPO_ROOT

BOOTSTRAP_STATUS = 11
DOCTOR_STATUS = 14
INSTALL_STATUS = 12
VERIFY_STATUS = 13
GUIDANCE_STATUS = 15
INIT_STATUS = 16
RATCHET_STATUS = 17
UNKNOWN_COMMAND_STATUS = 2


def test_justfile_full_output_recipe_uses_repo_roots() -> None:
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    recipe = justfile.split("verify-full-output:", maxsplit=1)[1].split(
        "clean-verify-logs:",
        maxsplit=1,
    )[0]

    assert "--cov=src/agent_maintainer" in recipe
    assert "--cov=" + "maintainer_" + "lib" not in recipe
    assert "--cov-fail-under=90" in recipe
    assert "--cov-fail-under=80" not in recipe
    assert "radon cc src" not in recipe
    assert "pylint src" not in recipe
    assert "bandit -q -r src" not in recipe


def test_scripted_entrypoints_disable_python_bytecode_writes() -> None:
    pre_commit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")

    assert "env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m agent_maintainer" in pre_commit
    assert 'export PYTHONDONTWRITEBYTECODE := "1"' in justfile


def test_maintainer_main_routes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(maintainer_cli, "bootstrap", lambda: BOOTSTRAP_STATUS)
    monkeypatch.setattr(maintainer_cli, "doctor_main", lambda args: DOCTOR_STATUS)
    monkeypatch.setattr(maintainer_cli, "guidance_main", lambda args: GUIDANCE_STATUS)
    monkeypatch.setattr(maintainer_cli, "init_main", lambda args: INIT_STATUS)
    monkeypatch.setattr(maintainer_cli, "install", lambda: INSTALL_STATUS)
    monkeypatch.setattr(maintainer_cli, "ratchet_command", lambda args: RATCHET_STATUS)
    monkeypatch.setattr(maintainer_cli, "verify_main", lambda args: VERIFY_STATUS)

    assert maintainer_cli.main(["bootstrap"]) == BOOTSTRAP_STATUS
    assert maintainer_cli.main(["doctor", "--strict"]) == DOCTOR_STATUS
    assert maintainer_cli.main(["guidance", "--check"]) == GUIDANCE_STATUS
    assert maintainer_cli.main(["init", "--track", "core"]) == INIT_STATUS
    assert maintainer_cli.main(["install"]) == INSTALL_STATUS
    assert maintainer_cli.main(["ratchet", "status"]) == RATCHET_STATUS
    assert maintainer_cli.main(["verify", "--profile", "fast"]) == VERIFY_STATUS
    assert maintainer_cli.main(["unknown"]) == UNKNOWN_COMMAND_STATUS


def test_verify_parser_accepts_manual_profile() -> None:
    args = maintainer_args.parse_args(["--profile", "manual"])

    assert args.profile == "manual"


def test_maintainer_package_entrypoint_help() -> None:
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "agent_maintainer", "--help"],
        cwd=REPO_ROOT,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "python -m agent_maintainer doctor" in result.stdout
    assert "python -m agent_maintainer <command> [options]" in result.stdout
    assert "Core commands:\n" in result.stdout
    assert "Agent repair commands:\n" in result.stdout


def test_project_exposes_console_script_entrypoint() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert (
        pyproject["project"]["scripts"]["agent-maintainer"] == "agent_maintainer.cli:console_main"
    )


def test_maintainer_console_script_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(maintainer_cli, "main", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(sys, "argv", ["agent-maintainer", "doctor"])

    assert maintainer_cli.console_main() == 0
    assert calls == [["doctor"]]


def test_maintainer_package_main_module_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(maintainer_cli, "main", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(sys, "argv", ["python -m agent_maintainer", "doctor"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("agent_maintainer", run_name="__main__")

    assert exc_info.value.code == 0
    assert calls == [["doctor"]]
