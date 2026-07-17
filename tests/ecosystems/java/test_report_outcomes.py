"""Tests task-scoped Java report outcome and freshness policy."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation
from agent_maintainer.ecosystems.java import observations, provider, report_outcomes
from agent_maintainer.ecosystems.java.observations import (
    GradleObservation,
    GradleTaskOutcome,
    GradleTaskState,
)

REPORT_GLOB = "build/reports/checkstyle/main.xml"
TASK = "checkstyleMain"
TEXT_ENCODING = "utf-8"


def test_provider_maps_parallel_tasks_and_globs_to_single_task_plans() -> None:
    """Multi-source defaults become unambiguous task-scoped report plans."""
    expectation = JavaReportExpectation(
        "checkstyle",
        ("checkstyleMain", "checkstyleTest"),
        ("build/main.xml", "build/test.xml"),
    )
    config = JavaGradleConfig(reports=(expectation,))

    plans = provider.plan_reports(config, ("checkstyleMain", "checkstyleTest"))

    assert [(plan.task, plan.globs) for plan in plans] == [
        ("checkstyleMain", ("build/main.xml",)),
        ("checkstyleTest", ("build/test.xml",)),
    ]


def test_provider_rejects_ambiguous_multi_task_report_mapping() -> None:
    """Multiple tasks need either positional globs or separate declarations."""
    expectation = JavaReportExpectation(
        "checkstyle",
        ("checkstyleMain", "checkstyleTest"),
        ("build/a.xml", "build/b.xml", "build/c.xml"),
    )

    with pytest.raises(provider.JavaProviderConfigurationError, match="unambiguous"):
        provider.plan_reports(JavaGradleConfig(reports=(expectation,)), (TASK,))


def test_unknown_gradle_outcome_fails_before_report_policy() -> None:
    """The plain-console parser rejects unrecognized Gradle task states."""
    with pytest.raises(observations.JavaConfigurationError, match="unsupported"):
        observations.build_gradle_observation(
            (TASK,),
            f"> Task :{TASK} UNKNOWN\n",
            0,
            (),
        )


def test_executed_task_requires_fresh_report(tmp_path: Path) -> None:
    """Executed evidence must be created or rewritten after the pre-run snapshot."""
    report = write_report(tmp_path)
    plan = report_plan()
    pre_run = snapshot(tmp_path, plan)

    with pytest.raises(report_outcomes.JavaReportEvidenceError, match="stale"):
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (plan,),
            observation(GradleTaskState.SUCCESS, pre_run),
        )

    fresh_time = pre_run[0].mtime_ns + 1
    os.utime(report, ns=(fresh_time, fresh_time))
    validated = report_outcomes.validate_report_outcomes(
        tmp_path,
        (plan,),
        observation(GradleTaskState.SUCCESS, pre_run),
    )

    assert len(validated) == 1


@pytest.mark.parametrize(
    "state",
    (GradleTaskState.FROM_CACHE, GradleTaskState.UP_TO_DATE),
)
def test_cached_or_up_to_date_task_accepts_existing_report(
    tmp_path: Path,
    state: GradleTaskState,
) -> None:
    """Non-executed successful tasks may reuse complete existing evidence."""
    write_report(tmp_path)
    plan = report_plan()
    pre_run = snapshot(tmp_path, plan)

    validated = report_outcomes.validate_report_outcomes(
        tmp_path,
        (plan,),
        observation(state, pre_run),
    )

    assert validated == pre_run


def test_no_source_accepts_absence_but_required_tests_fail(tmp_path: Path) -> None:
    """No-source is valid for analysis but cannot satisfy required test evidence."""
    analysis_plan = report_plan()
    assert (
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (analysis_plan,),
            observation(GradleTaskState.NO_SOURCE),
        )
        == ()
    )
    test_plan = provider.JavaReportPlan(
        "test",
        "test",
        ("build/test-results/test/*.xml",),
        True,
    )

    with pytest.raises(report_outcomes.JavaReportEvidenceError, match="required test"):
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (test_plan,),
            observation(GradleTaskState.NO_SOURCE, task="test"),
        )


@pytest.mark.parametrize(
    "state",
    (GradleTaskState.SKIPPED, GradleTaskState.FAILED),
)
def test_non_successful_task_states_fail_closed(
    tmp_path: Path,
    state: GradleTaskState,
) -> None:
    """Skipped and failed task outcomes cannot authorize report evidence."""
    with pytest.raises(report_outcomes.JavaReportEvidenceError, match="not successful"):
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (report_plan(),),
            observation(state),
        )


def test_required_glob_and_no_source_stale_file_fail(tmp_path: Path) -> None:
    """Required matches must exist, while no-source must not reuse old output."""
    plan = report_plan()
    with pytest.raises(report_outcomes.JavaReportEvidenceError, match="required report"):
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (plan,),
            observation(GradleTaskState.SUCCESS),
        )
    write_report(tmp_path)
    with pytest.raises(report_outcomes.JavaReportEvidenceError, match="no-source"):
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (plan,),
            observation(GradleTaskState.NO_SOURCE),
        )


def test_every_current_glob_match_is_confined_before_parsing(tmp_path: Path) -> None:
    """A report symlink escaping Gradle root is rejected by outcome validation."""
    outside = tmp_path.parent / "outside-checkstyle.xml"
    outside.write_text("<checkstyle/>", encoding=TEXT_ENCODING)
    report = tmp_path / REPORT_GLOB
    report.parent.mkdir(parents=True)
    report.symlink_to(outside)

    with pytest.raises(report_outcomes.JavaReportEvidenceError, match="escapes Gradle root"):
        report_outcomes.validate_report_outcomes(
            tmp_path,
            (report_plan(),),
            observation(GradleTaskState.SUCCESS),
        )


def report_plan() -> provider.JavaReportPlan:
    """Return one required Checkstyle evidence plan."""
    return provider.JavaReportPlan("checkstyle", TASK, (REPORT_GLOB,), True)


def observation(
    state: GradleTaskState,
    pre_run: tuple[observations.ReportSnapshot, ...] = (),
    *,
    task: str = TASK,
) -> GradleObservation:
    """Return one task-scoped observation."""
    outcome = GradleTaskOutcome(task, f":{task}", state)
    return GradleObservation((task,), (outcome,), pre_run, 0)


def snapshot(
    root: Path,
    plan: provider.JavaReportPlan,
) -> tuple[observations.ReportSnapshot, ...]:
    """Snapshot one plan's current reports."""
    return observations.snapshot_reports(root, (plan.expectation(),), (plan.task,))


def write_report(root: Path) -> Path:
    """Write one complete report placeholder."""
    report = root / REPORT_GLOB
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("<checkstyle/>", encoding=TEXT_ENCODING)
    return report
