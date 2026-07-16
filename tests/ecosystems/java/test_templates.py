"""Tests deterministic Gradle DSL fragments and curated Java rulesets."""

import pytest

from agent_maintainer.ecosystems.java.templates.api import (
    render_build_fragment,
    ruleset_text,
)


@pytest.mark.parametrize(
    ("dsl", "spotless_version", "spotbugs_version", "quote"),
    (
        (
            "groovy",
            "com.diffplug.spotless' version '8.8.0",
            "com.github.spotbugs' version '6.5.9",
            "'",
        ),
        (
            "kotlin",
            'com.diffplug.spotless") version "8.8.0',
            'com.github.spotbugs") version "6.5.9',
            '"',
        ),
    ),
)
def test_build_fragments_pin_plugins_and_native_defaults(
    dsl: str,
    spotless_version: str,
    spotbugs_version: str,
    quote: str,
) -> None:
    fragment = render_build_fragment(dsl)

    assert spotless_version in fragment
    assert spotbugs_version in fragment
    assert f"googleJavaFormat({quote}1.35.0{quote})" in fragment
    assert "Effort.MAX" in fragment
    assert "Confidence.MEDIUM" in fragment
    assert "13.8.0" in fragment
    assert "7.26.0" in fragment
    assert "0.8.15" in fragment
    assert "@" not in fragment


def test_checkstyle_ruleset_leaves_formatting_to_spotless() -> None:
    ruleset = ruleset_text("checkstyle")

    assert "AvoidStarImport" in ruleset
    assert "VisibilityModifier" in ruleset
    assert "WhitespaceAround" not in ruleset
    assert "Indentation" not in ruleset
    assert "LineLength" not in ruleset


def test_pmd_ruleset_owns_design_performance_and_complexity() -> None:
    ruleset = ruleset_text("pmd")

    assert "category/java/errorprone.xml" in ruleset
    assert "category/java/bestpractices.xml" in ruleset
    assert "category/java/performance.xml" in ruleset
    assert "design.xml/CyclomaticComplexity" in ruleset
    assert "<value>10</value>" in ruleset
    assert "design.xml/CognitiveComplexity" in ruleset
    assert "<value>15</value>" in ruleset
    assert "design.xml/NPathComplexity" in ruleset
    assert "<value>200</value>" in ruleset
    assert "design.xml/ExcessiveClassLength" in ruleset
    assert "<value>500</value>" in ruleset


def test_unknown_template_choices_fail_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Gradle DSL"):
        render_build_fragment("scala")
    with pytest.raises(ValueError, match="unsupported Java ruleset"):
        ruleset_text("formatter")
