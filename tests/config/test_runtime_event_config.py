"""Tests runtime event configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import loader as maintainer_config_loader
from agent_maintainer.core.config import MaintainerConfig

CONFIG_RUNTIME_EVENT_HISTORY_LIMIT = 5
ENV_RUNTIME_EVENT_HISTORY_LIMIT = 3


def set_envs(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    """Set environment overrides for one test."""
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_runtime_event_config_loads_pyproject_and_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime event settings load from config and environment overrides."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.agent_maintainer]
runtime_events_enabled = true
runtime_events_dir = ".custom-events"
runtime_event_history_limit = 5
runtime_event_level = "warning"
runtime_events_include_debug = true
""".strip(),
        encoding="utf-8",
    )

    loaded = maintainer_config_loader.apply_pyproject(
        MaintainerConfig(),
        maintainer_config_loader.read_pyproject(pyproject),
    )

    assert loaded.runtime_events_enabled is True
    assert loaded.runtime_events_dir == ".custom-events"
    assert loaded.runtime_event_history_limit == CONFIG_RUNTIME_EVENT_HISTORY_LIMIT
    assert loaded.runtime_event_level == "warning"
    assert loaded.runtime_events_include_debug is True

    set_envs(
        monkeypatch,
        {
            "AGENT_MAINTAINER_RUNTIME_EVENTS_ENABLED": "false",
            "AGENT_MAINTAINER_RUNTIME_EVENTS_DIR": ".env-events",
            "AGENT_MAINTAINER_RUNTIME_EVENT_HISTORY_LIMIT": "3",
            "AGENT_MAINTAINER_RUNTIME_EVENT_LEVEL": "error",
            "AGENT_MAINTAINER_RUNTIME_EVENTS_INCLUDE_DEBUG": "false",
        },
    )

    env_loaded = maintainer_config_loader.apply_env(MaintainerConfig())

    assert env_loaded.runtime_events_enabled is False
    assert env_loaded.runtime_events_dir == ".env-events"
    assert env_loaded.runtime_event_history_limit == ENV_RUNTIME_EVENT_HISTORY_LIMIT
    assert env_loaded.runtime_event_level == "error"
    assert env_loaded.runtime_events_include_debug is False
