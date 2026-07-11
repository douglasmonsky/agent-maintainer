"""Tests bootstrap hook setup behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.core import bootstrap as maintainer_bootstrap
from agent_maintainer.hooks import manager as hook_manager

INSTALL_STATUS = 12


def test_maintainer_install_runs_hook_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Install runs pre-commit setup and managed agent-hook setup."""

    calls: list[tuple[str, Path]] = []

    def project_root() -> Path:
        return tmp_path

    def install_pre_commit(repo_root: Path) -> int:
        calls.append(("pre-commit", repo_root))
        return INSTALL_STATUS

    def install_hooks(options: hook_manager.InstallOptions) -> int:
        calls.append((options.client, options.target))
        return 0

    def report_hooks(repo_root: Path) -> None:
        calls.append(("report", repo_root))

    monkeypatch.setattr(maintainer_bootstrap, "project_root", project_root)
    monkeypatch.setattr(
        maintainer_bootstrap,
        "install_pre_commit",
        install_pre_commit,
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "install_hooks",
        install_hooks,
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "report_agent_hooks",
        report_hooks,
    )

    assert maintainer_bootstrap.install() == INSTALL_STATUS
    assert calls == [
        ("pre-commit", tmp_path),
        (hook_manager.ALL_CLIENTS, tmp_path),
        ("report", tmp_path),
    ]


def test_maintainer_report_agent_hooks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Hook reporting prints status for supported clients."""

    maintainer_bootstrap.report_agent_hooks(tmp_path)

    output = capsys.readouterr().out
    assert "codex: config=missing scripts=missing" in output
    assert "claude-code: config=missing scripts=missing" in output


def test_maintainer_report_codex_hooks_keeps_compatibility(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Older tests/imports can still call the Codex report helper."""

    maintainer_bootstrap.report_codex_hooks(tmp_path)

    assert "codex:" in capsys.readouterr().out
