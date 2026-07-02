"""Doctor checks for built-in ecosystem provider setup."""

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
from agent_maintainer.ecosystems.models import ProviderMetadata
from agent_maintainer.ecosystems.registry import (
    TYPESCRIPT_PROVIDER,
    builtin_provider_metadata,
)

ConfiguredCommand = tuple[str, str, tuple[str, ...]]
ConfiguredCommands = tuple[ConfiguredCommand, ...]


def check_provider_status(config: MaintainerConfig) -> DoctorResult:
    """Return a compact summary of built-in provider state."""
    providers = ", ".join(
        provider_status(metadata, config) for metadata in builtin_provider_metadata()
    )
    return DoctorResult(
        "ecosystem-providers",
        OK,
        providers,
        state=ACTIVE,
    )


def check_typescript_provider(config: MaintainerConfig) -> tuple[DoctorResult, ...]:
    """Return TypeScript provider setup health rows."""
    return check_configured_command_provider(config, TYPESCRIPT_PROVIDER)


def check_configured_command_provider(
    config: MaintainerConfig,
    metadata: ProviderMetadata,
) -> tuple[DoctorResult, ...]:
    """Return setup health rows for one configured-command provider."""
    if not provider_enabled(metadata, config):
        return ()

    commands = configured_commands(config, metadata)
    if not commands:
        return (
            DoctorResult(
                provider_row_name(metadata),
                WARNING,
                f"{metadata.display_name} provider enabled but no commands are configured.",
                state=UNSAFE_CONFIG,
                hint=empty_command_hint(metadata),
            ),
        )

    missing = missing_executables(commands)
    if missing:
        missing_names = ", ".join(missing)
        return (
            DoctorResult(
                provider_row_name(metadata),
                WARNING,
                f"Missing {metadata.display_name} command executable(s): {missing_names}.",
                state=MISSING,
                hint=f"Install missing tools or update {metadata.display_name} command fields.",
            ),
        )

    names = ", ".join(check_name for check_name, _field_name, _command in commands)
    return (
        DoctorResult(
            provider_row_name(metadata),
            OK,
            f"Configured {metadata.display_name} command checks: {names}.",
            state=ACTIVE,
        ),
    )


def provider_status(metadata: ProviderMetadata, config: MaintainerConfig) -> str:
    """Return one compact provider status fragment."""
    state = "active" if provider_enabled(metadata, config) else "disabled"
    status = " ".join((metadata.display_name, metadata.maturity.value, state))
    return f"{status} ({metadata.docs_path})"


def provider_enabled(metadata: ProviderMetadata, config: MaintainerConfig) -> bool:
    """Return whether provider is enabled for this config."""
    if metadata.enabled_field is None:
        return metadata.enabled_by_default
    return bool(getattr(config, metadata.enabled_field))


def provider_row_name(metadata: ProviderMetadata) -> str:
    """Return stable doctor row name for a provider."""
    return f"{metadata.name}-provider"


def empty_command_hint(metadata: ProviderMetadata) -> str:
    """Return repair hint for enabled provider without configured commands."""
    field_names = [spec.config_field for spec in metadata.command_specs]
    if not field_names:
        return "No provider command fields are available."
    fields = ", ".join(field_names[:-1])
    fields = ", or ".join((fields, field_names[-1])) if fields else field_names[-1]
    disable_hint = "." if metadata.enabled_field is None else f"; disable {metadata.enabled_field}."
    return f"Set {fields}{disable_hint}"


def configured_commands(
    config: MaintainerConfig,
    metadata: ProviderMetadata,
) -> ConfiguredCommands:
    """Return configured provider command tuples."""
    return tuple(
        (spec.check_name, spec.config_field, command)
        for spec in metadata.command_specs
        if (command := getattr(config, spec.config_field))
    )


def missing_executables(commands: ConfiguredCommands) -> tuple[str, ...]:
    """Return configured commands whose executable cannot be resolved."""
    missing: list[str] = []
    for check_name, _field_name, command in commands:
        executable = command[0]
        if not executable_exists(executable):
            missing.append(f"{check_name} ({executable})")
    return tuple(missing)


def executable_exists(executable: str) -> bool:
    """Return whether executable is available on PATH or local tool dirs."""
    search_path = path_with_local_bins(Path.cwd())
    return shutil.which(executable, path=search_path) is not None


def path_with_local_bins(repo_root: Path) -> str:
    """Return PATH extended with local venv and Node tool directories."""
    local_dirs = [
        str(repo_root / ".venv" / "bin"),
        str(repo_root / "venv" / "bin"),
        str(repo_root / "node_modules" / ".bin"),
    ]
    existing_path = os.environ.get("PATH", "")
    if existing_path:
        return os.pathsep.join((*local_dirs, existing_path))
    return os.pathsep.join(local_dirs)
