"""Tests Go suppression classification."""

from __future__ import annotations

from agent_maintainer.ecosystems.go import suppressions


def test_go_suppressions_classify_broad_nolint() -> None:
    """Bare nolint is broad advisory suppression."""
    findings = suppressions.classify_line("//nolint")

    assert findings[0].kind == "nolint"
    assert findings[0].broad is True


def test_go_suppressions_classify_named_nolint() -> None:
    """Named nolint is still visible but not broad."""
    findings = suppressions.classify_line("//nolint:gocyclo,errcheck")

    assert findings[0].kind == "nolint"
    assert findings[0].broad is False


def test_go_suppressions_ignore_normal_comments() -> None:
    """Normal comments do not become suppression findings."""
    assert suppressions.classify_line("// regular comment") == ()
