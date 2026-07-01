"""Tests strict Pyright ratchet configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config import loader as maintainer_config_loader
from agent_maintainer.core.config import MaintainerConfig

CONFIG_PYRIGHT_STRICT_MAX_ERRORS = 9
ENV_PYRIGHT_STRICT_MAX_ERRORS = 8


def test_pyright_strict_ratchet_config_loads(tmp_path: Path) -> None:
    """Strict Pyright ratchet settings load from pyproject."""

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.agent_maintainer]
pyright_strict_ratchet_enabled = true
pyright_strict_baseline = "config/strict-baseline.json"
pyright_strict_max_errors = 9
pyright_strict_profiles = ["manual", "security"]
""",
        encoding="utf-8",
    )

    loaded = maintainer_config_loader.apply_pyproject(
        MaintainerConfig(),
        maintainer_config_loader.read_pyproject(pyproject),
    )

    assert loaded.pyright_strict_ratchet_enabled is True
    assert loaded.pyright_strict_baseline == "config/strict-baseline.json"
    assert loaded.pyright_strict_max_errors == CONFIG_PYRIGHT_STRICT_MAX_ERRORS
    assert loaded.pyright_strict_profiles == ("manual", "security")


def test_environment_overrides_pyright_strict_ratchet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict Pyright ratchet settings load environment variables."""

    monkeypatch.setenv("AGENT_MAINTAINER_PYRIGHT_STRICT_RATCHET_ENABLED", "true")
    monkeypatch.setenv("AGENT_MAINTAINER_PYRIGHT_STRICT_BASELINE", "config/custom.json")
    monkeypatch.setenv(
        "AGENT_MAINTAINER_PYRIGHT_STRICT_MAX_ERRORS",
        str(ENV_PYRIGHT_STRICT_MAX_ERRORS),
    )
    monkeypatch.setenv("AGENT_MAINTAINER_PYRIGHT_STRICT_PROFILES", "manual,security")

    loaded = maintainer_config_loader.apply_env(MaintainerConfig())

    assert loaded.pyright_strict_ratchet_enabled is True
    assert loaded.pyright_strict_baseline == "config/custom.json"
    assert loaded.pyright_strict_max_errors == ENV_PYRIGHT_STRICT_MAX_ERRORS
    assert loaded.pyright_strict_profiles == ("manual", "security")
