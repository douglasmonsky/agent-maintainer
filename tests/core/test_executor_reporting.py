"""Tests for command execution and compact reporting helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from agent_maintainer.core import command_run as maintainer_command_run
from agent_maintainer.core import executor as maintainer_executor
from agent_maintainer.models import (
    SKIP_STATUS_DISABLED,
    SKIP_STATUS_MISSING_OPTIONAL,
    SKIP_STATUS_NOT_APPLICABLE,
    SKIP_STATUS_REQUIRED,
    SKIP_STATUS_UNSAFE_CONFIG,
    Check,
)
from tests.support.callbacks import constant_callback


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


def test_run_command_bounds_stdout_without_labelling_simple_output() -> None:
    """Bounded command execution caps output while preserving simple stdout."""

    exit_code, output = maintainer_executor.run_command(
        [sys.executable, "-c", "print('x' * 2000)"],
        timeout_seconds=10,
        output_limit_chars=100,
    )

    assert exit_code == 0
    assert output.startswith("x" * 100)
    assert "## stdout" not in output
    assert "stream truncated" in output


def test_run_command_returns_timeout_result() -> None:
    """A hung command returns a compact timeout result instead of blocking."""

    exit_code, output = maintainer_executor.run_command(
        [
            sys.executable,
            "-c",
            "import time; print('start', flush=True); time.sleep(2)",
        ],
        timeout_seconds=1,
        output_limit_chars=200,
    )

    assert exit_code == maintainer_command_run.TIMEOUT_EXIT_CODE
    assert "start" in output
    assert "Command timed out after 1 second(s)." in output


def test_run_check_passes_check_specific_execution_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check metadata controls timeout and output cap for subprocess runs."""

    captured: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> tuple[int, str]:
        captured["command"] = command
        captured.update(kwargs)
        return 0, ""

    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    result = maintainer_executor.run_check(
        Check(
            "tool",
            ["tool"],
            frozenset(),
            timeout_seconds=7,
            output_limit_chars=11,
        ),
        tmp_path / "logs",
        5,
        200,
    )

    assert result.passed is True
    assert captured == {
        "command": ["tool"],
        "timeout_seconds": 7,
        "output_limit_chars": 11,
    }


def test_run_check_scopes_coverage_file_to_log_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generated coverage data defaults to verifier logs instead of repo root."""

    monkeypatch.delenv("COVERAGE_FILE", raising=False)
    monkeypatch.delenv("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR", raising=False)
    seen: list[str | None] = []
    diagnostics_seen: list[str | None] = []

    def fake_run(command: list[str], **_kwargs: object) -> tuple[int, str]:
        assert command == ["tool"]
        seen.append(os.environ.get("COVERAGE_FILE"))
        diagnostics_seen.append(os.environ.get("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"))
        return 0, ""

    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    result = maintainer_executor.run_check(
        Check("tool", ["tool"], frozenset()), tmp_path / "logs", 5, 200
    )

    assert result.passed is True
    assert seen == [str(tmp_path / "logs" / ".coverage")]
    assert diagnostics_seen == [str(tmp_path / "logs")]
    assert "COVERAGE_FILE" not in os.environ
    assert "AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR" not in os.environ


def test_run_check_preserves_explicit_coverage_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User-provided coverage destination is not overwritten."""

    monkeypatch.setenv("COVERAGE_FILE", "custom.coverage")
    monkeypatch.setenv("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR", "outer-logs")
    seen: list[str | None] = []
    diagnostics_seen: list[str | None] = []

    def fake_run(_command: list[str], **_kwargs: object) -> tuple[int, str]:
        seen.append(os.environ.get("COVERAGE_FILE"))
        diagnostics_seen.append(os.environ.get("AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"))
        return 0, ""

    monkeypatch.setattr(maintainer_executor, "run_command", fake_run)

    maintainer_executor.run_check(Check("tool", ["tool"], frozenset()), tmp_path / "logs", 5, 200)

    assert seen == ["custom.coverage"]
    assert diagnostics_seen == [str(tmp_path / "logs")]
    assert os.environ["COVERAGE_FILE"] == "custom.coverage"
    assert os.environ["AGENT_MAINTAINER_DIAGNOSTIC_ARTIFACTS_DIR"] == "outer-logs"


def test_missing_requirement_reports_required_path(tmp_path: Path) -> None:
    check = Check("missing", ["true"], frozenset(), required_paths=("missing.py",))

    assert maintainer_executor.missing_requirement(check) == "required path 'missing.py' is absent"


def test_missing_requirement_uses_capability_aware_executable_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maintainer_executor.shutil, "which", constant_callback(None))
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


@pytest.mark.parametrize(
    ("reason", "expected"),
    (
        ("disabled by default", SKIP_STATUS_DISABLED),
        (".github/workflows is absent", SKIP_STATUS_MISSING_OPTIONAL),
        ("enabled but no YAML files matched: docs/**", SKIP_STATUS_NOT_APPLICABLE),
        (
            "enabled without pinned input; skipped to avoid auditing the active environment",
            SKIP_STATUS_UNSAFE_CONFIG,
        ),
        ("tests are disabled by require_tests = false", SKIP_STATUS_REQUIRED),
    ),
)
def test_optional_skip_status_classifies_reason(reason: str, expected: str) -> None:
    check = Check("pip-audit", ["pip-audit"], frozenset(), optional_skip_reason=reason)

    assert maintainer_executor.optional_skip_status(check) == expected


def test_explicit_optional_skip_status_wins() -> None:
    check = Check(
        "custom",
        ["custom"],
        frozenset(),
        optional_skip_reason="disabled",
        optional_skip_status=SKIP_STATUS_NOT_APPLICABLE,
    )

    assert maintainer_executor.optional_skip_status(check) == SKIP_STATUS_NOT_APPLICABLE


def test_run_check_writes_skip_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    check = Check("pip-audit", ["pip-audit"], frozenset(), optional_skip_reason="disabled")

    result = maintainer_executor.run_check(check, tmp_path / "logs", 5, 200)

    assert result.name == "pip-audit"
    assert result.passed is True
    assert result.output == "disabled"
    assert result.skipped is True
    assert result.skip_status == SKIP_STATUS_DISABLED
    assert result.command == ("pip-audit",)
    assert result.log_path == str(tmp_path / "logs" / "pip-audit.log")
    assert (tmp_path / "logs" / "pip-audit.log").read_text(encoding="utf-8")


def test_run_check_summarizes_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> tuple[int, str]:
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
    assert "output omitted" in result.output
    assert "chars" in result.output
    assert "lines" in result.output
    assert ".verify-logs/" in result.output


def test_run_check_records_existing_declared_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "coverage.xml"

    def fake_run(command: list[str], **_kwargs: object) -> tuple[int, str]:
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

    def fake_run(command: list[str], **_kwargs: object) -> tuple[int, str]:
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
