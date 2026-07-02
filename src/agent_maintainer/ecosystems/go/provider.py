"""Experimental Go ecosystem provider."""

from __future__ import annotations

from collections.abc import Iterable

from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import Check


class GoProvider:
    """Build explicitly configured Go checks."""

    name = "go"

    def checks_by_name(self, context: EcosystemCheckContext) -> dict[str, Check]:
        """Return Go checks keyed by stable check name."""
        return {check.name: check for check in self.checks(context)}

    def checks(self, context: EcosystemCheckContext) -> list[Check]:
        """Return configured Go ecosystem checks."""
        config = context.config
        if not config.enable_go:
            return []

        return [
            _configured_check(
                "go-format",
                config.go_format_command,
                config.go_format_profiles,
                "go_format_command",
            ),
            _configured_check(
                "go-vet",
                config.go_vet_command,
                config.go_vet_profiles,
                "go_vet_command",
            ),
            _configured_check(
                "go-test",
                config.go_test_command,
                config.go_test_profiles,
                "go_test_command",
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
                f"Go provider enabled, but [tool.agent_maintainer].{config_field} is empty"
            ),
        )
    return Check(
        name,
        list(command),
        selected_profiles,
        required_executable=command[0],
    )
