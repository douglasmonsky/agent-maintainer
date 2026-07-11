"""Tests for doctor integration diagnostics."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.doctor.support import integrations as doctor_integrations
from agent_maintainer.doctor.support import models as doctor_models
from agent_waits.capabilities import CODEX_REWAKE_ENV, CODEX_THREAD_ID_ENV

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


def test_codex_rewake_capabilities_are_advisory_when_disabled() -> None:
    """Optional rewake capability rows do not break strict doctor by default."""

    results = doctor_integrations.check_codex_rewake_capabilities(
        env={},
        codex_available=False,
        sdk_available=False,
    )
    by_name = {result.name: result for result in results}

    assert tuple(by_name) == (
        "codex-thread-context",
        "codex-app-server",
        "codex-python-sdk",
        "codex-terminal-rewake",
    )
    assert all(result.status == doctor_models.OK for result in results)
    assert by_name["codex-thread-context"].state == doctor_models.MISSING
    assert by_name["codex-app-server"].state == doctor_models.MISSING
    assert by_name["codex-python-sdk"].state == doctor_models.MISSING
    assert by_name["codex-terminal-rewake"].state == doctor_models.DISABLED


def test_codex_rewake_capabilities_warn_without_claiming_visible_wake() -> None:
    """Enabled app-server support remains manual-only until smoke proves rewake."""

    thread_id = "thread-private-123"
    results = doctor_integrations.check_codex_rewake_capabilities(
        env={CODEX_REWAKE_ENV: "1", CODEX_THREAD_ID_ENV: thread_id},
        codex_available=True,
        sdk_available=True,
    )
    by_name = {result.name: result for result in results}
    rendered = repr(results)

    assert by_name["codex-thread-context"].status == doctor_models.OK
    assert by_name["codex-app-server"].status == doctor_models.OK
    assert by_name["codex-python-sdk"].status == doctor_models.OK
    assert by_name["codex-terminal-rewake"].status == doctor_models.WARNING
    assert "visible thread wake is unproven" in by_name["codex-terminal-rewake"].message
    assert "wait resume <id>" in by_name["codex-terminal-rewake"].hint
    assert "heartbeat" in by_name["codex-terminal-rewake"].hint
    assert thread_id not in rendered


def test_codex_rewake_terminal_row_names_missing_requirement() -> None:
    """Enabled rewake reports the first unavailable requirement without secrets."""

    results = doctor_integrations.check_codex_rewake_capabilities(
        env={CODEX_REWAKE_ENV: "1"},
        codex_available=True,
        sdk_available=False,
    )
    terminal = results[-1]

    assert terminal.status == doctor_models.WARNING
    assert terminal.state == doctor_models.MISSING
    assert "thread context is absent" in terminal.message


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
