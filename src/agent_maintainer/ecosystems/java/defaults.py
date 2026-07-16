"""Pinned, immutable defaults for reviewed Java/Gradle setup plans."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JavaToolVersions:
    """Pinned tool versions rendered into deterministic Gradle templates."""

    spotless_plugin: str = "8.8.0"
    spotbugs_plugin: str = "6.5.9"
    checkstyle: str = "13.8.0"
    pmd: str = "7.26.0"
    jacoco: str = "0.8.15"
    google_java_format: str = "1.35.0"


@dataclass(frozen=True)
class JavaPolicyDefaults:
    """Native analysis and quality thresholds for newly configured repositories."""

    spotbugs_effort: str = "MAX"
    spotbugs_confidence: str = "MEDIUM"
    cyclomatic_complexity: int = 10
    cognitive_complexity: int = 15
    npath_complexity: int = 200
    max_physical_lines: int = 500
    max_nonblank_lines: int = 375
    minimum_line_coverage: int = 80
    minimum_branch_coverage: int = 70


JAVA_TOOL_VERSIONS = JavaToolVersions()
JAVA_DEFAULTS = JavaPolicyDefaults()
