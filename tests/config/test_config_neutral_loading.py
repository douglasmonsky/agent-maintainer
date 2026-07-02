"""Tests neutral Agent Maintainer config loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import loader as maintainer_config_loader
from agent_maintainer.core.config import MaintainerConfig

CONFIG_RUN_HISTORY_LIMIT = 7


def test_read_neutral_config_loads_top_level_config(tmp_path: Path) -> None:
    """Neutral config files use top-level Agent Maintainer fields."""
    config_path = tmp_path / ".agent-maintainer" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
source_roots = ["lib"]
test_roots = ["specs"]
mode = "fresh-strict"

[diagnostics]
enabled = false
log_dir = ".custom-verify-logs"
run_history_limit = 7
""",
        encoding="utf-8",
    )

    raw = maintainer_config_loader.read_neutral_config((config_path,))
    loaded = maintainer_config_loader.apply_pyproject(MaintainerConfig(), raw)

    assert loaded.source_roots == ("lib",)
    assert loaded.test_roots == ("specs",)
    assert loaded.mode == "fresh-strict"
    assert loaded.enable_wemake is True
    assert loaded.diagnostic_artifacts_enabled is False
    assert loaded.diagnostic_artifacts_dir == ".custom-verify-logs"
    assert loaded.diagnostic_run_history_limit == CONFIG_RUN_HISTORY_LIMIT


def test_load_config_prefers_pyproject_table_over_neutral_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing pyproject config keeps precedence over neutral files."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.agent_maintainer]
source_roots = ["pyproject-src"]
""",
        encoding="utf-8",
    )
    (tmp_path / ".agent-maintainer").mkdir()
    (tmp_path / ".agent-maintainer" / "config.toml").write_text(
        'source_roots = ["neutral-src"]\n',
        encoding="utf-8",
    )

    loaded = maintainer_config_loader.load_config()

    assert loaded.source_roots == ("pyproject-src",)


def test_load_config_uses_neutral_config_when_pyproject_table_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neutral config supports repos without pyproject tool tables."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\n',
        encoding="utf-8",
    )
    (tmp_path / "agent-maintainer.toml").write_text(
        'source_roots = ["neutral-src"]\n',
        encoding="utf-8",
    )

    loaded = maintainer_config_loader.load_config()

    assert loaded.source_roots == ("neutral-src",)


def test_environment_overrides_neutral_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment overrides still win over neutral file config."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agent-maintainer.toml").write_text(
        'source_roots = ["neutral-src"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_MAINTAINER_SOURCE_ROOTS", "env-src")

    loaded = maintainer_config_loader.load_config()

    assert loaded.source_roots == ("env-src",)


def test_neutral_config_prefers_dot_directory_file(tmp_path: Path) -> None:
    """Neutral config precedence is deterministic when both paths exist."""
    dot_config = tmp_path / ".agent-maintainer" / "config.toml"
    root_config = tmp_path / "agent-maintainer.toml"
    dot_config.parent.mkdir()
    dot_config.write_text('source_roots = ["dot-src"]\n', encoding="utf-8")
    root_config.write_text('source_roots = ["root-src"]\n', encoding="utf-8")

    raw = maintainer_config_loader.read_neutral_config((dot_config, root_config))

    assert raw["source_roots"] == ["dot-src"]
