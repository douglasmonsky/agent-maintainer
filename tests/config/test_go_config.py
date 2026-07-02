"""Tests Go provider configuration fields."""

from __future__ import annotations

import pytest

from agent_maintainer.config import loader
from agent_maintainer.core.config import MaintainerConfig


def test_pyproject_loads_go_provider_config() -> None:
    """Pyproject config can opt into explicit Go commands."""
    loaded = loader.apply_pyproject(
        MaintainerConfig(),
        {
            "enable_go": True,
            "go_format_command": ["gofmt", "-l", "."],
            "go_format_profiles": ["precommit", "ci"],
            "go_vet_command": ["go", "vet", "./..."],
            "go_vet_profiles": ["full"],
            "go_test_command": ["go", "test", "./..."],
            "go_test_profiles": ["manual"],
        },
    )

    assert loaded.enable_go is True
    assert _commands_by_field(loaded) == {
        "go_format_command": ("gofmt", "-l", "."),
        "go_vet_command": ("go", "vet", "./..."),
        "go_test_command": ("go", "test", "./..."),
    }
    assert _profiles_by_field(loaded) == {
        "go_format_profiles": ("precommit", "ci"),
        "go_vet_profiles": ("full",),
        "go_test_profiles": ("manual",),
    }


def test_env_overrides_go_provider_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables can configure Go command checks."""
    monkeypatch.setenv("AGENT_MAINTAINER_ENABLE_GO", "true")
    monkeypatch.setenv(
        "AGENT_MAINTAINER_GO_FORMAT_COMMAND",
        "gofmt,-l,.",
    )
    monkeypatch.setenv("AGENT_MAINTAINER_GO_FORMAT_PROFILES", "fast,precommit")
    monkeypatch.setenv("AGENT_MAINTAINER_GO_VET_COMMAND", "go,vet,./...")
    monkeypatch.setenv("AGENT_MAINTAINER_GO_VET_PROFILES", "full,ci")
    monkeypatch.setenv("AGENT_MAINTAINER_GO_TEST_COMMAND", "go,test,./...")
    monkeypatch.setenv("AGENT_MAINTAINER_GO_TEST_PROFILES", "manual")

    loaded = loader.apply_env(MaintainerConfig())

    assert loaded.enable_go is True
    assert _commands_by_field(loaded) == {
        "go_format_command": ("gofmt", "-l", "."),
        "go_vet_command": ("go", "vet", "./..."),
        "go_test_command": ("go", "test", "./..."),
    }
    assert _profiles_by_field(loaded) == {
        "go_format_profiles": ("fast", "precommit"),
        "go_vet_profiles": ("full", "ci"),
        "go_test_profiles": ("manual",),
    }


def _commands_by_field(config: MaintainerConfig) -> dict[str, tuple[str, ...]]:
    return {
        "go_format_command": config.go_format_command,
        "go_vet_command": config.go_vet_command,
        "go_test_command": config.go_test_command,
    }


def _profiles_by_field(config: MaintainerConfig) -> dict[str, tuple[str, ...]]:
    return {
        "go_format_profiles": config.go_format_profiles,
        "go_vet_profiles": config.go_vet_profiles,
        "go_test_profiles": config.go_test_profiles,
    }
