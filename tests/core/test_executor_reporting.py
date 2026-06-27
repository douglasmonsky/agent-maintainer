"""Tests for command execution and compact reporting helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_maintainer.core import executor as maintainer_executor
from agent_maintainer.models import Check


def test_tool_search_path_prefers_local_virtualenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    monkeypatch.setenv("PATH", "/usr/bin")

    search_path = maintainer_executor.tool_search_path().split(os.pathsep)

    assert search_path[0] == ".venv/bin"
    assert "/usr/bin" in search_path


def test_command_env_disables_bytecode_writes_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_MAINTAINER_WRITE_BYTECODE", raising=False)
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)

    assert maintainer_executor.command_env()["PYTHONDONTWRITEBYTECODE"] == "1"


def test_command_env_adds_local_package_pythonpath(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    package_path = tmp_path / "src" / "agent_maintainer"
    package_path.mkdir(parents=True)
    monkeypatch.setenv("PYTHONPATH", "existing")

    assert maintainer_executor.command_env()["PYTHONPATH"] == f"src{os.pathsep}existing"


def test_missing_requirement_reports_required_path(tmp_path: Path) -> None:
    check = Check("missing", ["true"], frozenset(), required_paths=("missing.py",))

    assert maintainer_executor.missing_requirement(check) == "required path 'missing.py' is absent"


def test_missing_requirement_uses_capability_aware_executable_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maintainer_executor.shutil, "which", lambda *args, **_kwargs: None)
    check = Check("missing", ["missing-tool"], frozenset(), required_executable="missing-tool")

    message = maintainer_executor.missing_requirement(check)

    assert message is not None
    assert "Missing Python package command: missing-tool" in message
    assert "config/dev-lock.txt" in message


def test_optional_skip_reports_configured_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check(
        "import-linter",
        ["lint-imports"],
        frozenset(),
        optional_skip_reason=".importlinter is absent",
    )

    assert maintainer_executor.missing_requirement(check) == (
        "optional skip: .importlinter is absent"
    )


def test_tach_config_skip_reports_configured_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check(
        "tach-config",
        ["python", "-m", "agent_maintainer.checks.tach_config"],
        frozenset(),
        optional_skip_reason="tach.toml is absent",
    )

    assert maintainer_executor.missing_requirement(check) == "optional skip: tach.toml is absent"


def test_workflow_check_skip_reports_configured_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check(
        "zizmor",
        ["zizmor"],
        frozenset(),
        required_executable="zizmor",
        optional_skip_reason=".github/workflows is absent",
    )

    assert maintainer_executor.missing_requirement(check) == (
        "optional skip: .github/workflows is absent"
    )


def test_interrogate_skip_reports_configured_reason(tmp_path: Path) -> None:
    check = Check(
        "interrogate",
        ["interrogate"],
        frozenset(),
        optional_skip_reason="disabled",
    )

    assert maintainer_executor.missing_requirement(check) == "optional skip: disabled"


def test_external_manual_scanner_skip_reports_configured_reason(tmp_path: Path) -> None:
    for check_name in ("osv-scanner", "trivy"):
        check = Check(
            check_name,
            [check_name],
            frozenset(),
            optional_skip_reason="disabled",
        )

        assert maintainer_executor.missing_requirement(check) == "optional skip: disabled"


def test_run_check_writes_skip_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check("pip-audit", ["pip-audit"], frozenset(), optional_skip_reason="disabled")

    result = maintainer_executor.run_check(check, tmp_path / "logs", 5, 200)

    assert result.name == "pip-audit"
    assert result.passed is True
    assert result.output == "disabled"
    assert result.skipped is True
    assert result.command == ("pip-audit",)
    assert result.log_path == str(tmp_path / "logs" / "pip-audit.log")
    assert (tmp_path / "logs" / "pip-audit.log").read_text(encoding="utf-8")


def test_run_check_summarizes_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: list[str]) -> tuple[int, str]:
        assert command == ["tool"]
        return 1, "\n".join(f"line {index}" for index in range(10))

    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    result = maintainer_executor.run_check(
        Check("tool", ["tool"], frozenset()), tmp_path / "logs", 3, 200
    )

    assert result.passed is False
    assert result.command == ("tool",)
    assert result.exit_code == 1
    assert result.log_path == str(tmp_path / "logs" / "tool.log")
    assert "line 0" in result.output
    assert "more lines omitted" in result.output


def test_run_check_records_existing_declared_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "coverage.xml"

    def fake_run(command: list[str]) -> tuple[int, str]:
        assert command == ["pytest"]
        artifact.write_text("<coverage />\n", encoding="utf-8")
        return 0, "ok\n"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    result = maintainer_executor.run_check(
        Check("pytest-coverage", ["pytest"], frozenset(), artifact_paths=("coverage.xml",)),
        tmp_path / "logs",
        3,
        200,
    )

    assert result.passed is True
    assert result.exit_code == 0
    assert result.artifact_paths == ("coverage.xml",)


def test_run_check_creates_log_dir_before_command_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    artifact = Path("logs/pytest-junit.xml")

    def fake_run(command: list[str]) -> tuple[int, str]:
        assert command == ["pytest"]
        assert artifact.parent.is_dir()
        artifact.write_text("<testsuite />\n", encoding="utf-8")
        return 0, "ok\n"

    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    result = maintainer_executor.run_check(
        Check(
            "pytest-coverage",
            ["pytest"],
            frozenset(),
            artifact_paths=("logs/pytest-junit.xml",),
        ),
        Path("logs"),
        3,
        200,
    )

    assert result.passed is True
    assert result.artifact_paths == ("logs/pytest-junit.xml",)
