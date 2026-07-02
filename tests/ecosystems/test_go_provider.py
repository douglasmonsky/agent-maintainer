"""Tests experimental Go provider check generation."""

from __future__ import annotations

from dataclasses import replace

from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.go.provider import GoProvider
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import CI_PROFILE, FULL_PROFILE, PRECOMMIT_PROFILE, Check


def test_go_provider_is_disabled_by_default() -> None:
    """Default Python behavior does not grow Go checks."""
    assert GoProvider().checks(_context(MaintainerConfig())) == []


def test_go_provider_builds_commands() -> None:
    """Configured Go commands become profile-aware checks."""
    config = replace(
        MaintainerConfig(),
        enable_go=True,
        go_format_command=("gofmt", "-l", "."),
        go_vet_command=("go", "vet", "./..."),
        go_test_command=("go", "test", "./..."),
    )

    checks = GoProvider().checks_by_name(_context(config))

    assert {name: check.command for name, check in checks.items()} == {
        "go-format": ["gofmt", "-l", "."],
        "go-vet": ["go", "vet", "./..."],
        "go-test": ["go", "test", "./..."],
    }
    assert checks["go-format"].profiles == {PRECOMMIT_PROFILE, FULL_PROFILE, CI_PROFILE}
    assert checks["go-vet"].profiles == {FULL_PROFILE, CI_PROFILE}
    assert checks["go-test"].required_executable == "go"


def test_go_provider_skips_missing_commands() -> None:
    """Enabled provider reports empty command fields explicitly."""
    config = replace(MaintainerConfig(), enable_go=True)
    checks = {check.name: check for check in GoProvider().checks(_context(config))}

    assert _skip_reason(checks["go-format"], "go_format_command")
    assert _skip_reason(checks["go-vet"], "go_vet_command")
    assert _skip_reason(checks["go-test"], "go_test_command")


def _context(config: MaintainerConfig) -> EcosystemCheckContext:
    return EcosystemCheckContext(
        config=config,
        compare_branch="origin/main",
        package_paths=("src",),
    )


def _skip_reason(check: Check, field_name: str) -> bool:
    reason = check.optional_skip_reason
    return reason is not None and field_name in reason
