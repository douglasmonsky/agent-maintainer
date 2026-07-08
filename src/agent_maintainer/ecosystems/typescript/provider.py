"""Experimental TypeScript and JavaScript ecosystem provider."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import Check


class _TypeScriptProfileConfig(Protocol):
    """TypeScript profile fields needed by workspace check construction."""

    typescript_lint_profiles: Iterable[str]
    typescript_typecheck_profiles: Iterable[str]
    typescript_test_profiles: Iterable[str]


class _TypeScriptWorkspaceConfig(Protocol):
    """Workspace TypeScript command fields needed by check construction."""

    name: str
    typescript_lint_command: tuple[str, ...]
    typescript_typecheck_command: tuple[str, ...]
    typescript_test_command: tuple[str, ...]


# docsync:evidence.start evidence.typescript.provider_commands
class TypeScriptProvider:
    """Build explicitly configured TypeScript/JavaScript checks."""

    name = "typescript"

    def checks_by_name(self, context: EcosystemCheckContext) -> dict[str, Check]:
        """Return TypeScript checks keyed by stable check name."""
        return {check.name: check for check in self.checks(context)}

    def checks(self, context: EcosystemCheckContext) -> list[Check]:
        """Return configured TypeScript ecosystem checks."""
        config = context.config
        if not config.enable_typescript:
            return []
        checks = [
            _configured_check(
                "typescript-lint",
                config.typescript_lint_command,
                config.typescript_lint_profiles,
                "typescript_lint_command",
            ),
            _configured_check(
                "typescript-typecheck",
                config.typescript_typecheck_command,
                config.typescript_typecheck_profiles,
                "typescript_typecheck_command",
            ),
            _configured_check(
                "typescript-test",
                config.typescript_test_command,
                config.typescript_test_profiles,
                "typescript_test_command",
            ),
        ]
        for workspace in config.workspaces:
            checks.extend(
                _workspace_configured_checks(
                    workspace,
                    config,
                ),
            )
        return checks


def _workspace_configured_checks(
    workspace: _TypeScriptWorkspaceConfig,
    config: _TypeScriptProfileConfig,
) -> list[Check]:
    """Return explicitly owned TypeScript checks for one workspace."""
    specs = (
        (
            "typescript-lint",
            workspace.typescript_lint_command,
            config.typescript_lint_profiles,
            f"workspaces.{workspace.name}.typescript_lint_command",
        ),
        (
            "typescript-typecheck",
            workspace.typescript_typecheck_command,
            config.typescript_typecheck_profiles,
            f"workspaces.{workspace.name}.typescript_typecheck_command",
        ),
        (
            "typescript-test",
            workspace.typescript_test_command,
            config.typescript_test_profiles,
            f"workspaces.{workspace.name}.typescript_test_command",
        ),
    )
    return [
        _configured_check(
            f"{check_name}:{workspace.name}",
            command,
            profiles,
            config_field,
        )
        for check_name, command, profiles, config_field in specs
        if command
    ]


def _configured_check(
    name: str,
    command: tuple[str, ...],
    profiles: Iterable[str],
    config_field: str,
) -> Check:
    """Build a runnable or explicitly skipped configured-command check."""
    selected_profiles = frozenset(profiles)
    if not command:
        return Check(
            name,
            [name],
            selected_profiles,
            optional_skip_reason=(
                "TypeScript provider is enabled, but "
                f"[tool.agent_maintainer].{config_field} is empty"
            ),
        )
    return Check(
        name,
        list(command),
        selected_profiles,
        required_executable=command[0],
    )


# docsync:evidence.end evidence.typescript.provider_commands
