"""Tests truthful single- and multi-project JaCoCo report topology."""

from __future__ import annotations

import subprocess  # nosec B404 - isolated local Git fixture
from functools import partial
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.java import observations, provider, report_evidence, runner
from agent_maintainer.ecosystems.java.observations import (
    GradleObservation,
    GradleTaskOutcome,
    GradleTaskState,
)
from agent_maintainer.models import FULL_PROFILE

JACOCO_REPORT_PATH = "build/reports/jacoco/test/jacocoTestReport.xml"

# docsync:evidence.start evidence.java.coverage_rollout_tests


def test_default_single_project_coverage_is_labeled_as_root_project() -> None:
    config = JavaGradleConfig(
        enabled=True,
        checks=("jacoco",),
        jacoco_report_tasks=("jacocoTestReport",),
    )

    plans = provider.plan_reports(config, ("jacocoTestReport",))

    assert [(plan.coverage_scope, plan.coverage_label) for plan in plans] == [("project", ":")]


def test_multi_project_aggregate_requires_one_explicit_real_report() -> None:
    aggregate = JavaReportExpectation(
        "jacoco",
        ("testCodeCoverageReport",),
        ("build/reports/jacoco/testCodeCoverageReport/testCodeCoverageReport.xml",),
        coverage_scope="aggregate",
        coverage_label="all-projects",
    )
    config = JavaGradleConfig(
        checks=("jacoco",),
        projects=(":api", ":web"),
        jacoco_report_tasks=("testCodeCoverageReport",),
        reports=(aggregate,),
    )

    plans = provider.plan_reports(config, ("testCodeCoverageReport",))

    assert len(plans) == 1
    assert plans[0].coverage_scope == "aggregate"
    assert plans[0].coverage_label == "all-projects"


def test_multi_project_reports_must_label_every_project_exactly_once() -> None:
    config = JavaGradleConfig(
        checks=("jacoco",),
        projects=(":api", ":web"),
        jacoco_report_tasks=(":api:jacocoTestReport",),
        reports=project_reports(":api"),
    )

    with pytest.raises(provider.JavaProviderConfigurationError, match=":web"):
        provider.plan_reports(config, (":api:jacocoTestReport",))


def test_multi_project_cannot_mix_aggregate_and_project_percentages() -> None:
    aggregate = JavaReportExpectation(
        "jacoco",
        ("testCodeCoverageReport",),
        ("build/aggregate.xml",),
        coverage_scope="aggregate",
        coverage_label="all-projects",
    )
    config = multiproject_config((*project_reports(":api", ":web"), aggregate))

    with pytest.raises(provider.JavaProviderConfigurationError, match="mix"):
        provider.plan_reports(
            config,
            (":api:jacocoTestReport", ":web:jacocoTestReport", "testCodeCoverageReport"),
        )


def test_project_reports_remain_separate_labeled_artifact_facts(tmp_path: Path) -> None:
    plans = provider.plan_reports(
        multiproject_config(project_reports(":api", ":web")),
        (":api:jacocoTestReport", ":web:jacocoTestReport"),
    )
    for index, plan in enumerate(plans, start=1):
        report_path = tmp_path / plan.globs[0]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(jacoco_xml(index), encoding="utf-8")
    snapshots = observations.snapshot_reports(
        tmp_path,
        tuple(plan.expectation() for plan in plans),
        tuple(plan.task for plan in plans),
    )
    outcomes = tuple(
        GradleTaskOutcome(plan.task, plan.task, GradleTaskState.UP_TO_DATE) for plan in plans
    )
    observation = GradleObservation(tuple(plan.task for plan in plans), outcomes, snapshots, 0)

    evidence = report_evidence.collect_report_evidence(
        tmp_path,
        tmp_path,
        plans,
        observation,
        ".agent-maintainer/java-findings-baseline.json",
    )

    assert evidence.to_payload()["coverage"] == (
        {
            "branch_percentage": "75.0000",
            "label": ":api",
            "line_percentage": "66.6667",
            "scope": "project",
        },
        {
            "branch_percentage": "80.0000",
            "label": ":web",
            "line_percentage": "75.0000",
            "scope": "project",
        },
    )


def test_test_report_and_verification_tasks_keep_deterministic_order() -> None:
    config = JavaGradleConfig(
        enabled=True,
        checks=("test", "jacoco"),
        projects=(":api", ":web"),
        test_tasks=(":api:test", ":web:test"),
        jacoco_report_tasks=(":api:jacocoTestReport", ":web:jacocoTestReport"),
        jacoco_verify_tasks=(
            ":api:jacocoTestCoverageVerification",
            ":web:jacocoTestCoverageVerification",
        ),
        reports=project_reports(":api", ":web"),
    )

    assert provider.plan_group(config, "tests", FULL_PROFILE) == (
        ":api:test",
        ":web:test",
        ":api:jacocoTestReport",
        ":web:jacocoTestReport",
        ":api:jacocoTestCoverageVerification",
        ":web:jacocoTestCoverageVerification",
    )


def test_runner_blocks_downward_thresholds_and_publishes_labeled_headroom(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_properties(tmp_path, line="0.80", branch="0.70")
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "tests@example.com")
    git(tmp_path, "config", "user.name", "Tests")
    git(tmp_path, "add", "gradle.properties")
    git(tmp_path, "commit", "-qm", "base coverage")
    write_properties(tmp_path, line="0.79", branch="0.70")
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("jacoco",),
            jacoco_report_tasks=("jacocoTestReport",),
            jacoco_ratchet_ref="HEAD",
        )
    )
    resolved = runner.wrapper.ResolvedGradleWrapper(tmp_path, tmp_path, tmp_path / "gradlew")
    monkeypatch.setattr(runner, "_load_java_config", Mock(return_value=config))
    monkeypatch.setattr(runner.wrapper, "resolve_gradle_wrapper", Mock(return_value=resolved))
    monkeypatch.setattr(runner, "_run_wrapper", partial(run_jacoco_wrapper, tmp_path))

    outcome = runner.run_group(tmp_path, "tests", FULL_PROFILE)
    reports = cast(dict[str, object], outcome.payload["reports"])
    thresholds = cast(tuple[dict[str, object], ...], reports["coverage_thresholds"])

    assert outcome.exit_code == 1
    assert outcome.payload["evidence_status"] == "regression"
    assert thresholds[0]["label"] == ":"
    assert thresholds[0]["line_headroom"] == "11.0000"
    assert thresholds[0]["regressions"] == ("line",)


def multiproject_config(
    reports: tuple[JavaReportExpectation, ...],
) -> JavaGradleConfig:
    return JavaGradleConfig(
        checks=("jacoco",),
        projects=(":api", ":web"),
        jacoco_report_tasks=(":api:jacocoTestReport", ":web:jacocoTestReport"),
        reports=reports,
    )


def project_reports(*projects: str) -> tuple[JavaReportExpectation, ...]:
    return tuple(
        JavaReportExpectation(
            "jacoco",
            (f"{project}:jacocoTestReport",),
            (f"{project.removeprefix(':')}/build/reports/jacoco/test.xml",),
            coverage_scope="project",
            coverage_label=project,
        )
        for project in projects
    )


def jacoco_xml(index: int) -> str:
    return f"""<report name="project-{index}">
    <counter type="LINE" missed="1" covered="{index + 1}"/>
    <counter type="BRANCH" missed="1" covered="{index + 2}"/>
    </report>"""


def run_jacoco_wrapper(repo: Path, *_args: object) -> runner.subprocess.CompletedProcess[str]:
    report = repo / JACOCO_REPORT_PATH
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        """<report name="root">
        <counter type="LINE" missed="10" covered="90"/>
        <counter type="BRANCH" missed="20" covered="80"/>
        </report>""",
        encoding="utf-8",
    )
    return runner.subprocess.CompletedProcess(
        args=(),
        returncode=0,
        stdout="> Task :jacocoTestReport\n",
    )


def write_properties(repo: Path, *, line: str, branch: str) -> None:
    (repo / "gradle.properties").write_text(
        "\n".join(
            (
                f"agentMaintainer.jacoco.minimumLineCoverage={line}",
                f"agentMaintainer.jacoco.minimumBranchCoverage={branch}",
                "",
            )
        ),
        encoding="utf-8",
    )


def git(repo: Path, *args: str) -> None:
    subprocess.run(("git", "-C", str(repo), *args), check=True, capture_output=True)  # nosec B603


# docsync:evidence.end evidence.java.coverage_rollout_tests
