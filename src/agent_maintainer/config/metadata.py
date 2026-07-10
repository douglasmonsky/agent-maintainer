"""Compatibility facade over the authoritative configuration field registry."""

from __future__ import annotations

from dataclasses import dataclass

from agent_maintainer.config import registry

CLI_OVERRIDE_NONE = registry.CLI_OVERRIDE_NONE
CLI_OVERRIDE_VERIFY = registry.CLI_OVERRIDE_VERIFY
STABILITY_BETA = registry.STABILITY_BETA
STABILITY_STABLE = registry.STABILITY_STABLE
VALID_CLI_OVERRIDE_STATUSES = frozenset((CLI_OVERRIDE_NONE, CLI_OVERRIDE_VERIFY))
VALID_STABILITY_LEVELS = frozenset((STABILITY_BETA, STABILITY_STABLE))

DIAGNOSTIC_TOML_KEYS = tuple(
    (field_name, registry.FIELD_SPECS[field_name].toml_key)
    for field_name in registry.DIAGNOSTIC_FIELD_MAP.values()
)
CLI_OVERRIDE_FIELDS = registry.CLI_OVERRIDE_FIELDS
STABLE_FIELDS = registry.STABLE_FIELDS


@dataclass(frozen=True)
class ConfigFieldMetadata:
    """Compatibility view of one public configuration field."""

    field_name: str
    toml_key: str
    env_var: str
    cli_override: str
    docs_label: str
    stability: str

    @property
    def has_env_override(self) -> bool:
        """Return whether the field has an environment override."""

        return bool(self.env_var)

    @property
    def has_cli_override(self) -> bool:
        """Return whether verifier CLI can override the field."""

        return self.cli_override != CLI_OVERRIDE_NONE


def env_vars_by_field() -> dict[str, str]:
    """Return registered environment variable names keyed by config field."""

    return {spec.field_name: spec.env_var for spec in registry.env_specs()}


def build_field_metadata() -> dict[str, ConfigFieldMetadata]:
    """Build compatibility metadata from the authoritative registry."""

    return {
        field_name: ConfigFieldMetadata(
            field_name=spec.field_name,
            toml_key=spec.toml_key,
            env_var=spec.env_var,
            cli_override=spec.cli_override,
            docs_label=spec.docs_label,
            stability=spec.stability,
        )
        for field_name, spec in registry.FIELD_SPECS.items()
    }


def toml_key_for(field_name: str) -> str:
    """Return the registered TOML key path for a config field."""

    return registry.FIELD_SPECS[field_name].toml_key


def cli_override_for(field_name: str) -> str:
    """Return verifier CLI override status for a config field."""

    return registry.FIELD_SPECS[field_name].cli_override


def docs_label_for(field_name: str) -> str:
    """Return the registered human-readable field label."""

    return registry.FIELD_SPECS[field_name].docs_label


def stability_for(field_name: str) -> str:
    """Return the registered public stability level."""

    return registry.FIELD_SPECS[field_name].stability


FIELD_METADATA = build_field_metadata()
