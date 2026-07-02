"""Internal registry for built-in ecosystem providers."""

from __future__ import annotations

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

BUILTIN_PROVIDER_METADATA = (
    PYTHON_PROVIDER,
    TYPESCRIPT_PROVIDER,
)


def builtin_provider_metadata() -> tuple[ProviderMetadata, ...]:
    """Return metadata for built-in providers in display order."""
    return BUILTIN_PROVIDER_METADATA


def python_provider() -> PythonProvider:
    """Return the built-in Python provider."""
    return PythonProvider()


def experimental_check_providers() -> tuple[TypeScriptProvider]:
    """Return experimental providers appended after stable Python checks."""
    return (TypeScriptProvider(),)
