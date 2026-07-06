"""Tests for managed hook templates."""

from __future__ import annotations

import json

import yaml

from agent_client_hooks import templates
from agent_maintainer.core.scaffold import templates as scaffold_templates
from agent_maintainer.hooks import templates as shim_templates


def test_codex_config_file_enables_hooks() -> None:
    """Complete Codex config includes feature flag and managed hooks."""

    config = templates.codex_config_file()

    assert "[features]" in config
    assert "hooks = true" in config
    assert "agent-maintainer:codex-hooks" in config
    assert ".codex/hooks/post_edit_fast_gate.py" in config
    assert ".codex/hooks/post_pr_wait.py" in config
    assert 'matcher = "Bash"' in config


def test_claude_settings_template_declares_supported_events() -> None:
    """Claude Code settings include post-edit and stop-time hooks."""

    settings = json.loads(templates.claude_settings())

    assert set(settings["hooks"]) == {"PostToolUse", "Stop", "SubagentStop"}
    assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit|MultiEdit"
    assert settings["hooks"]["PostToolUse"][1]["matcher"] == "Bash"
    command = settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert ".claude/hooks/post_tool_use.py" in command
    pr_wait_hook = settings["hooks"]["PostToolUse"][1]["hooks"][0]
    assert ".claude/hooks/post_pr_wait.py" in pr_wait_hook["command"]
    assert pr_wait_hook["async"] is True
    assert pr_wait_hook["asyncRewake"] is True
    assert "async" not in settings["hooks"]["PostToolUse"][0]["hooks"][0]
    assert "async" not in settings["hooks"]["Stop"][0]["hooks"][0]
    assert "asyncRewake" not in settings["hooks"]["SubagentStop"][0]["hooks"][0]


def test_claude_async_rewake_applies_only_to_stop_hooks() -> None:
    """Claude Code async rewake is opt-in for slow stop-time hooks."""

    settings = json.loads(templates.claude_settings(async_rewake_stop=True))

    assert "async" not in settings["hooks"]["PostToolUse"][0]["hooks"][0]
    stop_hook = settings["hooks"]["Stop"][0]["hooks"][0]
    subagent_hook = settings["hooks"]["SubagentStop"][0]["hooks"][0]
    assert stop_hook["async"] is True
    assert stop_hook["asyncRewake"] is True
    assert subagent_hook["async"] is True
    assert subagent_hook["asyncRewake"] is True


def test_claude_async_rewake_user_scope_commands_pass_runtime_flag() -> None:
    """User-scope async rewake commands invoke runtime async-rewake mode."""

    settings = json.loads(templates.claude_settings(user_scope=True, async_rewake_stop=True))

    post_command = settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    pr_wait_command = settings["hooks"]["PostToolUse"][1]["hooks"][0]["command"]
    stop_command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
    subagent_command = settings["hooks"]["SubagentStop"][0]["hooks"][0]["command"]

    assert "--async-rewake" not in post_command
    assert pr_wait_command == (
        "agent-maintainer hooks pr-wait --platform claude-code --async-rewake"
    )
    assert stop_command.endswith("--async-rewake")
    assert subagent_command.endswith("--async-rewake")


def test_claude_async_rewake_repo_wrappers_pass_runtime_flag() -> None:
    """Repo-local async rewake wrappers call runtime async-rewake mode."""

    assert "async_rewake=True" in templates.claude_stop_hook(async_rewake=True)
    assert "async_rewake=True" in templates.claude_subagent_stop_hook(async_rewake=True)
    assert "async_rewake=False" in templates.claude_stop_hook()


def test_hook_wrappers_are_valid_python() -> None:
    """Generated wrapper strings compile without writing bytecode."""

    for source in (
        templates.codex_post_hook(),
        templates.codex_pr_wait_hook(),
        templates.codex_stop_hook(),
        templates.claude_post_hook(),
        templates.claude_pr_wait_hook(),
        templates.claude_stop_hook(),
        templates.claude_stop_hook(async_rewake=True),
        templates.claude_subagent_stop_hook(),
        templates.claude_subagent_stop_hook(async_rewake=True),
        templates.hook_audit_shim(),
    ):
        compile(source, "<hook-template>", "exec")


def test_legacy_template_imports_still_work() -> None:
    """Old Agent Maintainer hook template path remains compatible."""
    assert shim_templates.codex_config_file() == templates.codex_config_file()


def test_starter_workflow_installs_node_dependencies_inside_run_block() -> None:
    """Starter workflow keeps optional Node install shell inside YAML run block."""

    workflow = yaml.safe_load(scaffold_templates.WORKFLOW)
    steps = workflow["jobs"]["verify"]["steps"]
    install_step = next(
        step for step in steps if step.get("name") == "Install project and Agent Maintainer tools"
    )

    assert "if [ -f package.json ]; then" in install_step["run"]
    assert "npm ci" in install_step["run"]
