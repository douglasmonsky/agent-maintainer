"""Frozen public configuration models for the Java/Gradle provider."""

from __future__ import annotations

from dataclasses import dataclass

JAVA_TOOLS = frozenset(("spotless", "spotbugs", "checkstyle", "pmd", "test", "jacoco"))
REPORT_TOOLS = JAVA_TOOLS - {"spotless"}
STATIC_PROFILES = ("full", "ci")


@dataclass(frozen=True)
class JavaReportExpectation:
    """Expected task-scoped report evidence beneath the configured Gradle root."""

    tool: str
    tasks: tuple[str, ...]
    globs: tuple[str, ...]
    required: bool = True
    coverage_scope: str = ""
    coverage_label: str = ""


DEFAULT_REPORTS = (
    JavaReportExpectation(
        "spotbugs",
        ("spotbugsMain", "spotbugsTest"),
        ("build/reports/spotbugs/main.xml", "build/reports/spotbugs/test.xml"),
    ),
    JavaReportExpectation(
        "checkstyle",
        ("checkstyleMain", "checkstyleTest"),
        ("build/reports/checkstyle/main.xml", "build/reports/checkstyle/test.xml"),
    ),
    JavaReportExpectation(
        "pmd",
        ("pmdMain", "pmdTest"),
        ("build/reports/pmd/main.xml", "build/reports/pmd/test.xml"),
    ),
    JavaReportExpectation("test", ("test",), ("build/test-results/test/*.xml",)),
    JavaReportExpectation(
        "jacoco",
        ("jacocoTestReport",),
        ("build/reports/jacoco/test/jacocoTestReport.xml",),
        coverage_scope="project",
        coverage_label=":",
    ),
)


@dataclass(frozen=True)
class JavaGradleConfig:
    """Resolved Java/Gradle provider configuration."""

    enabled: bool = False
    gradle_root: str = "."
    checks: tuple[str, ...] = ()
    gradle_args: tuple[str, ...] = ("--console=plain", "--continue")
    source_roots: tuple[str, ...] = ("src/main/java", "**/src/main/java")
    test_roots: tuple[str, ...] = ("src/test/java", "**/src/test/java")
    projects: tuple[str, ...] = (":",)
    spotless_tasks: tuple[str, ...] = ()
    spotbugs_tasks: tuple[str, ...] = ()
    checkstyle_tasks: tuple[str, ...] = ()
    pmd_tasks: tuple[str, ...] = ()
    test_tasks: tuple[str, ...] = ()
    jacoco_report_tasks: tuple[str, ...] = ()
    jacoco_verify_tasks: tuple[str, ...] = ()
    spotless_profiles: tuple[str, ...] = ("precommit", "full", "ci")
    spotbugs_profiles: tuple[str, ...] = STATIC_PROFILES
    checkstyle_profiles: tuple[str, ...] = STATIC_PROFILES
    pmd_profiles: tuple[str, ...] = STATIC_PROFILES
    test_profiles: tuple[str, ...] = STATIC_PROFILES
    jacoco_profiles: tuple[str, ...] = STATIC_PROFILES
    spotless_ratchet_ref: str = ""
    findings_baseline: str = ".agent-maintainer/java-findings-baseline.json"
    spotbugs_baseline: str = ""
    jacoco_ratchet_ref: str = "origin/main"
    jacoco_line_property: str = "agentMaintainer.jacoco.minimumLineCoverage"
    jacoco_branch_property: str = "agentMaintainer.jacoco.minimumBranchCoverage"
    reports: tuple[JavaReportExpectation, ...] = DEFAULT_REPORTS
