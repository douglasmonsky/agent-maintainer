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
    monkeypatch.setattr(maintainer_bootstrap, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        maintainer_bootstrap,
        "install_pre_commit",
        lambda repo_root: calls.append(("pre-commit", repo_root)) or INSTALL_STATUS,
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "install_hooks",
        lambda options: calls.append((options.client, options.target)) or 0,
    )
    monkeypatch.setattr(
        maintainer_bootstrap,
        "report_agent_hooks",
        lambda repo_root: calls.append(("report", repo_root)),
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
