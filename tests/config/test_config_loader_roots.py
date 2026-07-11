"""Tests root-aware Agent Maintainer config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import coercion
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


def test_loader_compatibility_helpers(tmp_path: Path) -> None:
    """Established loader helpers retain their provider-neutral behavior."""

    (tmp_path / "agent-maintainer.toml").write_text('source_roots = ["lib"]\n', encoding="utf-8")
    updates: dict[str, object] = {}
    maintainer_config_loader.merge_env_values(
        updates,
        (("change_warn_lines", "EXAMPLE_WARN_LINES"),),
        coercion.as_int,
        environment={"EXAMPLE_WARN_LINES": "42"},
    )

    assert maintainer_config_loader.read_config(tmp_path) == {"source_roots": ["lib"]}
    assert updates == {"change_warn_lines": 42}
