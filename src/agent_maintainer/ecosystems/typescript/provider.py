"""Experimental TypeScript and JavaScript ecosystem provider."""

from __future__ import annotations

from collections.abc import Iterable

from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import Check

DEPENDENCY_CRUISER_OUTPUT_LIMIT_CHARS = 5_000_000


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
            _configured_check(
                "typescript-knip",
                config.typescript_knip_command,
                config.typescript_knip_profiles,
                "typescript_knip_command",
            ),
            _configured_check(
                "typescript-dependency-cruiser",
                config.typescript_dependency_cruiser_command,
                config.typescript_dependency_cruiser_profiles,
                "typescript_dependency_cruiser_command",
            ),
        ]
        for workspace in config.workspaces:
            workspace_specs = (
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
                (
                    "typescript-knip",
                    workspace.typescript_knip_command,
                    config.typescript_knip_profiles,
                    f"workspaces.{workspace.name}.typescript_knip_command",
                ),
                (
                    "typescript-dependency-cruiser",
                    workspace.typescript_dependency_cruiser_command,
                    config.typescript_dependency_cruiser_profiles,
                    (f"workspaces.{workspace.name}.typescript_dependency_cruiser_command"),
                ),
            )
            checks.extend(
                _configured_check(
                    f"{check_name}:{workspace.name}",
                    command,
                    profiles,
                    config_field,
                )
                for check_name, command, profiles, config_field in workspace_specs
                if command
            )
        return checks


def _configured_check(
    name: str,
    command: tuple[str, ...],
    profiles: Iterable[str],
    config_field: str,
) -> Check:
    """Build a runnable or explicitly skipped configured-command check."""
    selected_profiles = frozenset(profiles)
    is_dependency_cruiser = name.partition(":")[0] == "typescript-dependency-cruiser"
    output_limit = DEPENDENCY_CRUISER_OUTPUT_LIMIT_CHARS if is_dependency_cruiser else None
    if not command:
        return Check(
            name,
            [name],
            selected_profiles,
            optional_skip_reason=(
                "TypeScript provider is enabled, but "
                f"[tool.agent_maintainer].{config_field} is empty"
            ),
            report_success_output=is_dependency_cruiser,
            output_limit_chars=output_limit,
        )
    return Check(
        name,
        list(command),
        selected_profiles,
        required_executable=command[0],
        report_success_output=is_dependency_cruiser,
        output_limit_chars=output_limit,
    )


# docsync:evidence.end evidence.typescript.provider_commands
