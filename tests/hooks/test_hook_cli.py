"""Tests hook-management CLI dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.hooks import cli, lifecycle, manager

INSTALL_STATUS = 7
UNINSTALL_STATUS = 9
RUNTIME_STATUS = 11


@pytest.mark.parametrize("command", ("update", "uninstall"))
def test_lifecycle_help_stops_before_dispatch(
    command: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lifecycle help exits in argparse without calling a mutation handler."""

    def fail_mutation(_options: object) -> int:
        pytest.fail("help dispatched a mutation")

    monkeypatch.setattr(
        cli,
        f"{command}_hooks",
        fail_mutation,
    )

    with pytest.raises(SystemExit) as raised:
        cli.main([command, "--help"])

    assert raised.value.code == 0


def test_install_command_delegates_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Install subcommand builds manager options."""

    calls: list[manager.InstallOptions] = []

    def fake_install(options: manager.InstallOptions) -> int:
        calls.append(options)
        return INSTALL_STATUS

    monkeypatch.setattr(cli, "install_hooks", fake_install)

    status = cli.main(
        [
            "install",
            "codex",
            "--target",
            str(tmp_path),
            "--scope",
            manager.USER_SCOPE,
            "--force",
            "--yes",
            "--dry-run",
        ],
    )

    assert status == INSTALL_STATUS
    assert calls == [
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CODEX_CLIENT,
            scope=manager.USER_SCOPE,
            force=True,
            yes=True,
            dry_run=True,
        ),
    ]


def test_install_command_delegates_async_rewake_option(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Install subcommand passes Claude async rewake option."""
    calls: list[manager.InstallOptions] = []

    def fake_install(options: manager.InstallOptions) -> int:
        calls.append(options)
        return INSTALL_STATUS

    monkeypatch.setattr(cli, "install_hooks", fake_install)

    status = cli.main(
        [
            "install",
            "claude-code",
            "--target",
            str(tmp_path),
            "--dry-run",
            "--async-rewake-stop",
        ],
    )

    assert status == INSTALL_STATUS
    assert calls == [
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CLAUDE_CODE_CLIENT,
            dry_run=True,
            async_rewake_stop=True,
        ),
    ]


def test_update_command_delegates_install_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update uses the install-like lossless merge option contract."""

    calls: list[manager.InstallOptions] = []

    def update_hooks(options: manager.InstallOptions) -> int:
        calls.append(options)
        return INSTALL_STATUS

    monkeypatch.setattr(cli, "update_hooks", update_hooks)

    status = cli.main(["update", "codex", "--target", str(tmp_path), "--dry-run"])

    assert status == INSTALL_STATUS
    assert calls == [
        manager.InstallOptions(
            target=tmp_path,
            client=manager.CODEX_CLIENT,
            dry_run=True,
        )
    ]


def test_uninstall_command_delegates_removal_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uninstall passes scope, confirmation, preview, and ownership flags."""

    calls: list[lifecycle.UninstallOptions] = []

    def uninstall_hooks(options: lifecycle.UninstallOptions) -> int:
        calls.append(options)
        return UNINSTALL_STATUS

    monkeypatch.setattr(
        cli,
        "uninstall_hooks",
        uninstall_hooks,
    )

    status = cli.main(
        [
            "uninstall",
            "claude-code",
            "--target",
            str(tmp_path),
            "--scope",
            manager.USER_SCOPE,
            "--force",
            "--yes",
            "--dry-run",
        ]
    )

    assert status == UNINSTALL_STATUS
    assert calls == [
        lifecycle.UninstallOptions(
            target=tmp_path,
            client=manager.CLAUDE_CODE_CLIENT,
            scope=manager.USER_SCOPE,
            force=True,
            yes=True,
            dry_run=True,
        )
    ]


def test_status_command_delegates_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status subcommand delegates selected clients."""

    calls: list[tuple[Path, str, str]] = []

    def fake_status(target: Path, client: str, scope: str) -> int:
        calls.append((target, client, scope))
        return 3

    monkeypatch.setattr(cli, "status_hooks", fake_status)

    status = cli.main(["status", "claude-code", "--target", str(tmp_path)])

    assert status == 0
    assert calls == [(tmp_path, manager.CLAUDE_CODE_CLIENT, manager.REPO_SCOPE)]


def test_run_command_delegates_to_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hidden run subcommand delegates to the shared hook runtime."""

    calls: list[list[str]] = []

    def fake_runtime(argv: list[str]) -> int:
        calls.append(argv)
        return RUNTIME_STATUS

    monkeypatch.setattr(cli, "runtime_main", fake_runtime)

    status = cli.main(
        [
            "run",
            "--platform",
            "codex",
            "--event",
            "Stop",
            "--profile",
            "precommit",
            "--repo-root",
            str(tmp_path),
            "--async-rewake",
        ],
    )

    assert status == RUNTIME_STATUS
    assert calls == [
        [
            "--platform",
            "codex",
            "--event",
            "Stop",
            "--profile",
            "precommit",
            "--repo-root",
            str(tmp_path),
            "--async-rewake",
        ],
    ]


def test_pr_wait_command_delegates_to_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hidden PR wait subcommand delegates PR wait hook runtime."""
    calls: list[list[str]] = []

    def fake_pr_wait(argv: list[str]) -> int:
        calls.append(argv)
        return RUNTIME_STATUS

    monkeypatch.setattr(cli, "pr_wait_main", fake_pr_wait)

    status = cli.main(
        [
            "pr-wait",
            "--platform",
            "claude-code",
            "--repo-root",
            str(tmp_path),
            "--async-rewake",
        ]
    )

    assert status == RUNTIME_STATUS
    assert calls == [
        [
            "--platform",
            "claude-code",
            "--repo-root",
            str(tmp_path),
            "--async-rewake",
        ]
    ]
