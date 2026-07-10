"""Tests lossless managed-hook update and uninstall lifecycle operations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_client_hooks import adapters, templates
from agent_maintainer.hooks import lifecycle, manager, mutations


def test_uninstall_preview_and_apply_preserve_third_party_config(tmp_path: Path) -> None:
    """Preview is inert; apply removes only managed entries and scripts."""

    assert manager.install_hooks(_install_options(tmp_path)) == 0
    codex = tmp_path / ".codex/config.toml"
    codex.write_text(f"{codex.read_text()}\n[custom]\nenabled = true\n", encoding="utf-8")
    claude = tmp_path / ".claude/settings.json"
    payload = json.loads(claude.read_text(encoding="utf-8"))
    payload["theme"] = "dark"
    payload["hooks"]["Stop"].append(_entry("third-party"))
    claude.write_text(json.dumps(payload), encoding="utf-8")
    before = _tree_payloads(tmp_path)
    transactions = _transaction_names(tmp_path)

    preview = lifecycle.UninstallOptions(
        target=tmp_path,
        client=manager.ALL_CLIENTS,
        dry_run=True,
    )
    assert lifecycle.uninstall_hooks(preview) == 0
    assert _tree_payloads(tmp_path) == before
    assert _transaction_names(tmp_path) == transactions

    assert lifecycle.uninstall_hooks(lifecycle.UninstallOptions(tmp_path, manager.ALL_CLIENTS)) == 0

    assert "[custom]" in codex.read_text(encoding="utf-8")
    assert templates.CODEX_MARKER not in codex.read_text(encoding="utf-8")
    remaining = json.loads(claude.read_text(encoding="utf-8"))
    assert remaining["theme"] == "dark"
    assert remaining["hooks"]["Stop"] == [_entry("third-party")]
    for script in _script_paths(tmp_path):
        assert not script.exists()


@pytest.mark.parametrize("force", (False, True))
def test_uninstall_refuses_unowned_script_without_partial_removal(
    tmp_path: Path,
    force: bool,
) -> None:
    """Neither ordinary nor forced uninstall deletes an unowned destination."""

    assert (
        manager.install_hooks(
            manager.InstallOptions(tmp_path, manager.CODEX_CLIENT),
        )
        == 0
    )
    unowned = tmp_path / templates.CODEX_POST_HOOK
    unowned.write_text("user-owned hook\n", encoding="utf-8")
    before = _tree_payloads(tmp_path)

    status = lifecycle.uninstall_hooks(
        lifecycle.UninstallOptions(tmp_path, manager.CODEX_CLIENT, force=force),
    )

    assert status == 1
    assert _tree_payloads(tmp_path) == before


def test_uninstall_force_removes_stale_owned_script(tmp_path: Path) -> None:
    """Force resolves stale content only when a stable ownership marker remains."""

    assert (
        manager.install_hooks(
            manager.InstallOptions(tmp_path, manager.CODEX_CLIENT),
        )
        == 0
    )
    stale = tmp_path / templates.CODEX_POST_HOOK
    stale.write_text('"""Agent Maintainer stale wrapper."""\n', encoding="utf-8")

    assert (
        lifecycle.uninstall_hooks(
            lifecycle.UninstallOptions(tmp_path, manager.CODEX_CLIENT),
        )
        == 1
    )
    assert stale.exists()
    assert (
        lifecycle.uninstall_hooks(
            lifecycle.UninstallOptions(tmp_path, manager.CODEX_CLIENT, force=True),
        )
        == 0
    )
    assert not stale.exists()


def test_invalid_late_config_refuses_all_uninstall_changes(tmp_path: Path) -> None:
    """A late config parse failure stops earlier client removals before apply."""

    assert manager.install_hooks(_install_options(tmp_path)) == 0
    settings = tmp_path / ".claude/settings.json"
    settings.write_text("{", encoding="utf-8")
    before = _tree_payloads(tmp_path)

    status = lifecycle.uninstall_hooks(
        lifecycle.UninstallOptions(tmp_path, manager.ALL_CLIENTS),
    )

    assert status == 1
    assert _tree_payloads(tmp_path) == before


def test_user_uninstall_requires_confirmation_and_preserves_other_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User configuration is confirmed and unrelated commands survive removal."""

    monkeypatch.setattr(adapters, "home", lambda: tmp_path)
    options = manager.InstallOptions(
        tmp_path / "repo",
        manager.CLAUDE_CODE_CLIENT,
        scope=manager.USER_SCOPE,
        yes=True,
    )
    assert manager.install_hooks(options) == 0
    settings = tmp_path / ".claude/settings.json"
    payload = json.loads(settings.read_text(encoding="utf-8"))
    payload["hooks"]["Stop"].append(_entry("third-party"))
    settings.write_text(json.dumps(payload), encoding="utf-8")
    before = settings.read_bytes()
    monkeypatch.setattr(manager, "confirm_user_scope", lambda _operation="write": False)
    uninstall = lifecycle.UninstallOptions(
        tmp_path / "repo",
        manager.CLAUDE_CODE_CLIENT,
        scope=manager.USER_SCOPE,
    )

    assert lifecycle.uninstall_hooks(uninstall) == 1
    assert settings.read_bytes() == before
    assert (
        lifecycle.uninstall_hooks(
            lifecycle.UninstallOptions(
                tmp_path / "repo",
                manager.CLAUDE_CODE_CLIENT,
                scope=manager.USER_SCOPE,
                yes=True,
            )
        )
        == 0
    )
    assert json.loads(settings.read_text())["hooks"]["Stop"] == [_entry("third-party")]


def test_clean_clone_update_twice_keeps_git_status_clean(tmp_path: Path) -> None:
    """Current generated hooks are a no-op on first and second clean-clone update."""

    seed = tmp_path / "seed"
    clone = tmp_path / "clone"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    assert manager.install_hooks(_install_options(seed)) == 0
    _git(seed, "add", ".codex", ".claude")
    _git(
        seed,
        "-c",
        "user.name=Agent Maintainer",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "seed",
    )
    _git(tmp_path, "clone", str(seed), str(clone))
    options = _install_options(clone)

    assert lifecycle.update_hooks(options) == 0
    assert _git(clone, "status", "--porcelain").stdout == ""
    assert lifecycle.update_hooks(options) == 0
    assert _git(clone, "status", "--porcelain").stdout == ""
    assert not mutations.backup_root(clone, git_private=True).exists()


def _install_options(root: Path) -> manager.InstallOptions:
    return manager.InstallOptions(root, manager.ALL_CLIENTS)


def _entry(command: str) -> dict[str, object]:
    return {"hooks": [{"type": "command", "command": command}]}


def _script_paths(root: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for client in manager.CLIENTS
        for path in manager.hook_script_paths(client, root, manager.REPO_SCOPE)
    )


def _transaction_names(root: Path) -> tuple[str, ...]:
    backup_root = mutations.backup_root(root, git_private=False)
    return (
        tuple(sorted(path.name for path in backup_root.iterdir())) if backup_root.exists() else ()
    )


def _tree_payloads(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *args),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
