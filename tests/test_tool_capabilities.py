"""Tests for guardrail tool capability modeling."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import guardrail_tool_capabilities as capabilities
from scripts.guardrail_models import FULL_PROFILES, Check


def test_python_package_tool_state_passes_when_local_executable_exists(tmp_path: Path) -> None:
    tool_path = tmp_path / ".venv" / "bin" / "ruff"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")
    capability = capabilities.ToolCapability("ruff", capabilities.PYTHON_PACKAGE)

    state = capabilities.evaluate_tool(tmp_path, capability)

    assert state.state == capabilities.SUPPORTED
    assert "Python package" in state.message


def test_external_binary_tool_state_reports_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(capabilities.shutil, "which", lambda name: None)
    capability = capabilities.ToolCapability("git", capabilities.EXTERNAL_BINARY)

    state = capabilities.evaluate_tool(tmp_path, capability)

    assert state.state == capabilities.MISSING
    assert "external binary" in state.message


def test_disabled_tool_state_does_not_require_executable(tmp_path: Path) -> None:
    capability = capabilities.ToolCapability("lint-imports", capabilities.PYTHON_PACKAGE)

    state = capabilities.evaluate_tool(tmp_path, capability, enabled=False)

    assert state.state == capabilities.DISABLED
    assert "disabled" in state.message


def test_github_action_only_tool_state_can_be_not_applicable(tmp_path: Path) -> None:
    capability = capabilities.ToolCapability("zizmor", capabilities.GITHUB_ACTION_ONLY)

    state = capabilities.evaluate_tool(tmp_path, capability, applicable=False)

    assert state.state == capabilities.NOT_APPLICABLE
    assert "not applicable" in state.message


def test_manual_optional_tool_state_reports_disabled_by_default(tmp_path: Path) -> None:
    capability = capabilities.ToolCapability("mutmut", capabilities.MANUAL_OPTIONAL)

    state = capabilities.evaluate_tool(tmp_path, capability, enabled=False)

    assert state.state == capabilities.DISABLED
    assert "manual optional" in state.message


def test_check_states_skip_disabled_optional_checks(tmp_path: Path) -> None:
    check = Check(
        "import-linter",
        ["lint-imports"],
        FULL_PROFILES,
        required_executable="lint-imports",
        optional_skip_reason=".importlinter is absent",
    )

    states = capabilities.states_for_checks(tmp_path, [check])

    assert states[0].state == capabilities.DISABLED
    assert states[0].tool == "lint-imports"


def test_check_states_require_active_optional_checks(tmp_path: Path) -> None:
    (tmp_path / ".importlinter").write_text("[importlinter]\n", encoding="utf-8")
    tool_path = tmp_path / ".venv" / "bin" / "lint-imports"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")
    check = Check(
        "import-linter",
        ["lint-imports"],
        FULL_PROFILES,
        required_executable="lint-imports",
        optional_skip_reason=".importlinter is absent",
    )

    states = capabilities.states_for_checks(tmp_path, [check])

    assert states[0].state == capabilities.SUPPORTED


def test_workflow_tool_states_follow_workflow_applicability(tmp_path: Path) -> None:
    check = Check(
        "zizmor",
        ["zizmor"],
        FULL_PROFILES,
        required_executable="zizmor",
        optional_skip_reason=".github/workflows is absent",
    )

    assert capabilities.states_for_checks(tmp_path, [check])[0].state == capabilities.DISABLED

    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    tool_path = tmp_path / ".venv" / "bin" / "zizmor"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")

    assert capabilities.states_for_checks(tmp_path, [check])[0].state == capabilities.SUPPORTED


def test_summarize_states_fails_on_missing_tools(tmp_path: Path) -> None:
    states = [
        capabilities.evaluate_tool(
            tmp_path,
            capabilities.ToolCapability("missing-tool", capabilities.PYTHON_PACKAGE),
        )
    ]

    status, message = capabilities.summarize_states(states)

    assert status == capabilities.MISSING
    assert "missing-tool" in message
