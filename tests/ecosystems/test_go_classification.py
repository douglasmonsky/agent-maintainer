"""Tests experimental Go ecosystem file classification."""

from __future__ import annotations

from agent_maintainer.ecosystems.go.classification import classify_path
from agent_maintainer.ecosystems.models import FileClassification, FileRole


def test_go_classifier_source_and_tests() -> None:
    """Source and test roles follow common Go naming patterns."""
    source = _classification("cmd/server/main.go")
    test = _classification("internal/app/handler_test.go")

    assert source.role == FileRole.SOURCE
    assert source.ecosystem == "go"
    assert test.role == FileRole.TEST


def test_go_classifier_config_dependency_docs() -> None:
    """Repo-adjacent Go files get stable roles."""
    roles = {
        ".golangci.yml": FileRole.CONFIG,
        "go.mod": FileRole.DEPENDENCY,
        "go.work.sum": FileRole.DEPENDENCY,
        "docs/go-provider.md": FileRole.DOCS,
    }

    assert {path: _classification(path).role for path in roles} == roles


def test_go_classifier_generated_and_ignored() -> None:
    """Generated files and vendored paths do not count as source."""
    ignored = _classification("vendor/example.com/pkg/file.go")
    generated = _classification("internal/proto/user.pb.go")

    assert ignored.role == FileRole.IGNORED
    assert ignored.ignored is True
    assert generated.role == FileRole.GENERATED
    assert generated.generated is True


def test_go_classifier_ignores_unrelated_files() -> None:
    """Unrelated files are not claimed by the Go provider."""
    assert classify_path("src/package/module.py") is None


def _classification(path: str) -> FileClassification:
    classification = classify_path(path)
    assert classification is not None
    return classification
