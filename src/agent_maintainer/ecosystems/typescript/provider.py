"""Experimental TypeScript and JavaScript ecosystem provider."""

from __future__ import annotations

from collections.abc import Iterable

from agent_maintainer.config.schema import VALID_TYPESCRIPT_PACKAGE_MANAGERS
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import SKIP_STATUS_UNSAFE_CONFIG, Check

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
            _configured_audit_check(
                "typescript-package-manager-audit",
                config.typescript_package_manager_audit_manager,
                config.typescript_package_manager_audit_command,
                config.typescript_package_manager_audit_profiles,
                "typescript_package_manager_audit_command",
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
            if workspace.typescript_package_manager_audit_command:
                checks.append(
                    _configured_audit_check(
                        f"typescript-package-manager-audit:{workspace.name}",
                        workspace.typescript_package_manager_audit_manager,
                        workspace.typescript_package_manager_audit_command,
                        config.typescript_package_manager_audit_profiles,
                        f"workspaces.{workspace.name}.typescript_package_manager_audit_command",
                    )
                )
        return checks


def _configured_check(
    name: str,
    command: tuple[str, ...],
    profiles: Iterable[str],
    config_field: str,
    *,
    structured_parser: str = "",
    structured_parser_manager: str = "",
) -> Check:
    """Build a runnable or explicitly skipped configured-command check."""
    selected_profiles = frozenset(profiles)
    is_dependency_cruiser = name.partition(":")[0] == "typescript-dependency-cruiser"
    output_limit = DEPENDENCY_CRUISER_OUTPUT_LIMIT_CHARS if is_dependency_cruiser else None
    report_success_output = is_dependency_cruiser or bool(structured_parser)
    if not command:
        return Check(
            name,
            [name],
            selected_profiles,
            optional_skip_reason=(
                "TypeScript provider is enabled, but "
                f"[tool.agent_maintainer].{config_field} is empty"
            ),
            report_success_output=report_success_output,
            output_limit_chars=output_limit,
            structured_parser=structured_parser,
            structured_parser_manager=structured_parser_manager,
        )
    return Check(
        name,
        list(command),
        selected_profiles,
        required_executable=command[0],
        report_success_output=report_success_output,
        output_limit_chars=output_limit,
        structured_parser=structured_parser,
        structured_parser_manager=structured_parser_manager,
    )


def _configured_audit_check(
    name: str,
    manager: str,
    command: tuple[str, ...],
    profiles: Iterable[str],
    config_field: str,
) -> Check:
    """Build an audit check only when its manager is explicit and supported."""

    parser_name = "typescript-package-manager-audit"
    selected_profiles = frozenset(profiles)
    if command and manager not in VALID_TYPESCRIPT_PACKAGE_MANAGERS:
        manager_field = config_field.removesuffix("_command") + "_manager"
        return Check(
            name,
            [name],
            selected_profiles,
            optional_skip_reason=(
                f"{config_field} requires {manager_field} to be one of: "
                f"{', '.join(sorted(VALID_TYPESCRIPT_PACKAGE_MANAGERS))}"
            ),
            optional_skip_status=SKIP_STATUS_UNSAFE_CONFIG,
            report_success_output=True,
            structured_parser=parser_name,
            structured_parser_manager="",
        )
    return _configured_check(
        name,
        command,
        profiles,
        config_field,
        structured_parser=parser_name,
        structured_parser_manager=manager,
    )


# docsync:evidence.end evidence.typescript.provider_commands
