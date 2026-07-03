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


def test_claude_settings_template_declares_supported_events() -> None:
    """Claude Code settings include post-edit and stop-time hooks."""

    settings = json.loads(templates.claude_settings())

    assert set(settings["hooks"]) == {"PostToolUse", "Stop", "SubagentStop"}
    assert settings["hooks"]["PostToolUse"][0]["matcher"] == "Write|Edit|MultiEdit"
    command = settings["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert ".claude/hooks/post_tool_use.py" in command


def test_hook_wrappers_are_valid_python() -> None:
    """Generated wrapper strings compile without writing bytecode."""

    for source in (
        templates.codex_post_hook(),
        templates.codex_stop_hook(),
        templates.claude_post_hook(),
        templates.claude_stop_hook(),
        templates.claude_subagent_stop_hook(),
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
