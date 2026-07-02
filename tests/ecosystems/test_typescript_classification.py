"""Tests experimental TypeScript ecosystem file classification."""

from __future__ import annotations

from agent_maintainer.ecosystems.models import FileRole
from agent_maintainer.ecosystems.typescript.classification import classify_path


def test_typescript_classifier_identifies_source_and_tests() -> None:
    """Source and test roles follow common TypeScript naming patterns."""
    source = classify_path("src/app/component.tsx")
    spec = classify_path("src/app/component.spec.ts")
    nested_test = classify_path("src/app/__tests__/component.test.tsx")

    assert source is not None
    assert source.role == FileRole.SOURCE
    assert source.ecosystem == "typescript"
    assert spec is not None
    assert spec.role == FileRole.TEST
    assert nested_test is not None
    assert nested_test.role == FileRole.TEST


def test_typescript_classifier_identifies_config_dependency_and_docs() -> None:
    """Repo-adjacent TypeScript files get stable roles."""
    config = classify_path("tsconfig.json")
    dependency = classify_path("pnpm-lock.yaml")
    docs = classify_path("docs/components.mdx")

    assert config is not None
    assert config.role == FileRole.CONFIG
    assert dependency is not None
    assert dependency.role == FileRole.DEPENDENCY
    assert docs is not None
    assert docs.role == FileRole.DOCS


def test_typescript_classifier_identifies_generated_and_ignored_files() -> None:
    """Build outputs and generated folders do not count as source."""
    ignored = classify_path("node_modules/pkg/index.js")
    generated = classify_path("src/__generated__/client.ts")

    assert ignored is not None
    assert ignored.role == FileRole.IGNORED
    assert ignored.ignored is True
    assert generated is not None
    assert generated.role == FileRole.GENERATED
    assert generated.generated is True


def test_typescript_classifier_ignores_unrelated_files() -> None:
    """Unrelated files are not claimed by the TypeScript provider."""
    assert classify_path("src/package/module.py") is None
