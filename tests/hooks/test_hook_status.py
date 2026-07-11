"""Tests manifest-derived managed hook currentness status."""

from pathlib import Path

import pytest

from agent_client_hooks import adapters, templates
from agent_maintainer.hooks import manager


def test_adapter_status_reports_config_and_scripts(tmp_path: Path) -> None:
    """Adapter status reports missing and current lifecycle states."""

    adapter = adapters.CodexAdapter()
    missing = adapter.status(tmp_path, manager.REPO_SCOPE)
    assert missing == adapters.HookClientStatus(
        name=manager.CODEX_CLIENT,
        config_present=False,
        scripts_present=False,
        config_current=False,
        scripts_current=False,
        scripts_expected=True,
    )

    manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CODEX_CLIENT,
            force=True,
        )
    )

    present = adapter.status(tmp_path, manager.REPO_SCOPE)
    assert present == adapters.HookClientStatus(
        name=manager.CODEX_CLIENT,
        config_present=True,
        scripts_present=True,
        config_current=True,
        scripts_current=True,
        scripts_expected=True,
    )


def test_adapter_status_reports_present_repo_hooks(tmp_path: Path) -> None:
    """Adapter status reports current config and hook scripts together."""

    manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CLAUDE_CODE_CLIENT,
            force=True,
        ),
    )

    status = adapters.adapter_for_client(manager.CLAUDE_CODE_CLIENT).status(
        tmp_path,
        manager.REPO_SCOPE,
    )

    assert status.config_present is True
    assert status.scripts_present is True
    assert status.config_current is True
    assert status.scripts_current is True


def test_adapter_status_reports_stale_generated_script(tmp_path: Path) -> None:
    """Status distinguishes an existing stale wrapper from a current install."""

    manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CODEX_CLIENT,
            force=True,
        )
    )
    (tmp_path / templates.CODEX_POST_HOOK).write_text("stale\n", encoding="utf-8")

    status = adapters.CodexAdapter().status(tmp_path, manager.REPO_SCOPE)

    assert status.scripts_present is True
    assert status.scripts_current is False


def test_user_scope_status_does_not_require_repo_scripts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """User-scope status treats wrappers as intentionally unmanaged."""

    monkeypatch.setattr(adapters, "home", lambda: tmp_path)
    manager.install_hooks(
        manager.InstallOptions(
            target=tmp_path / "repo",
            client=manager.CODEX_CLIENT,
            scope=manager.USER_SCOPE,
            yes=True,
            force=True,
        )
    )

    status = adapters.CodexAdapter().status(tmp_path / "repo", manager.USER_SCOPE)

    assert status.config_current is True
    assert status.scripts_expected is False
    assert status.scripts_present is True
    assert status.scripts_current is True


def test_status_hooks_reports_currentness(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status output distinguishes current and missing managed files."""

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
    assert "codex: config=current scripts=current" in output
    assert "claude-code: config=missing scripts=missing" in output
