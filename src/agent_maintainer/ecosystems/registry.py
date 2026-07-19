"""Internal registry for built-in ecosystem providers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.cpp import classification as cpp_classification
from agent_maintainer.ecosystems.java import classification as java_classification
from agent_maintainer.ecosystems.java.provider import JavaProvider
from agent_maintainer.ecosystems.models import (
    FileClassification,
    ProviderCommandSpec,
    ProviderMaturity,
    ProviderMetadata,
    SuppressionFinding,
)
from agent_maintainer.ecosystems.python import classification as python_classification
from agent_maintainer.ecosystems.python.provider import PythonProvider
from agent_maintainer.ecosystems.typescript import (
    classification as typescript_classification,
)
from agent_maintainer.ecosystems.typescript import (
    suppressions as typescript_suppressions,
)
from agent_maintainer.ecosystems.typescript.provider import TypeScriptProvider

ClassificationProvider = Callable[
    [str | Path, MaintainerConfig, Path | None],
    FileClassification | None,
]
SuppressionProvider = Callable[[str], tuple[SuppressionFinding, ...]]
SuppressionProviderEntry = tuple[str, SuppressionProvider]

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
    capabilities=(
        "lint",
        "typecheck",
        "test",
        "classification",
        "repair-facts",
        "architecture",
        "dead-code",
        "dependency-hygiene",
    ),
    enabled_field="enable_typescript",
    command_specs=(
        ProviderCommandSpec("typescript-lint", "typescript_lint_command"),
        ProviderCommandSpec("typescript-typecheck", "typescript_typecheck_command"),
        ProviderCommandSpec("typescript-test", "typescript_test_command"),
        ProviderCommandSpec("typescript-knip", "typescript_knip_command"),
        ProviderCommandSpec(
            "typescript-dependency-cruiser",
            "typescript_dependency_cruiser_command",
        ),
    ),
)

JAVA_PROVIDER = ProviderMetadata(
    name="java",
    display_name="Java/Gradle",
    maturity=ProviderMaturity.EXPERIMENTAL,
    docs_path="docs/provider-status.md",
    capabilities=("format", "static-analysis", "test", "coverage", "classification"),
    enabled_field="java.enabled",
)

BUILTIN_PROVIDER_METADATA = (
    PYTHON_PROVIDER,
    TYPESCRIPT_PROVIDER,
    JAVA_PROVIDER,
)


def builtin_provider_metadata() -> tuple[ProviderMetadata, ...]:
    """Return metadata for built-in providers in display order."""
    return BUILTIN_PROVIDER_METADATA


def python_provider() -> PythonProvider:
    """Return the built-in Python provider."""
    return PythonProvider()


def experimental_check_providers() -> tuple[TypeScriptProvider | JavaProvider, ...]:
    """Return experimental providers appended after stable Python checks."""
    return (TypeScriptProvider(), JavaProvider())


def classification_candidates(
    path: str | Path,
    config: MaintainerConfig,
    *,
    repo_root: Path | None = None,
) -> tuple[FileClassification, ...]:
    """Return classifications from providers active for this repository."""
    return tuple(
        classification
        for provider in CLASSIFICATION_PROVIDERS
        if (classification := provider(path, config, repo_root)) is not None
    )


def advisory_suppression_findings(
    ecosystem: str,
    line: str,
) -> tuple[SuppressionFinding, ...]:
    """Return advisory suppression findings for ecosystem line."""
    provider = suppression_provider(ecosystem)
    return provider(line) if provider else ()


def suppression_provider(ecosystem: str) -> SuppressionProvider | None:
    """Return advisory suppression provider for ecosystem."""
    for provider_ecosystem, provider in ADVISORY_SUPPRESSION_PROVIDERS:
        if ecosystem == provider_ecosystem:
            return provider
    return None


def python_classification_candidate(
    path: str | Path,
    config: MaintainerConfig,
    repo_root: Path | None,
) -> FileClassification | None:
    """Return Python classification candidate."""
    return python_classification.classify_path(path, config, repo_root=repo_root)


def typescript_classification_candidate(
    path: str | Path,
    config: MaintainerConfig,
    _repo_root: Path | None,
) -> FileClassification | None:
    """Return TypeScript classification candidate when provider is enabled."""
    if not config.enable_typescript:
        return None
    return typescript_classification.classify_path(path)


def java_classification_candidate(
    path: str | Path,
    config: MaintainerConfig,
    _repo_root: Path | None,
) -> FileClassification | None:
    """Return Java classification only after explicit provider enablement."""

    if not config.java.enabled:
        return None
    normalized_path = path.as_posix() if isinstance(path, Path) else path
    return java_classification.classify_path(normalized_path, config.java)


def cpp_classification_candidate(
    path: str | Path,
    config: MaintainerConfig,
    _repo_root: Path | None,
) -> FileClassification | None:
    """Return C/C++ classification only after explicit provider enablement."""

    if not config.cpp.enabled:
        return None
    return cpp_classification.classify_path(path, config.cpp)


CLASSIFICATION_PROVIDERS: tuple[ClassificationProvider, ...] = (
    python_classification_candidate,
    typescript_classification_candidate,
    java_classification_candidate,
    cpp_classification_candidate,
)
ADVISORY_SUPPRESSION_PROVIDERS: tuple[SuppressionProviderEntry, ...] = (
    ("typescript", typescript_suppressions.classify_line),
)
