"""Tests TypeScript provider configuration fields."""

from __future__ import annotations

import pytest

from agent_maintainer.config import loader
from agent_maintainer.core.config import MaintainerConfig


def test_pyproject_loads_typescript_provider_config() -> None:
    """Pyproject config can opt into explicit TypeScript commands."""
    loaded = loader.apply_pyproject(
        MaintainerConfig(),
        {
            "enable_typescript": True,
            "typescript_lint_command": ["npm", "run", "lint"],
            "typescript_lint_profiles": ["precommit", "ci"],
            "typescript_typecheck_command": ["npm", "run", "typecheck"],
            "typescript_typecheck_profiles": ["full"],
            "typescript_test_command": ["npm", "test"],
            "typescript_test_profiles": ["manual"],
        },
    )

    assert loaded.enable_typescript is True
    assert loaded.typescript_lint_command == ("npm", "run", "lint")
    assert loaded.typescript_lint_profiles == ("precommit", "ci")
    assert loaded.typescript_typecheck_command == ("npm", "run", "typecheck")
    assert loaded.typescript_typecheck_profiles == ("full",)
    assert loaded.typescript_test_command == ("npm", "test")
    assert loaded.typescript_test_profiles == ("manual",)


def test_env_overrides_typescript_provider_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables can configure TypeScript command checks."""
    monkeypatch.setenv("AGENT_MAINTAINER_ENABLE_TYPESCRIPT", "true")
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_LINT_COMMAND",
        "pnpm,lint",
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_LINT_PROFILES",
        "fast,precommit",
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_TYPECHECK_COMMAND",
        "pnpm,typecheck",
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_TYPECHECK_PROFILES",
        "full,ci",
    )
    monkeypatch.setenv("AGENT_MAINTAINER_TYPESCRIPT_TEST_COMMAND", "pnpm,test")
    monkeypatch.setenv("AGENT_MAINTAINER_TYPESCRIPT_TEST_PROFILES", "manual")

    loaded = loader.apply_env(MaintainerConfig())

    assert loaded.enable_typescript is True
    assert loaded.typescript_lint_command == ("pnpm", "lint")
    assert loaded.typescript_lint_profiles == ("fast", "precommit")
    assert loaded.typescript_typecheck_command == ("pnpm", "typecheck")
    assert loaded.typescript_typecheck_profiles == ("full", "ci")
    assert loaded.typescript_test_command == ("pnpm", "test")
    assert loaded.typescript_test_profiles == ("manual",)
