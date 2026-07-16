"""Tests pinned Java/Gradle setup defaults."""

from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.ecosystems.java.defaults import JAVA_DEFAULTS, JAVA_TOOL_VERSIONS

EXPECTED_COMPLEXITY = (10, 15, 200)
EXPECTED_FILE_LIMITS = (500, 375)
EXPECTED_COVERAGE = (80, 70)


def test_tool_versions_are_explicitly_pinned() -> None:
    assert JAVA_TOOL_VERSIONS.spotless_plugin == "8.8.0"
    assert JAVA_TOOL_VERSIONS.spotbugs_plugin == "6.5.9"
    assert JAVA_TOOL_VERSIONS.checkstyle == "13.8.0"
    assert JAVA_TOOL_VERSIONS.pmd == "7.26.0"
    assert JAVA_TOOL_VERSIONS.jacoco == "0.8.15"
    assert JAVA_TOOL_VERSIONS.google_java_format == "1.35.0"


def test_native_policy_defaults_match_the_approved_contract() -> None:
    assert JAVA_DEFAULTS.spotbugs_effort == "MAX"
    assert JAVA_DEFAULTS.spotbugs_confidence == "MEDIUM"
    assert (
        JAVA_DEFAULTS.cyclomatic_complexity,
        JAVA_DEFAULTS.cognitive_complexity,
        JAVA_DEFAULTS.npath_complexity,
    ) == EXPECTED_COMPLEXITY
    assert (
        JAVA_DEFAULTS.max_physical_lines,
        JAVA_DEFAULTS.max_nonblank_lines,
    ) == EXPECTED_FILE_LIMITS
    assert (
        JAVA_DEFAULTS.minimum_line_coverage,
        JAVA_DEFAULTS.minimum_branch_coverage,
    ) == EXPECTED_COVERAGE


def test_defaults_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        _set_attribute(JAVA_DEFAULTS, "max_physical_lines", 1)
    with pytest.raises(FrozenInstanceError):
        _set_attribute(JAVA_TOOL_VERSIONS, "spotless_plugin", "unbounded")


def _set_attribute(target: object, name: str, value: object) -> None:
    setattr(target, name, value)
