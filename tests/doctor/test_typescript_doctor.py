"""Tests TypeScript provider doctor hints."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import providers as doctor_providers
from agent_maintainer.doctor.support.models import MISSING, OK, UNSAFE_CONFIG, WARNING
from agent_maintainer.ecosystems.models import (
    ProviderCommandSpec,
    ProviderMaturity,
    ProviderMetadata,
)


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

    result, guidance = doctor_providers.check_typescript_provider(config)

    assert result.status == OK
    assert "typescript-lint" in result.message
    assert guidance.name == "typescript-repair-fact-output"
    assert guidance.status == OK
    assert "ESLint JSON" in guidance.hint
    assert "no package manager is inferred" in guidance.hint


def test_typescript_doctor_recommends_stable_repair_fact_outputs() -> None:
    """Human-oriented TypeScript commands receive parser-friendly output guidance."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=(sys.executable, "lint"),
        typescript_typecheck_command=(sys.executable, "typecheck"),
        typescript_test_command=(sys.executable, "test"),
    )

    provider, guidance = doctor_providers.check_typescript_provider(config)

    assert provider.status == OK
    assert guidance.name == "typescript-repair-fact-output"
    assert guidance.status == OK
    assert "typescript_lint_command" in guidance.hint
    assert "typescript_typecheck_command" in guidance.hint
    assert "typescript_test_command" in guidance.hint
    assert "ESLint JSON" in guidance.hint
    assert "tsc with --pretty false" in guidance.hint
    assert "Jest/Vitest JSON" in guidance.hint
    assert "coverage-summary.json or lcov.info" in guidance.hint


def test_typescript_doctor_skips_repair_fact_guidance_when_outputs_are_stable() -> None:
    """Parser-friendly command tokens avoid extra TypeScript doctor guidance."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=(sys.executable, "eslint", "--format=json"),
        typescript_typecheck_command=(sys.executable, "tsc", "--pretty=false"),
        typescript_test_command=(sys.executable, "vitest", "--json", "lcov.info"),
    )

    (provider,) = doctor_providers.check_typescript_provider(config)

    assert provider.status == OK
    assert provider.name == "typescript-provider"


def test_configured_command_provider_uses_generic_missing_tool_hint() -> None:
    """Non-TypeScript providers keep generic missing-tool hint text."""
    result = doctor_providers.missing_command_hint(
        doctor_providers.builtin_provider_metadata()[0],
    )

    assert result == "Install missing tools or update Python command fields."


def test_empty_command_hint_handles_generic_provider_metadata() -> None:
    """Generic provider metadata keeps compact command-field hints."""
    metadata = ProviderMetadata(
        name="example",
        display_name="Example",
        maturity=ProviderMaturity.EXPERIMENTAL,
        docs_path="docs/example.md",
        capabilities=(),
        enabled_field="enable_example",
        command_specs=(
            ProviderCommandSpec("example-lint", "example_lint_command"),
            ProviderCommandSpec("example-test", "example_test_command"),
        ),
    )

    assert doctor_providers.empty_command_hint(metadata) == (
        "Set example_lint_command, or example_test_command; disable enable_example."
    )


def test_empty_command_hint_handles_metadata_without_commands_or_enabled_field() -> None:
    """Provider metadata without command fields receives fallback hint."""
    metadata = ProviderMetadata(
        name="example",
        display_name="Example",
        maturity=ProviderMaturity.EXPERIMENTAL,
        docs_path="docs/example.md",
        capabilities=(),
    )

    assert doctor_providers.empty_command_hint(metadata) == (
        "No provider command fields are available."
    )
    assert doctor_providers.provider_disable_hint(None) == "."


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
