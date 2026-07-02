"""Experimental TypeScript and JavaScript ecosystem provider."""

from __future__ import annotations

from collections.abc import Iterable

from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import Check


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
        return [
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
