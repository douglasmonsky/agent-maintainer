"""Tests Java/Gradle provider check and task planning."""

from __future__ import annotations

import sys
from dataclasses import replace

import pytest

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.java.provider import (
    JavaProvider,
    JavaProviderConfigurationError,
    plan_group,
)
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import CI_PROFILE, FULL_PROFILE, PRECOMMIT_PROFILE


def test_java_provider_is_disabled_by_default() -> None:
    assert JavaProvider().checks(_context(MaintainerConfig())) == []


def test_java_provider_builds_three_stable_group_checks() -> None:
    config = replace(
        MaintainerConfig(),
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotless", "spotbugs", "test"),
            spotless_tasks=("spotlessCheck",),
            spotbugs_tasks=("spotbugsMain",),
            test_tasks=("test",),
        ),
    )

    checks = JavaProvider().checks_by_name(_context(config))

    assert tuple(checks) == (
        "java-gradle-format",
        "java-gradle-static",
        "java-gradle-tests",
    )
    assert checks["java-gradle-format"].profiles == {PRECOMMIT_PROFILE}
    assert checks["java-gradle-static"].profiles == {FULL_PROFILE, CI_PROFILE}
    assert checks["java-gradle-tests"].profiles == {FULL_PROFILE, CI_PROFILE}
    for group, check in checks.items():
        assert check.command == [
            sys.executable,
            "-m",
            "agent_maintainer.ecosystems.java.runner",
            "--group",
            group.removeprefix("java-gradle-"),
        ]
        assert check.artifact_paths == (f".verify-logs/java-gradle/{group}.json",)


def test_plan_group_orders_and_deduplicates_selected_tasks() -> None:
    config = JavaGradleConfig(
        enabled=True,
        checks=("spotless", "spotbugs", "checkstyle", "pmd", "test", "jacoco"),
        spotless_tasks=("spotlessCheck", ":shared"),
        spotbugs_tasks=(":shared", "spotbugsMain"),
        checkstyle_tasks=("checkstyleMain",),
        pmd_tasks=("pmdMain", "checkstyleMain"),
        test_tasks=("test",),
        jacoco_report_tasks=("jacocoTestReport", "test"),
        jacoco_verify_tasks=("jacocoTestCoverageVerification",),
    )

    assert plan_group(config, "format", PRECOMMIT_PROFILE) == (
        "spotlessCheck",
        ":shared",
    )
    assert plan_group(config, "static", FULL_PROFILE) == (
        "spotlessCheck",
        ":shared",
        "spotbugsMain",
        "checkstyleMain",
        "pmdMain",
    )
    assert plan_group(config, "tests", CI_PROFILE) == (
        "test",
        "jacocoTestReport",
        "jacocoTestCoverageVerification",
    )


def test_java_provider_uses_configured_artifact_directory() -> None:
    config = replace(
        MaintainerConfig(),
        diagnostic_artifacts_dir=".custom-logs",
        java=JavaGradleConfig(
            enabled=True,
            checks=("test",),
            test_tasks=("test",),
        ),
    )

    checks = JavaProvider().checks_by_name(_context(config))

    assert checks["java-gradle-tests"].artifact_paths == (
        ".custom-logs/java-gradle/java-gradle-tests.json",
    )


def test_plan_group_omits_tools_not_assigned_to_profile() -> None:
    config = JavaGradleConfig(
        enabled=True,
        checks=("spotless", "spotbugs", "checkstyle"),
        spotless_tasks=("spotlessCheck",),
        spotbugs_tasks=("spotbugsMain",),
        checkstyle_tasks=("checkstyleMain",),
        spotless_profiles=(PRECOMMIT_PROFILE,),
        spotbugs_profiles=(FULL_PROFILE,),
        checkstyle_profiles=(CI_PROFILE,),
    )

    assert plan_group(config, "static", FULL_PROFILE) == ("spotbugsMain",)
    assert plan_group(config, "static", CI_PROFILE) == ("checkstyleMain",)


def test_selected_tool_without_tasks_is_verification_configuration_failure() -> None:
    config = JavaGradleConfig(
        enabled=True,
        checks=("spotbugs",),
        spotbugs_profiles=(FULL_PROFILE,),
    )

    with pytest.raises(
        JavaProviderConfigurationError,
        match=r"selected Java tool 'spotbugs'.*java\.spotbugs_tasks",
    ):
        plan_group(config, "static", FULL_PROFILE)


def test_unselected_tool_with_no_tasks_is_silent() -> None:
    assert plan_group(JavaGradleConfig(enabled=True), "static", FULL_PROFILE) == ()

    config = replace(MaintainerConfig(), java=JavaGradleConfig(enabled=True))
    assert JavaProvider().checks(_context(config)) == []


def _context(config: MaintainerConfig) -> EcosystemCheckContext:
    return EcosystemCheckContext(
        config=config,
        compare_branch="origin/main",
        package_paths=("src",),
    )
