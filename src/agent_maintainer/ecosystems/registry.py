"""Internal registry for built-in ecosystem providers."""

from __future__ import annotations

from agent_maintainer.ecosystems.go.provider import GoProvider
from agent_maintainer.ecosystems.models import (
    ProviderCommandSpec,
    ProviderMaturity,
    ProviderMetadata,
)
from agent_maintainer.ecosystems.python.provider import PythonProvider
from agent_maintainer.ecosystems.typescript.provider import TypeScriptProvider

PYTHON_PROVIDER = ProviderMetadata(
    name="python",
    display_name="Python",
    maturity=ProviderMaturity.CORE,
    docs_path="README.md",
    capabilities=(
        "format",
        "lint",
        "typecheck",
        "test",
        "coverage",
        "diff-coverage",
        "mutation",
        "security",
        "dead-code",
        "dependency-hygiene",
    ),
    enabled_by_default=True,
)

TYPESCRIPT_PROVIDER = ProviderMetadata(
    name="typescript",
    display_name="TypeScript/JavaScript",
    maturity=ProviderMaturity.EXPERIMENTAL,
    docs_path="docs/typescript-javascript-provider.md",
    capabilities=("lint", "typecheck", "test", "classification", "repair-facts"),
    enabled_field="enable_typescript",
    command_specs=(
        ProviderCommandSpec("typescript-lint", "typescript_lint_command"),
        ProviderCommandSpec("typescript-typecheck", "typescript_typecheck_command"),
        ProviderCommandSpec("typescript-test", "typescript_test_command"),
    ),
)

GO_PROVIDER = ProviderMetadata(
    name="go",
    display_name="Go",
    maturity=ProviderMaturity.EXPERIMENTAL,
    docs_path="docs/go-provider.md",
    capabilities=("format", "vet", "test", "classification"),
    enabled_field="enable_go",
    command_specs=(
        ProviderCommandSpec("go-format", "go_format_command"),
        ProviderCommandSpec("go-vet", "go_vet_command"),
        ProviderCommandSpec("go-test", "go_test_command"),
    ),
)

BUILTIN_PROVIDER_METADATA = (
    PYTHON_PROVIDER,
    TYPESCRIPT_PROVIDER,
    GO_PROVIDER,
)


def builtin_provider_metadata() -> tuple[ProviderMetadata, ...]:
    """Return metadata for built-in providers in display order."""
    return BUILTIN_PROVIDER_METADATA


def python_provider() -> PythonProvider:
    """Return the built-in Python provider."""
    return PythonProvider()


def experimental_check_providers() -> tuple[TypeScriptProvider, GoProvider]:
    """Return experimental providers appended after stable Python checks."""
    return (TypeScriptProvider(), GoProvider())
