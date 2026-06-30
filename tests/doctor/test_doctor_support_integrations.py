"""Tests for doctor integration diagnostics."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.doctor.support import integrations as doctor_integrations
from agent_maintainer.doctor.support import models as doctor_models

ENCODING = "utf-8"


def test_pre_commit_installed(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding=ENCODING)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("#!/bin/sh\n", encoding=ENCODING)

    result = doctor_integrations.check_pre_commit(tmp_path)

    assert result.status == doctor_models.OK
    assert result.message == ".git/hooks/pre-commit is installed."


def test_codex_hooks_disabled(tmp_path: Path) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = false\n", encoding=ENCODING)

    result = doctor_integrations.check_codex_hooks(tmp_path)

    assert result.status == doctor_models.WARNING
    assert result.state == doctor_models.DISABLED
    assert "does not enable hooks" in result.message
    assert "hooks = true" in result.hint


def test_claude_code_hooks_report_missing_scripts(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text('{"hooks": {}}\n', encoding=ENCODING)

    result = doctor_integrations.check_claude_code_hooks(tmp_path)

    assert result.status == doctor_models.WARNING
    assert result.state == doctor_models.MISSING
    assert ".claude/hooks/post_tool_use.py" in result.message
    assert ".claude/hooks/stop.py" in result.message
    assert ".claude/hooks/subagent_stop.py" in result.message


def test_claude_hooks_settings_without_markers(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text('{"hooks": {}}\n', encoding=ENCODING)
    hook_dir = tmp_path / ".claude" / "hooks"
    hook_dir.mkdir()
    for hook_name in doctor_integrations.CLAUDE_HOOK_NAMES:
        (hook_dir / hook_name).write_text("agent_maintainer\n", encoding=ENCODING)

    result = doctor_integrations.check_claude_code_hooks(tmp_path)

    assert result.status == doctor_models.WARNING
    assert result.state == doctor_models.DISABLED
    assert "does not reference Agent Maintainer hooks" in result.message


def test_claude_hooks_pass_with_settings_marker(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text(
        '{"hooks": {"Stop": [{"command": ".claude/hooks/stop.py"}]}}\n',
        encoding=ENCODING,
    )
    hook_dir = tmp_path / ".claude" / "hooks"
    hook_dir.mkdir()
    for hook_name in doctor_integrations.CLAUDE_HOOK_NAMES:
        (hook_dir / hook_name).write_text("agent_maintainer\n", encoding=ENCODING)

    result = doctor_integrations.check_claude_code_hooks(tmp_path)

    assert result.status == doctor_models.OK
    assert result.message == ".claude/settings.json enables Agent Maintainer hooks."


def test_canonical_commands_report_stale_first(
    tmp_path: Path,
) -> None:
    workflow = tmp_path / ".github" / "workflows" / "verify.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("python3 scripts/guardrail.py verify --profile ci\n", encoding=ENCODING)

    result = doctor_integrations.check_canonical_commands(tmp_path)

    assert result.status == doctor_models.ERROR
    assert result.state == doctor_models.UNSAFE_CONFIG
    assert result.message == "Stale command path in: .github/workflows/verify.yml"


def test_normalized_text_collapses_whitespace() -> None:
    assert (
        doctor_integrations.normalized_text("python3  -m\nagent_maintainer\tverify")
        == "python3 -m agent_maintainer verify"
    )
