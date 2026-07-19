"""Tests internal ecosystem provider registry metadata."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor.support.providers import provider_enabled
from agent_maintainer.ecosystems.models import ProviderMaturity
from agent_maintainer.ecosystems.registry import (
    advisory_suppression_findings,
    builtin_provider_metadata,
    classification_candidates,
    experimental_check_providers,
    python_provider,
)


def test_provider_metadata_names_and_maturity() -> None:
    """Built-in providers expose maturity without publishing plugin API."""
    # docsync:evidence.start evidence.provider_registry.active_providers
    providers = {metadata.name: metadata for metadata in builtin_provider_metadata()}

    assert tuple(providers) == ("python", "typescript", "java")
    assert providers["python"].maturity == ProviderMaturity.CORE
    assert providers["typescript"].maturity == ProviderMaturity.EXPERIMENTAL
    assert providers["java"].maturity == ProviderMaturity.EXPERIMENTAL
    # docsync:evidence.end evidence.provider_registry.active_providers


def test_provider_metadata_enabled_fields() -> None:
    """Built-in providers declare enabled-state config fields."""
    providers = {metadata.name: metadata for metadata in builtin_provider_metadata()}

    assert providers["python"].enabled_by_default is True
    assert providers["python"].enabled_field is None
    assert providers["typescript"].enabled_field == "enable_typescript"
    assert providers["java"].enabled_field == "java.enabled"
    assert MaintainerConfig().enable_typescript is False
    assert provider_enabled(providers["typescript"], MaintainerConfig(enable_typescript=True))
    assert provider_enabled(providers["java"], MaintainerConfig()) is False
    assert provider_enabled(
        providers["java"],
        MaintainerConfig(java=JavaGradleConfig(enabled=True)),
    )


def test_configured_provider_command_fields() -> None:
    """Experimental providers make configured-command ownership explicit."""
    providers = {metadata.name: metadata for metadata in builtin_provider_metadata()}

    assert [spec.config_field for spec in providers["typescript"].command_specs] == [
        "typescript_lint_command",
        "typescript_typecheck_command",
        "typescript_test_command",
        "typescript_knip_command",
        "typescript_dependency_cruiser_command",
    ]
    assert {"architecture", "dead-code", "dependency-hygiene"} <= set(
        providers["typescript"].capabilities
    )


def test_archived_go_provider_has_no_active_config_surface() -> None:
    """Go experiment remains archived outside active provider configuration."""
    # docsync:evidence.start evidence.provider_registry.no_active_go
    config_fields = {field.name for field in fields(MaintainerConfig)}
    assert (
        not {
            "enable_go",
            "go_format_command",
            "go_vet_command",
            "go_test_command",
            "go_format_profiles",
            "go_vet_profiles",
            "go_test_profiles",
        }
        & config_fields
    )
    # docsync:evidence.end evidence.provider_registry.no_active_go


def test_registry_provider_order() -> None:
    """Catalog can preserve Python ordering while appending experiments."""
    assert python_provider().name == "python"
    assert [provider.name for provider in experimental_check_providers()] == [
        "typescript",
        "java",
    ]


def test_registry_owns_classification_dispatch() -> None:
    """Registry exposes active provider classification candidates."""
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",))

    python_candidates = classification_candidates("src/pkg/app.py", config)
    disabled_candidates = classification_candidates("src/app.ts", config)
    enabled_candidates = classification_candidates(
        "src/app.ts",
        MaintainerConfig(enable_typescript=True),
    )

    assert [candidate.ecosystem for candidate in python_candidates] == ["python"]
    assert disabled_candidates == ()
    assert [candidate.ecosystem for candidate in enabled_candidates] == ["typescript"]
    java_candidates = classification_candidates(
        Path("src/main/java/App.java"),
        MaintainerConfig(java=JavaGradleConfig(enabled=True)),
    )
    assert [candidate.ecosystem for candidate in java_candidates] == ["java"]
    assert classification_candidates("src/main.cpp", config) == ()
    cpp_candidates = classification_candidates(
        "src/main.cpp",
        MaintainerConfig(cpp=CppCmakeConfig(enabled=True)),
    )
    assert [candidate.ecosystem for candidate in cpp_candidates] == ["cpp"]


def test_registry_owns_advisory_suppression_dispatch() -> None:
    """Registry exposes advisory suppression classifiers by ecosystem."""
    findings = advisory_suppression_findings("typescript", "// eslint-disable")

    assert len(findings) == 1
    assert findings[0].ecosystem == "typescript"
    assert findings[0].broad is True
    cpp_findings = advisory_suppression_findings(
        "cpp",
        "uninitvar",
        "cppcheck-suppressions.txt",
    )
    assert [(item.kind, item.broad) for item in cpp_findings] == [
        ("cppcheck-suppression-file", False)
    ]
    assert advisory_suppression_findings("unknown", "// eslint-disable") == ()


def test_provider_dispatch_callers_use_registry() -> None:
    """Assessment dispatch callers do not import concrete provider helpers."""
    file_changes = Path("src/agent_maintainer/ecosystems/file_changes.py").read_text()
    reviewability = Path("src/agent_maintainer/assess/reviewability.py").read_text()

    assert "ecosystems.python import classification" not in file_changes
    assert "ecosystems.typescript import" not in file_changes
    assert "ecosystems.typescript import suppressions" not in reviewability
