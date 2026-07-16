"""Tests for the nested Java/Gradle configuration contract."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.config import loader
from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.config.validation import ConfigValidationError

OVERSIZED_INTEGER_DIGITS = 5_000


def apply_java(raw: object) -> MaintainerConfig:
    """Apply one nested Java table through the public loader seam."""

    return loader.apply_pyproject(MaintainerConfig(), {"java": raw})


def test_java_config_defaults_are_frozen_and_disabled() -> None:
    config = MaintainerConfig().java

    assert config == JavaGradleConfig()
    assert config.enabled is False
    assert config.gradle_root == "."
    assert config.checks == ()
    assert config.gradle_args == ("--console=plain", "--continue")
    assert config.source_roots == ("src/main/java", "**/src/main/java")
    assert config.test_roots == ("src/test/java", "**/src/test/java")
    assert config.projects == (":",)
    assert config.spotless_profiles == ("precommit", "full", "ci")
    assert config.test_profiles == ("full", "ci")
    assert config.findings_baseline == ".agent-maintainer/java-findings-baseline.json"
    assert config.jacoco_ratchet_ref == "origin/main"
    assert config.reports == (
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

    with pytest.raises(FrozenInstanceError):
        config.enabled = True  # type: ignore[misc]


def test_complete_java_table_is_coerced_without_shell_parsing() -> None:
    config = apply_java(
        {
            "enabled": True,
            "gradle_root": "backend",
            "checks": ["spotless", "spotbugs", "checkstyle", "pmd", "test", "jacoco"],
            "gradle_args": ["--console=plain", "--max-workers=4", "--warning-mode=fail"],
            "source_roots": ["backend/src/main/java", "modules/*/src/main/java"],
            "test_roots": ["backend/src/test/java"],
            "projects": [":app"],
            "spotless_tasks": ["spotlessCheck"],
            "spotbugs_tasks": ["spotbugsMain", "spotbugsTest"],
            "checkstyle_tasks": ["checkstyleMain"],
            "pmd_tasks": [":quality:pmdMain"],
            "test_tasks": [":app:test"],
            "jacoco_report_tasks": [":app:jacocoTestReport"],
            "jacoco_verify_tasks": [":app:jacocoTestCoverageVerification"],
            "spotless_profiles": ["precommit", "ci"],
            "spotbugs_profiles": ["full"],
            "checkstyle_profiles": ["ci"],
            "pmd_profiles": ["full", "ci"],
            "test_profiles": ["full"],
            "jacoco_profiles": ["ci"],
            "spotless_ratchet_ref": "origin/main",
            "findings_baseline": ".agent-maintainer/custom-java.json",
            "spotbugs_baseline": "config/spotbugs/baseline.xml",
            "jacoco_line_property": "coverage.line",
            "jacoco_branch_property": "coverage.branch",
            "jacoco_ratchet_ref": "upstream/trunk",
            "reports": [
                {
                    "tool": "checkstyle",
                    "tasks": ["checkstyleMain"],
                    "globs": ["build/reports/checkstyle/main.xml"],
                    "required": False,
                    "coverage_scope": "",
                    "coverage_label": "",
                }
            ],
        }
    ).java

    assert config.enabled is True
    assert config.gradle_root == "backend"
    assert config.pmd_tasks == (":quality:pmdMain",)
    assert config.projects == (":app",)
    assert config.jacoco_ratchet_ref == "upstream/trunk"
    assert config.gradle_args == (
        "--console=plain",
        "--max-workers=4",
        "--warning-mode=fail",
    )
    assert config.reports == (
        JavaReportExpectation(
            tool="checkstyle",
            tasks=("checkstyleMain",),
            globs=("build/reports/checkstyle/main.xml",),
            required=False,
        ),
    )


def test_java_enabled_environment_override_only_changes_enablement() -> None:
    original = JavaGradleConfig(
        gradle_root="backend",
        checks=("test",),
        test_tasks=("test",),
    )

    config = loader.apply_env(
        MaintainerConfig(java=original),
        environment={"AGENT_MAINTAINER_JAVA_ENABLED": "true"},
    )

    assert config.java.enabled is True
    assert config.java.gradle_root == "backend"
    assert config.java.test_tasks == ("test",)


@pytest.mark.parametrize(
    ("raw", "path"),
    [
        ({"unknown": True}, "tool.agent_maintainer.java.unknown"),
        (
            {"reports": [{"tool": "pmd", "tasks": ["pmdMain"], "globs": [], "extra": 1}]},
            "tool.agent_maintainer.java.reports.0.extra",
        ),
    ],
)
def test_java_config_rejects_unknown_nested_keys(raw: object, path: str) -> None:
    with pytest.raises(ConfigValidationError, match=path):
        apply_java(raw)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([], "java: must be a table"),
        ({"enabled": "yes"}, "java.enabled: must be a boolean"),
        ({"checks": "test"}, "java.checks: must be a list of strings"),
        ({"reports": {}}, "java.reports: must be a list of tables"),
        (
            {"reports": [{"tool": "pmd", "tasks": "pmdMain", "globs": ["a.xml"]}]},
            "java.reports.0.tasks: must be a list of strings",
        ),
    ],
)
def test_java_config_rejects_invalid_nested_types(raw: object, message: str) -> None:
    with pytest.raises(ConfigValidationError, match=re.escape(message)):
        apply_java(raw)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"checks": ["unknown"]}, "java.checks"),
        ({"spotless_profiles": ["manual"]}, "java.spotless_profiles"),
        ({"spotbugs_profiles": ["precommit"]}, "java.spotbugs_profiles"),
        ({"test_profiles": ["precommit"]}, "java.test_profiles"),
        ({"spotless_tasks": ["bad task"]}, "java.spotless_tasks"),
        ({"test_tasks": ["--scan"]}, "java.test_tasks"),
        ({"test_tasks": ["test", "test"]}, "java.test_tasks"),
        (
            {"reports": [{"tool": "spotless", "tasks": ["spotlessCheck"], "globs": ["x"]}]},
            "java.reports.0.tool",
        ),
    ],
)
def test_java_config_rejects_invalid_checks_profiles_and_tasks(
    raw: object,
    message: str,
) -> None:
    with pytest.raises(ConfigValidationError, match=message):
        apply_java(raw)


@pytest.mark.parametrize(
    "argument",
    [
        "--project-dir",
        "--project-dir=outside",
        "-p",
        "--settings-file=elsewhere.gradle",
        "--init-script",
        "--gradle-user-home=/tmp/gradle",
        "-Dsecret=value",
        "-Pprofile=release",
        "--max-workers=0",
        "--max-workers=4097",
        "--warning-mode=verbose",
        "--no-daemon",
    ],
)
def test_java_config_rejects_gradle_arguments_outside_allowlist(argument: str) -> None:
    with pytest.raises(ConfigValidationError, match=r"java\.gradle_args"):
        apply_java({"gradle_args": [argument]})


def test_java_config_rejects_oversized_worker_integer_deterministically() -> None:
    argument = f"--max-workers={'9' * OVERSIZED_INTEGER_DIGITS}"

    with pytest.raises(ConfigValidationError, match=r"java\.gradle_args"):
        apply_java({"gradle_args": [argument]})


@pytest.mark.parametrize(
    "argument",
    [
        "--console=plain",
        "--continue",
        "--stacktrace",
        "--offline",
        "--warning-mode=all",
        "--warning-mode=none",
        "--max-workers=1",
        "--max-workers=4096",
    ],
)
def test_java_config_accepts_allowlisted_gradle_arguments(argument: str) -> None:
    assert apply_java({"gradle_args": [argument]}).java.gradle_args == (argument,)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"gradle_root": "/tmp/build"}, "java.gradle_root"),
        ({"gradle_root": "../build"}, "java.gradle_root"),
        ({"source_roots": ["../src/main/java"]}, "java.source_roots"),
        ({"findings_baseline": "/tmp/findings.json"}, "java.findings_baseline"),
        (
            {"reports": [{"tool": "pmd", "tasks": ["pmdMain"], "globs": ["../pmd.xml"]}]},
            "java.reports.0.globs",
        ),
    ],
)
def test_java_config_rejects_lexically_unsafe_paths(raw: object, message: str) -> None:
    with pytest.raises(ConfigValidationError, match=message):
        apply_java(raw)


def test_selected_tool_without_tasks_remains_typed_for_doctor() -> None:
    config = apply_java({"enabled": True, "checks": ["spotbugs"]})

    assert config.java.enabled is True
    assert config.java.checks == ("spotbugs",)
    assert config.java.spotbugs_tasks == ()
