"""Doctor checks for experimental TypeScript provider setup."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.doctor.support.models import (
    ACTIVE,
    MISSING,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)

COMMAND_FIELDS = (
    ("typescript-lint", "typescript_lint_command"),
    ("typescript-typecheck", "typescript_typecheck_command"),
    ("typescript-test", "typescript_test_command"),
)
TypeScriptCommand = tuple[str, tuple[str, ...]]
TypeScriptCommands = tuple[TypeScriptCommand, ...]


def check_typescript_provider(config: MaintainerConfig) -> tuple[DoctorResult, ...]:
    """Return TypeScript provider setup health rows."""
    if not config.enable_typescript:
        return ()
    commands = configured_commands(config)
    if not commands:
        return (
            DoctorResult(
                "typescript-provider",
                WARNING,
                "TypeScript provider enabled but no commands are configured.",
                state=UNSAFE_CONFIG,
                hint=(
                    "Set typescript_lint_command, typescript_typecheck_command, "
                    "or typescript_test_command; or disable enable_typescript."
                ),
            ),
        )
    missing = missing_executables(commands)
    if missing:
        missing_names = ", ".join(missing)
        return (
            DoctorResult(
                "typescript-provider",
                WARNING,
                f"Missing TypeScript command executable(s): {missing_names}.",
                state=MISSING,
                hint="Install missing tools or update TypeScript command fields.",
            ),
        )
    names = ", ".join(name for name, _command in commands)
    return (
        DoctorResult(
            "typescript-provider",
            OK,
            f"Configured TypeScript command checks: {names}.",
            state=ACTIVE,
        ),
    )


def configured_commands(config: MaintainerConfig) -> TypeScriptCommands:
    """Return configured TypeScript check commands."""
    return tuple(
        (check_name, command)
        for check_name, field_name in COMMAND_FIELDS
        if (command := getattr(config, field_name))
    )


def missing_executables(
    commands: TypeScriptCommands,
) -> list[str]:
    """Return configured TypeScript command executables missing from PATH."""
    path = executable_search_path()
    return [
        f"{check_name} -> {command[0]}"
        for check_name, command in commands
        if shutil.which(command[0], path=path) is None
    ]


def executable_search_path() -> str:
    """Return PATH with common repo-local tool directories prepended."""
    local_dirs = [
        str(Path(relative))
        for relative in ("node_modules/.bin", ".venv/bin", "venv/bin")
        if Path(relative).is_dir()
    ]
    existing_path = os.environ.get("PATH", "")
    return (
        os.pathsep.join((*local_dirs, existing_path))
        if existing_path
        else os.pathsep.join(local_dirs)
    )
