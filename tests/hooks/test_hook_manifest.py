"""Tests the authoritative managed hook-file inventory."""

from __future__ import annotations

import os
import re
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from agent_client_hooks import adapters, constants, manifest
from agent_maintainer.core.scaffold import initializer
from tests.support.paths import REPO_ROOT

CONFIGURED_HOOK_PATTERN = re.compile(
    r"(?P<path>\.(?:codex|claude)/hooks/[A-Za-z0-9_.-]+\.py)",
)


def test_manifest_records_complete_lifecycle_policy() -> None:
    """Every managed path has one complete, unique lifecycle record."""

    records = manifest.managed_files()
    identities = {(item.client, item.relative_path) for item in records}

    assert len(identities) == len(records)
    assert {item.client for item in records} == set(constants.CLIENTS)
    for item in records:
        assert item.description
        assert item.scopes
        assert item.ownership_marker
        assert item.status_policy in {"exact", "merged"}
        assert item.merge_strategy in {"replace", "codex-toml", "claude-json"}


@pytest.mark.parametrize("client", constants.CLIENTS)
@pytest.mark.parametrize("scope", constants.SCOPES)
def test_manifest_drives_install_and_uninstall_paths(
    client: str,
    scope: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adapter install and uninstall surfaces select the same scoped records."""

    home = tmp_path / "home"
    target = tmp_path / "repo"
    monkeypatch.setattr(adapters, "home", lambda: home)
    adapter = adapters.adapter_for_client(client)
    options = manifest.RenderOptions(user_scope=scope == constants.USER_SCOPE)
    expected_records = manifest.managed_files(client, scope=scope)

    if isinstance(adapter, adapters.ClaudeCodeAdapter):
        plans = adapter.install(target, scope, async_rewake_stop=False)
    else:
        plans = adapter.install(target, scope)

    root = home if scope == constants.USER_SCOPE else target.resolve()
    expected_paths = tuple(root / item.relative_path for item in expected_records)
    assert tuple(plan.path for plan in plans) == expected_paths
    assert tuple(plan.content for plan in plans) == tuple(
        manifest.render(item, options=options) for item in expected_records
    )
    assert adapter.uninstall(target, scope) == tuple(
        path for path, item in zip(expected_paths, expected_records, strict=True) if item.uninstall
    )


def test_scaffold_uses_every_manifest_scaffold_record(tmp_path: Path) -> None:
    """Agent initialization emits each manifest-selected file exactly once."""

    assert initializer.main(["--target", str(tmp_path), "--track", "agent"]) == 0

    expected = manifest.scaffold_files()
    for item in expected:
        path = tmp_path / item.relative_path
        assert path.read_text(encoding="utf-8") == manifest.render_scaffold(item)


def test_checked_in_managed_scripts_match_renderers() -> None:
    """Dogfood hook scripts remain byte-for-byte current with their renderer."""

    for item in manifest.managed_files(scope=constants.REPO_SCOPE):
        if item.kind != "script":
            continue
        checked_in = REPO_ROOT / item.relative_path
        assert checked_in.read_text(encoding="utf-8") == manifest.render(item)


def test_hook_documentation_lists_every_manifest_path() -> None:
    """Public hook inventory stays complete when the manifest changes."""

    documentation = (REPO_ROOT / "docs" / "agent-client-hooks.md").read_text(
        encoding="utf-8",
    )

    for item in manifest.managed_files():
        assert f"`{item.relative_path}`" in documentation


@pytest.mark.parametrize("client", constants.CLIENTS)
def test_generated_config_commands_resolve_and_noop(
    client: str,
    tmp_path: Path,
) -> None:
    """Every configured wrapper exists and safely handles an empty event."""

    assert initializer.main(["--target", str(tmp_path), "--track", "agent"]) == 0
    config = manifest.config_files(client)[0]
    configured_paths = tuple(CONFIGURED_HOOK_PATTERN.findall(manifest.render_scaffold(config)))
    expected_paths = tuple(
        item.relative_path
        for item in manifest.hook_files(client)
        if item.relative_path != ".codex/hooks/hook_audit.py"
    )

    assert configured_paths == expected_paths
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
    )
    for relative_path in configured_paths:
        completed = subprocess.run(  # nosec B603
            [sys.executable, str(tmp_path / relative_path)],
            cwd=tmp_path,
            env=environment,
            input="{}\n",
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
