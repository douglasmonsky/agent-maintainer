"""Tests root-aware Agent Maintainer config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import loader as maintainer_config_loader


def test_load_config_reads_explicit_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit repo roots load pyproject config without changing process cwd."""

    outside = tmp_path / "outside"
    repo_root = tmp_path / "repo"
    outside.mkdir()
    repo_root.mkdir()
    monkeypatch.chdir(outside)
    (repo_root / "pyproject.toml").write_text(
        "[tool.agent_maintainer]\nsource_roots = ['pkg']\n",
        encoding="utf-8",
    )

    loaded = maintainer_config_loader.load_config(repo_root)

    assert loaded.source_roots == ("pkg",)
    assert Path.cwd() == outside


def test_load_config_reads_explicit_neutral_config_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit repo roots also load neutral config files."""

    outside = tmp_path / "outside"
    repo_root = tmp_path / "repo"
    outside.mkdir()
    repo_root.mkdir()
    monkeypatch.chdir(outside)
    (repo_root / "agent-maintainer.toml").write_text(
        "source_roots = ['app']\n",
        encoding="utf-8",
    )

    loaded = maintainer_config_loader.load_config(repo_root)

    assert loaded.source_roots == ("app",)
    assert Path.cwd() == outside
