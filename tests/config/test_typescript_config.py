"""Tests TypeScript provider configuration fields."""

from __future__ import annotations

import pytest

from agent_maintainer.config import loader
from agent_maintainer.core.config import MaintainerConfig

ENV_TYPESCRIPT_SOURCE_WARN_FILES = 7
ENV_TYPESCRIPT_SOURCE_WARN_LINES = 275
ENV_TYPESCRIPT_BROAD_SUPPRESSION_WARN = 3


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
            "typescript_knip_command": [
                "pnpm",
                "exec",
                "knip",
                "--reporter",
                "json",
            ],
            "typescript_knip_profiles": ["full", "ci"],
            "typescript_dependency_cruiser_command": [
                "pnpm",
                "exec",
                "depcruise",
                "--output-type",
                "json",
                "src",
            ],
            "typescript_dependency_cruiser_profiles": ["full", "ci"],
        },
    )

    assert loaded.enable_typescript is True
    assert loaded.typescript_lint_command == ("npm", "run", "lint")
    assert loaded.typescript_lint_profiles == ("precommit", "ci")
    assert loaded.typescript_typecheck_command == ("npm", "run", "typecheck")
    assert loaded.typescript_typecheck_profiles == ("full",)
    assert loaded.typescript_test_command == ("npm", "test")
    assert loaded.typescript_test_profiles == ("manual",)
    assert loaded.typescript_knip_command == (
        "pnpm",
        "exec",
        "knip",
        "--reporter",
        "json",
    )
    assert loaded.typescript_knip_profiles == ("full", "ci")
    assert loaded.typescript_dependency_cruiser_command == (
        "pnpm",
        "exec",
        "depcruise",
        "--output-type",
        "json",
        "src",
    )
    assert loaded.typescript_dependency_cruiser_profiles == ("full", "ci")


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
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_KNIP_COMMAND",
        "pnpm,exec,knip,--reporter,json",
    )
    monkeypatch.setenv("AGENT_MAINTAINER_TYPESCRIPT_KNIP_PROFILES", "full,ci")
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_DEPENDENCY_CRUISER_COMMAND",
        "pnpm,exec,depcruise,--output-type,json,src",
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_DEPENDENCY_CRUISER_PROFILES",
        "full,ci",
    )

    loaded = loader.apply_env(MaintainerConfig())

    assert loaded.enable_typescript is True
    assert loaded.typescript_lint_command == ("pnpm", "lint")
    assert loaded.typescript_lint_profiles == ("fast", "precommit")
    assert loaded.typescript_typecheck_command == ("pnpm", "typecheck")
    assert loaded.typescript_typecheck_profiles == ("full", "ci")
    assert loaded.typescript_test_command == ("pnpm", "test")
    assert loaded.typescript_test_profiles == ("manual",)
    assert loaded.typescript_knip_command == (
        "pnpm",
        "exec",
        "knip",
        "--reporter",
        "json",
    )
    assert loaded.typescript_knip_profiles == ("full", "ci")
    assert loaded.typescript_dependency_cruiser_command == (
        "pnpm",
        "exec",
        "depcruise",
        "--output-type",
        "json",
        "src",
    )
    assert loaded.typescript_dependency_cruiser_profiles == ("full", "ci")


def test_typescript_knip_defaults_to_full_and_ci_profiles() -> None:
    """Knip stays out of the fast and precommit profiles by default."""

    loaded = MaintainerConfig()

    assert loaded.typescript_knip_command == ()
    assert loaded.typescript_knip_profiles == ("full", "ci")


def test_typescript_dependency_cruiser_defaults_to_full_and_ci_profiles() -> None:
    """Dependency-cruiser stays out of fast and precommit by default."""

    loaded = MaintainerConfig()

    assert loaded.typescript_dependency_cruiser_command == ()
    assert loaded.typescript_dependency_cruiser_profiles == ("full", "ci")


# docsync:evidence.start evidence.typescript.advisory_threshold_config_tests
def test_env_overrides_typescript_advisory_thresholds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TypeScript advisory thresholds load from environment variables."""

    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_ADVISORY_SOURCE_WARN_FILES",
        str(ENV_TYPESCRIPT_SOURCE_WARN_FILES),
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_ADVISORY_SOURCE_WARN_LINES",
        str(ENV_TYPESCRIPT_SOURCE_WARN_LINES),
    )
    monkeypatch.setenv(
        "AGENT_MAINTAINER_TYPESCRIPT_ADVISORY_BROAD_SUPPRESSION_WARN",
        str(ENV_TYPESCRIPT_BROAD_SUPPRESSION_WARN),
    )

    loaded = loader.apply_env(MaintainerConfig())

    assert loaded.typescript_advisory_source_warn_files == (ENV_TYPESCRIPT_SOURCE_WARN_FILES)
    assert loaded.typescript_advisory_source_warn_lines == ENV_TYPESCRIPT_SOURCE_WARN_LINES
    assert loaded.typescript_advisory_broad_suppression_warn == (
        ENV_TYPESCRIPT_BROAD_SUPPRESSION_WARN
    )


# docsync:evidence.end evidence.typescript.advisory_threshold_config_tests
