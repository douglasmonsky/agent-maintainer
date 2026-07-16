"""Tests native SpotBugs baseline creation from successful evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.config.java import JavaReportExpectation
from agent_maintainer.core.setup_plans import SetupReviewError
from agent_maintainer.ecosystems.java.observations import (
    GradleObservation,
    GradleTaskOutcome,
    GradleTaskState,
    snapshot_reports,
)
from agent_maintainer.ecosystems.java.reports.spotbugs import (
    SpotBugsEvidenceError,
    create_spotbugs_baseline,
)
from agent_maintainer.ecosystems.java.setup import (
    JavaSetupStatus,
    apply_java_setup,
    plan_spotbugs_baseline,
    preview_java_setup,
)

REPORT_PATH = "build/reports/spotbugs/main.xml"
SPOTBUGS_TASK = "spotbugsMain"
TEXT_ENCODING = "utf-8"
EXPECTED_BASELINE_MATCHES = 2


def test_baseline_is_deterministic_and_reviewed(tmp_path: Path) -> None:
    """Fresh successful evidence creates one approved deterministic XML edit."""
    write_report(tmp_path, ("B_TYPE", "A_TYPE", "A_TYPE"))
    expectation = spotbugs_expectation()
    observation = successful_observation()

    baseline = create_spotbugs_baseline(tmp_path, expectation, observation)
    plan = plan_spotbugs_baseline(
        tmp_path,
        gradle_root=tmp_path,
        expectation=expectation,
        observation=observation,
        baseline_path="config/spotbugs/baseline.xml",
    )

    assert (
        baseline.count("<Match>"),
        baseline.index("A_TYPE") < baseline.index("B_TYPE"),
    ) == (EXPECTED_BASELINE_MATCHES, True)
    assert plan.status == JavaSetupStatus.READY
    assert "+<FindBugsFilter>" in preview_java_setup(plan)

    changed = apply_java_setup(plan, approved_digest=plan.review_digest)
    assert changed == (tmp_path / "config" / "spotbugs" / "baseline.xml",)
    assert changed[0].read_text(encoding=TEXT_ENCODING) == baseline


def test_baseline_refuses_failed_gradle(tmp_path: Path) -> None:
    """A failed Gradle run can never produce a native baseline."""
    write_report(tmp_path, ("A_TYPE",))
    observation = successful_observation(exit_code=1)

    with pytest.raises(SpotBugsEvidenceError, match="Gradle run failed"):
        create_spotbugs_baseline(tmp_path, spotbugs_expectation(), observation)


def test_baseline_refuses_stale_success_report(tmp_path: Path) -> None:
    """Unchanged pre-run evidence is stale after an executed-success task."""
    write_report(tmp_path, ("A_TYPE",))
    expectation = spotbugs_expectation()
    pre_run = snapshot_reports(tmp_path, (expectation,), (SPOTBUGS_TASK,))
    observation = successful_observation(pre_run=pre_run)

    with pytest.raises(SpotBugsEvidenceError, match="stale"):
        create_spotbugs_baseline(tmp_path, expectation, observation)


def test_baseline_requires_complete_report(tmp_path: Path) -> None:
    """Missing required report evidence is refused."""
    with pytest.raises(SpotBugsEvidenceError, match="required SpotBugs report"):
        create_spotbugs_baseline(tmp_path, spotbugs_expectation(), successful_observation())


def test_refused_baseline_plan_cannot_apply(tmp_path: Path) -> None:
    """Setup exposes evidence refusal through the normal reviewed-plan boundary."""
    plan = plan_spotbugs_baseline(
        tmp_path,
        gradle_root=tmp_path,
        expectation=spotbugs_expectation(),
        observation=successful_observation(exit_code=1),
        baseline_path="config/spotbugs/baseline.xml",
    )

    assert plan.status == JavaSetupStatus.REFUSED
    with pytest.raises(SetupReviewError, match="Gradle run failed"):
        apply_java_setup(plan, approved_digest=plan.review_digest)


def successful_observation(
    *,
    exit_code: int = 0,
    pre_run=(),
) -> GradleObservation:
    """Return successful task-scoped SpotBugs evidence."""
    outcome = GradleTaskOutcome(SPOTBUGS_TASK, f":{SPOTBUGS_TASK}", GradleTaskState.SUCCESS)
    return GradleObservation((SPOTBUGS_TASK,), (outcome,), pre_run, exit_code)


def spotbugs_expectation() -> JavaReportExpectation:
    """Return the single-report test expectation."""
    return JavaReportExpectation("spotbugs", (SPOTBUGS_TASK,), (REPORT_PATH,))


def write_report(root: Path, bug_types: tuple[str, ...]) -> Path:
    """Write one successful SpotBugs XML report."""
    findings = "".join(
        f"<BugInstance type='{bug_type}'><Class classname='example.App'/></BugInstance>"
        for bug_type in bug_types
    )
    payload = f"<BugCollection>{findings}<Errors errors='0' missingClasses='0'/></BugCollection>"
    report = root / REPORT_PATH
    report.parent.mkdir(parents=True)
    report.write_text(payload, encoding=TEXT_ENCODING)
    return report
