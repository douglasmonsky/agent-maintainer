"""Tests for managed agent-client hook installation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.hooks import manager, merge, templates


def test_repo_install_writes_codex_and_claude_files(tmp_path: Path) -> None:
    """Repo-scope install writes shareable client hook files."""

    status = manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path,
            client=manager.ALL_CLIENTS,
            force=True,
        )
    )

    assert status == 0
    expected = (
        tmp_path / ".codex" / "config.toml",
        tmp_path / ".codex" / "hooks" / "post_edit_fast_gate.py",
        tmp_path / ".codex" / "hooks" / "stop_full_verify.py",
        tmp_path / ".claude" / "settings.json",
        tmp_path / ".claude" / "hooks" / "post_tool_use.py",
        tmp_path / ".claude" / "hooks" / "stop.py",
        tmp_path / ".claude" / "hooks" / "subagent_stop.py",
    )
    for path in expected:
        assert path.exists()


def test_codex_merge_removes_previous_agent_hook_blocks() -> None:
    """Codex merge removes stale unmarked Agent Maintainer hook tables."""

    previous = """
[features]

[[hooks.PostToolUse]]
matcher = "apply_patch|Edit|Write"

[[hooks.PostToolUse.hooks]]
type = "command"
command = 'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/post_edit_fast_gate.py"'

[[hooks.Stop]]

[[hooks.Stop.hooks]]
type = "command"
command = 'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/stop_full_verify.py"'
"""
    merged = merge.merge_codex_config(previous, templates.codex_config_block())

    assert merged.count("[[hooks.PostToolUse]]") == 1
    assert merged.count("[[hooks.Stop]]") == 1
    assert "hooks = true" in merged
    assert "agent-maintainer:codex-hooks" in merged


def test_user_scope_dry_run_does_not_prompt_or_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User-scope dry-runs avoid permission prompts and file writes."""

    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("existing = true\n", encoding="utf-8")
    monkeypatch.setattr(manager, "home", lambda: tmp_path)

    status = manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CODEX_CLIENT,
            scope=manager.USER_SCOPE,
            dry_run=True,
        )
    )

    assert status == 0
    assert config_path.read_text(encoding="utf-8") == "existing = true\n"
    assert not list(config_path.parent.glob("*.agent-maintainer-backup-*"))


def test_user_scope_uses_installed_command_without_repo_wrappers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User-scope install plans global config that calls console command."""

    monkeypatch.setattr(manager, "home", lambda: tmp_path)

    status = manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path / "repo",
            client=manager.CLAUDE_CODE_CLIENT,
            scope=manager.USER_SCOPE,
            yes=True,
            force=True,
        )
    )

    assert status == 0
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    command = settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert command == (
        "agent-maintainer hooks run --platform claude-code --event PostToolUse --profile fast"
    )
    assert not (tmp_path / ".claude" / "hooks").exists()


def test_status_hooks_reports_config_and_script_presence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status reports config and script presence for selected clients."""

    manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CODEX_CLIENT,
            force=True,
        ),
    )
    capsys.readouterr()

    status = manager.status_hooks(tmp_path, manager.ALL_CLIENTS)

    output = capsys.readouterr().out
    assert status == 0
    assert "codex: config=present scripts=present" in output
    assert "claude-code: config=missing scripts=missing" in output


def test_install_noops_when_no_plans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Install reports a no-op when selected clients have no planned writes."""

    monkeypatch.setattr(manager, "planned_writes", lambda *_args: ())

    status = manager.install_hooks(
        manager.InstallOptions(target=tmp_path, client=manager.CODEX_CLIENT),
    )

    assert status == 0
    assert "No hook files selected." in capsys.readouterr().out


def test_user_scope_install_aborts_without_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User-scope installs require explicit confirmation."""

    monkeypatch.setattr(manager, "home", lambda: tmp_path)
    monkeypatch.setattr(manager, "confirm_user_scope", lambda: False)

    status = manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path / "repo",
            client=manager.CODEX_CLIENT,
            scope=manager.USER_SCOPE,
        ),
    )

    assert status == 1
    assert not (tmp_path / ".codex" / "config.toml").exists()


def test_planned_writes_rejects_unknown_client(tmp_path: Path) -> None:
    """Unknown hook clients fail before file writes are planned."""

    with pytest.raises(ValueError, match="Unsupported hook client"):
        manager.planned_writes(
            "unknown",
            manager.InstallOptions(target=tmp_path, client="unknown"),
        )


def test_write_plan_skips_unchanged_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unchanged managed files are not rewritten."""

    hook_file = tmp_path / "hook.py"
    hook_file.write_text("same", encoding="utf-8")

    manager.write_plan(
        manager.PlannedWrite(hook_file, "same", "hook"),
        manager.InstallOptions(target=tmp_path, client=manager.CODEX_CLIENT),
    )

    assert hook_file.read_text(encoding="utf-8") == "same"
    assert "unchanged" in capsys.readouterr().out


def test_write_plan_backs_up_existing_file(tmp_path: Path) -> None:
    """Existing unmanaged files are backed up before replacement."""

    hook_file = tmp_path / "hook.py"
    hook_file.write_text("old", encoding="utf-8")

    manager.write_plan(
        manager.PlannedWrite(hook_file, "new", "hook"),
        manager.InstallOptions(target=tmp_path, client=manager.CODEX_CLIENT),
    )

    assert hook_file.read_text(encoding="utf-8") == "new"
    backups = list(tmp_path.glob("hook.py.agent-maintainer-backup-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old"


def test_rendered_content_merges_existing_claude_settings(tmp_path: Path) -> None:
    """Claude settings merge tolerates invalid existing hook shapes."""

    settings = tmp_path / "settings.json"
    settings.write_text('{"hooks": []}', encoding="utf-8")

    rendered = manager.rendered_content(
        manager.PlannedWrite(
            settings,
            templates.claude_settings(user_scope=True),
            "Claude settings",
            merge_json=True,
        ),
    )

    parsed = json.loads(rendered)
    command = parsed["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert command.startswith("agent-maintainer hooks run")


def test_merge_claude_settings_tolerates_non_object_file(tmp_path: Path) -> None:
    """Claude settings merge replaces non-object JSON with managed hooks."""

    settings = tmp_path / "settings.json"
    settings.write_text("[]", encoding="utf-8")

    rendered = merge.merge_claude_settings(
        settings,
        templates.claude_settings(user_scope=True),
    )

    assert "PostToolUse" in json.loads(rendered)["hooks"]


def test_strip_managed_block_removes_existing_marker() -> None:
    """Managed marker blocks are replaced instead of duplicated."""

    content = "before\n# >>> test >>>\nold\n# <<< test <<<\nafter\n"

    stripped = merge.strip_managed_block(content, "test")
    assert "old" not in stripped
    assert stripped.startswith("before\n")
    assert stripped.endswith("after\n")


def test_orphan_previous_hook_parent_is_removed() -> None:
    """Old parent hook tables are dropped when their child hook is gone."""

    sections = ["[[hooks.Stop]]\n", "[other]\nvalue = true"]

    assert merge.previous_agent_codex_hook_indexes(sections) == {0}


def test_codex_feature_section_rewrites_disabled_hooks() -> None:
    """Codex feature merge enables hooks once inside an existing section."""

    merged = merge.ensure_codex_hooks_feature(
        "[features]\nhooks = false\n[other]\nvalue = true\n",
    )

    assert merged == "[features]\nhooks = true\n[other]\nvalue = true"
