"""Tests for standalone helper scripts and guardrail entrypoint."""

from __future__ import annotations

import runpy
import subprocess
import sys
import tomllib

import pytest

from ai_guardrails import cli as guardrail_cli
from ai_guardrails.core import args as guardrail_args
from tests.support.paths import REPO_ROOT

BOOTSTRAP_STATUS = 11
DOCTOR_STATUS = 14
INSTALL_STATUS = 12
VERIFY_STATUS = 13
GUIDANCE_STATUS = 15
INIT_STATUS = 16
UNKNOWN_COMMAND_STATUS = 2


def test_justfile_full_output_recipe_uses_repo_roots() -> None:
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    recipe = justfile.split("verify-full-output:", maxsplit=1)[1].split(
        "clean-verify-logs:",
        maxsplit=1,
    )[0]

    assert "--cov=src/ai_guardrails" in recipe
    assert "--cov=guardrail_lib" not in recipe
    assert "--cov-fail-under=90" in recipe
    assert "--cov-fail-under=80" not in recipe
    assert "radon cc src" not in recipe
    assert "pylint src" not in recipe
    assert "bandit -q -r src" not in recipe


def test_scripted_entrypoints_disable_python_bytecode_writes() -> None:
    pre_commit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")

    assert "env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m ai_guardrails" in pre_commit
    assert 'export PYTHONDONTWRITEBYTECODE := "1"' in justfile


def test_guardrail_main_routes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardrail_cli, "bootstrap", lambda: BOOTSTRAP_STATUS)
    monkeypatch.setattr(guardrail_cli, "doctor_main", lambda args: DOCTOR_STATUS)
    monkeypatch.setattr(guardrail_cli, "guidance_main", lambda args: GUIDANCE_STATUS)
    monkeypatch.setattr(guardrail_cli, "init_main", lambda args: INIT_STATUS)
    monkeypatch.setattr(guardrail_cli, "install", lambda: INSTALL_STATUS)
    monkeypatch.setattr(guardrail_cli, "verify_main", lambda args: VERIFY_STATUS)

    assert guardrail_cli.main(["bootstrap"]) == BOOTSTRAP_STATUS
    assert guardrail_cli.main(["doctor", "--strict"]) == DOCTOR_STATUS
    assert guardrail_cli.main(["guidance", "--check"]) == GUIDANCE_STATUS
    assert guardrail_cli.main(["init", "--track", "core"]) == INIT_STATUS
    assert guardrail_cli.main(["install"]) == INSTALL_STATUS
    assert guardrail_cli.main(["verify", "--profile", "fast"]) == VERIFY_STATUS
    assert guardrail_cli.main(["unknown"]) == UNKNOWN_COMMAND_STATUS


def test_verify_parser_accepts_manual_profile() -> None:
    args = guardrail_args.parse_args(["--profile", "manual"])

    assert args.profile == "manual"


def test_guardrail_package_entrypoint_help() -> None:
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "ai_guardrails", "--help"],
        cwd=REPO_ROOT,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "python -m ai_guardrails doctor" in result.stdout


def test_project_exposes_console_script_entrypoint() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["ai-guardrails"] == "ai_guardrails.cli:console_main"


def test_guardrail_console_script_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(guardrail_cli, "main", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(sys, "argv", ["ai-guardrails", "doctor"])

    assert guardrail_cli.console_main() == 0
    assert calls == [["doctor"]]


def test_guardrail_package_main_module_dispatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    monkeypatch.setattr(guardrail_cli, "main", lambda argv: calls.append(argv) or 0)
    monkeypatch.setattr(sys, "argv", ["python -m ai_guardrails", "doctor"])

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("ai_guardrails", run_name="__main__")

    assert exc_info.value.code == 0
    assert calls == [["doctor"]]
