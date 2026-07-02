"""Tests experimental TypeScript provider check generation."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.ecosystems.typescript.provider import TypeScriptProvider
from agent_maintainer.models import CI_PROFILE, FULL_PROFILE, PRECOMMIT_PROFILE


def test_typescript_provider_is_disabled_by_default() -> None:
    """Default Python behavior does not grow TypeScript checks."""
    assert TypeScriptProvider().checks(_context(MaintainerConfig())) == []


def test_typescript_provider_builds_explicit_configured_commands() -> None:
    """Configured commands become profile-aware checks."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=("npm", "run", "lint"),
        typescript_typecheck_command=("npm", "run", "typecheck"),
        typescript_test_command=("npm", "test", "--", "--runInBand"),
    )

    checks = TypeScriptProvider().checks_by_name(_context(config))

    assert checks["typescript-lint"].command == ["npm", "run", "lint"]
    assert checks["typescript-lint"].required_executable == "npm"
    assert checks["typescript-lint"].profiles == {
        PRECOMMIT_PROFILE,
        FULL_PROFILE,
        CI_PROFILE,
    }
    assert checks["typescript-typecheck"].command == ["npm", "run", "typecheck"]
    assert checks["typescript-typecheck"].profiles == {FULL_PROFILE, CI_PROFILE}
    assert checks["typescript-test"].command == ["npm", "test", "--", "--runInBand"]
    assert checks["typescript-test"].profiles == {FULL_PROFILE, CI_PROFILE}


def test_typescript_provider_marks_missing_enabled_commands_as_skipped() -> None:
    """Enabled provider reports empty command fields explicitly."""
    config = replace(MaintainerConfig(), enable_typescript=True)

    checks = {check.name: check for check in TypeScriptProvider().checks(_context(config))}

    assert checks["typescript-lint"].optional_skip_reason is not None
    assert "typescript_lint_command" in checks["typescript-lint"].optional_skip_reason
    assert checks["typescript-typecheck"].optional_skip_reason is not None
    assert "typescript_typecheck_command" in checks["typescript-typecheck"].optional_skip_reason
    assert checks["typescript-test"].optional_skip_reason is not None
    assert "typescript_test_command" in checks["typescript-test"].optional_skip_reason


def test_typescript_provider_honors_configured_profiles() -> None:
    """Experimental provider profile lists are configurable."""
    config = replace(
        MaintainerConfig(),
        enable_typescript=True,
        typescript_lint_command=("pnpm", "lint"),
        typescript_lint_profiles=("fast",),
    )

    checks = {check.name: check for check in TypeScriptProvider().checks(_context(config))}

    assert checks["typescript-lint"].profiles == {"fast"}


def _context(config: MaintainerConfig) -> EcosystemCheckContext:
    """Build provider context for tests."""
    return EcosystemCheckContext(
        config=config,
        compare_branch="origin/main",
        package_paths=("src",),
    )
