"""Tests hook runtime repository opt-in detection."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.hooks import runtime

ENCODING = "utf-8"


def test_maintainer_configured_requires_table(tmp_path: Path) -> None:
    """Hook opt-in requires the Agent Maintainer config table."""

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'example'\n",
        encoding=ENCODING,
    )
    assert runtime.maintainer_configured(tmp_path) is False


def test_maintainer_configured_accepts_table(tmp_path: Path) -> None:
    """Hook opt-in accepts repositories with Agent Maintainer config."""

    (tmp_path / "pyproject.toml").write_text(
        "[tool.agent_maintainer]\n",
        encoding=ENCODING,
    )
    assert runtime.maintainer_configured(tmp_path) is True
