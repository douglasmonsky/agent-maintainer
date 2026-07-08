"""Tests TypeScript provider doctor hints."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import providers as doctor_providers
from agent_maintainer.doctor.support.models import MISSING, OK, UNSAFE_CONFIG, WARNING


# docsync:evidence.start evidence.typescript.doctor_setup_tests
def test_typescript_doctor_is_silent_when_provider_disabled() -> None:
    """Disabled TypeScript provider does not add doctor noise."""
    assert doctor_providers.check_typescript_provider(MaintainerConfig()) == ()


def test_typescript_doctor_warns_when_enabled_without_commands() -> None:
    """Enabled provider with no commands gets a concrete setup hint."""
    config = replace(MaintainerConfig(), enable_typescript=True)

    (result,) = doctor_providers.check_typescript_provider(config)

    assert result.status == WARNING
    assert result.state == UNSAFE_CONFIG
    assert "no commands" in result.message
    assert "typescript_lint_command" in result.hint
    assert "ESLint JSON" in result.hint
    assert "tsc --pretty false" in result.hint
    assert "Jest/Vitest JSON" in result.hint
    assert "coverage-summary.json" in result.hint
    assert "lcov.info" in result.hint
    assert "disable enable_typescript" in result.hint


def test_typescript_doctor_warns_when_command_executable_missing() -> None:
    """Configured command executables must resolve."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=("definitely-missing-agent-maintainer-ts", "lint"),
    )

    (result,) = doctor_providers.check_typescript_provider(config)

    assert result.status == WARNING
    assert result.state == MISSING
    assert "typescript-lint" in result.message
    assert "definitely-missing-agent-maintainer-ts" in result.message
    assert "local node_modules/.bin" in result.hint
    assert "explicit TypeScript command fields" in result.hint
    assert "no package manager is inferred" in result.hint


def test_typescript_doctor_passes_when_command_executable_exists() -> None:
    """Configured command executables produce an active provider row."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=(sys.executable, "--version"),
    )

    (result,) = doctor_providers.check_typescript_provider(config)

    assert result.status == OK
    assert "typescript-lint" in result.message


def test_run_doctor_includes_typescript_row_only_when_enabled(tmp_path: Path) -> None:
    """Full doctor result list includes TypeScript row only after opt-in."""
    disabled_results = maintainer_doctor.run_doctor(tmp_path, MaintainerConfig())
    enabled_results = maintainer_doctor.run_doctor(
        tmp_path,
        replace(
            MaintainerConfig(),
            enable_typescript=True,
            typescript_lint_command=(sys.executable, "--version"),
        ),
    )

    assert not [result for result in disabled_results if result.name == "typescript-provider"]
    assert [result for result in enabled_results if result.name == "typescript-provider"]


# docsync:evidence.end evidence.typescript.doctor_setup_tests
