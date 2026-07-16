"""Tests deterministic Gradle DSL fragments and curated Java rulesets."""

from dataclasses import dataclass

import pytest

from agent_maintainer.ecosystems.java.templates.api import (
    render_build_fragment,
    render_gradle_properties,
    ruleset_text,
)

MIN_XML_REQUIRED_OCCURRENCES = 3


@dataclass(frozen=True)
class _TemplateExpectation:
    dsl: str
    spotless_version: str
    spotbugs_version: str
    quote: str
    confidence: str
    spotbugs_xml: str


@pytest.mark.parametrize(
    "expected",
    (
        _TemplateExpectation(
            "groovy",
            "com.diffplug.spotless' version '8.8.0",
            "com.github.spotbugs' version '6.5.9",
            "'",
            "Confidence.valueOf('MEDIUM')",
            "xml.required = true",
        ),
        _TemplateExpectation(
            "kotlin",
            'com.diffplug.spotless") version "8.8.0',
            'com.github.spotbugs") version "6.5.9',
            '"',
            "Confidence.MEDIUM",
            'reports.create("xml")',
        ),
    ),
)
def test_build_fragments_pin_plugins_and_native_defaults(
    expected: _TemplateExpectation,
) -> None:
    fragment = render_build_fragment(expected.dsl)

    assert expected.spotless_version in fragment
    assert expected.spotbugs_version in fragment
    assert f"googleJavaFormat({expected.quote}1.35.0{expected.quote})" in fragment
    assert "Effort.MAX" in fragment
    assert expected.confidence in fragment
    assert "13.8.0" in fragment
    assert "7.26.0" in fragment
    assert "0.8.15" in fragment
    assert "agentMaintainer.jacoco.minimumLineCoverage" in fragment
    assert "agentMaintainer.jacoco.minimumBranchCoverage" in fragment
    assert "COVEREDRATIO" in fragment
    assert "jacocoTestReport" in fragment
    assert "SpotBugsTask" in fragment
    assert expected.spotbugs_xml in fragment
    assert fragment.count("xml.required") >= MIN_XML_REQUIRED_OCCURRENCES
    assert "dependsOn" in fragment
    assert "test" in fragment
    assert "@" not in fragment


def test_new_repository_coverage_properties_use_strict_defaults() -> None:
    assert render_gradle_properties() == (
        "agentMaintainer.jacoco.minimumLineCoverage=0.80\n"
        "agentMaintainer.jacoco.minimumBranchCoverage=0.70\n"
    )


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
