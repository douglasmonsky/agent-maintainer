"""Tests direct agent_client_hooks package boundaries."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from agent_client_hooks import adapters, merge, templates
from agent_maintainer.hooks import adapters as shim_adapters
from agent_maintainer.hooks import merge as shim_merge


def test_agent_client_hooks_templates_are_direct_package_surface() -> None:
    """Direct package templates expose existing client config behavior."""
    codex_config = templates.codex_config_file()
    assert "agent-maintainer:codex-hooks" in codex_config
    assert ".codex/hooks/post_edit_fast_gate.py" in codex_config

    claude_settings = json.loads(templates.claude_settings())
    assert set(claude_settings["hooks"]) == {"PostToolUse", "Stop", "SubagentStop"}
    async_claude_settings = json.loads(templates.claude_settings(async_rewake_stop=True))
    assert async_claude_settings["hooks"]["Stop"][0]["hooks"][0]["asyncRewake"] is True


def test_agent_client_hooks_adapters_plan_existing_clients(tmp_path: Path) -> None:
    """Direct package adapters own client planning primitives."""
    plans = adapters.CodexAdapter().install(tmp_path, adapters.REPO_SCOPE)

    assert [plan.description for plan in plans] == [
        "Codex hook config",
        "Codex post-edit hook",
        "Codex stop hook",
        "Codex hook-audit compatibility shim",
    ]
    assert plans[0].merge_codex


def test_claude_adapter_describes_async_rewake_plan(tmp_path: Path) -> None:
    """Claude adapter dry-run descriptions expose async rewake mode."""
    plans = adapters.ClaudeCodeAdapter().install(
        tmp_path,
        adapters.REPO_SCOPE,
        async_rewake_stop=True,
    )

    assert plans[0].description == "Claude Code hook settings (async rewake Stop/SubagentStop)"


def test_agent_client_hooks_merge_uses_package_templates() -> None:
    """Direct package merge helpers preserve managed Codex block behavior."""
    merged = merge.merge_codex_config("other = true\n", templates.codex_config_block())

    assert "other = true" in merged
    assert "hooks = true" in merged
    assert "agent-maintainer:codex-hooks" in merged


def test_legacy_adapter_imports_still_work() -> None:
    """Old Agent Maintainer adapter path remains compatible."""

    assert shim_adapters.CodexAdapter is adapters.CodexAdapter
    assert shim_adapters.ClaudeCodeAdapter is adapters.ClaudeCodeAdapter
    assert shim_adapters.adapter_for_client is adapters.adapter_for_client
    assert shim_adapters.CODEX_CLIENT == adapters.CODEX_CLIENT


def test_legacy_merge_imports_still_work() -> None:
    """Old Agent Maintainer merge path remains compatible."""

    assert shim_merge.merge_codex_config is merge.merge_codex_config
    assert shim_merge.ensure_codex_hooks_feature is merge.ensure_codex_hooks_feature
    assert shim_merge.CODEX_HOOK_FEATURE == merge.CODEX_HOOK_FEATURE


def test_agent_client_hooks_do_not_import_agent_maintainer() -> None:
    """Extracted hook package must not import product package internals."""
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[str] = []

    for path in sorted((repo_root / "src" / "agent_client_hooks").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported = _imported_module(node)
            if imported and imported.partition(".")[0] == "agent_maintainer":
                violations.append(f"{path.relative_to(repo_root)} imports {imported}")

    assert violations == []


def _imported_module(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return node.module
    return None
