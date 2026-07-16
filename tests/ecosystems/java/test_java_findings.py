"""Tests canonical Java finding identities."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agent_maintainer.ecosystems.java.findings import JavaFinding


def test_finding_normalizes_and_ignores_line_moves() -> None:
    """Formatting noise and moved lines do not change semantic identity."""
    first = JavaFinding(
        tool=" CheckStyle ",
        rule=" AvoidInlineConditionals ",
        path=r"./src\main\java\example\App.java",
        subject=" example.App.run() ",
        message="Avoid   inline\nconditionals",
        line=12,
    )
    moved = replace(first, line=91)

    assert first.tool == "checkstyle"
    assert first.path == "src/main/java/example/App.java"
    assert first.message == "Avoid inline conditionals"
    assert first.fingerprint == moved.fingerprint


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("rule", "DifferentRule"),
        ("path", "src/main/java/example/Other.java"),
        ("subject", "example.App.other()"),
    ),
)
def test_semantic_changes_change_fingerprint(field: str, value: str) -> None:
    """Rule, path, and semantic-subject changes are new identities."""
    finding = JavaFinding("pmd", "CyclomaticComplexity", "App.java", "App.run", "high")

    assert replace(finding, **{field: value}).fingerprint != finding.fingerprint


def test_numeric_measurement_is_not_identity() -> None:
    """Complexity values ratchet separately from the semantic signature."""
    finding = JavaFinding(
        "pmd",
        "CyclomaticComplexity",
        "App.java",
        "App.run",
        "complexity",
        metric=7,
    )

    assert replace(finding, metric=8).fingerprint == finding.fingerprint


@pytest.mark.parametrize("path", ("/tmp/App.java", "../App.java", "src/../../App.java"))
def test_finding_rejects_unconfined_paths(path: str) -> None:
    """Finding paths remain repository-relative and traversal-free."""
    with pytest.raises(ValueError, match="repository-relative"):
        JavaFinding("pmd", "Rule", path, "App", "message")
