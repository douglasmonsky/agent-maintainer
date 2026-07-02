"""Tests internal ecosystem provider registry metadata."""

from __future__ import annotations

from agent_maintainer.ecosystems.models import ProviderMaturity
from agent_maintainer.ecosystems.registry import (
    builtin_provider_metadata,
    experimental_check_providers,
    python_provider,
)


def test_provider_metadata_names_and_maturity() -> None:
    """Built-in providers expose maturity without publishing plugin API."""
    providers = {metadata.name: metadata for metadata in builtin_provider_metadata()}

    assert tuple(providers) == ("python", "typescript")
    assert providers["python"].maturity == ProviderMaturity.CORE
    assert providers["typescript"].maturity == ProviderMaturity.EXPERIMENTAL


def test_provider_metadata_enabled_fields() -> None:
    """Built-in providers declare enabled-state config fields."""
    providers = {metadata.name: metadata for metadata in builtin_provider_metadata()}

    assert providers["python"].enabled_by_default is True
    assert providers["python"].enabled_field is None
    assert providers["typescript"].enabled_field == "enable_typescript"


def test_configured_provider_command_fields() -> None:
    """Experimental providers make configured-command ownership explicit."""
    providers = {metadata.name: metadata for metadata in builtin_provider_metadata()}

    assert [spec.config_field for spec in providers["typescript"].command_specs] == [
        "typescript_lint_command",
        "typescript_typecheck_command",
        "typescript_test_command",
    ]


def test_registry_provider_order() -> None:
    """Catalog can preserve Python ordering while appending experiments."""
    assert python_provider().name == "python"
    assert [provider.name for provider in experimental_check_providers()] == [
        "typescript",
    ]
