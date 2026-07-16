"""Task-state and freshness policy for Java report evidence."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.ecosystems.java import provider
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.java.observations import (
    GradleObservation,
    GradleTaskOutcome,
    GradleTaskState,
    ReportSnapshot,
    snapshot_reports,
)


class JavaReportEvidenceError(JavaConfigurationError):
    """Raised when report evidence cannot authorize a verification result."""


def validate_report_outcomes(
    gradle_root: Path,
    plans: tuple[provider.JavaReportPlan, ...],
    observation: GradleObservation,
) -> tuple[ReportSnapshot, ...]:
    """Return confined current reports after enforcing the task-state matrix."""
    if observation.exit_code != 0:
        raise JavaReportEvidenceError("Gradle failure precedes Java report validation")
    expectations = tuple(plan.expectation() for plan in plans)
    try:
        current = snapshot_reports(
            gradle_root,
            expectations,
            observation.requested_tasks,
        )
    except (JavaConfigurationError, OSError) as exc:
        raise JavaReportEvidenceError(str(exc)) from exc
    for plan in plans:
        outcome = _plan_outcome(plan, observation.task_outcomes)
        snapshots = _plan_snapshots(plan, current)
        _validate_plan_state(plan, outcome.state, snapshots, observation.pre_run_reports)
    return current


def _plan_outcome(
    plan: provider.JavaReportPlan,
    outcomes: tuple[GradleTaskOutcome, ...],
) -> GradleTaskOutcome:
    matching = tuple(outcome for outcome in outcomes if outcome.task == plan.task)
    if len(matching) != 1:
        raise JavaReportEvidenceError(f"missing or ambiguous report task outcome: {plan.task}")
    return matching[0]


def _plan_snapshots(
    plan: provider.JavaReportPlan,
    snapshots: tuple[ReportSnapshot, ...],
) -> tuple[ReportSnapshot, ...]:
    return tuple(
        item for item in snapshots if item.tool == plan.tool and item.tasks == (plan.task,)
    )


def _validate_plan_state(
    plan: provider.JavaReportPlan,
    state: GradleTaskState,
    current: tuple[ReportSnapshot, ...],
    previous: tuple[ReportSnapshot, ...],
) -> None:
    if state is GradleTaskState.NO_SOURCE:
        _validate_no_source(plan, current)
        return
    successful = {
        GradleTaskState.SUCCESS,
        GradleTaskState.FROM_CACHE,
        GradleTaskState.UP_TO_DATE,
    }
    if state not in successful:
        raise JavaReportEvidenceError(f"Java report task is not successful: {plan.task}")
    _validate_required_globs(plan, current)
    if state is GradleTaskState.SUCCESS:
        _validate_freshness(plan, current, previous)


def _validate_no_source(
    plan: provider.JavaReportPlan,
    current: tuple[ReportSnapshot, ...],
) -> None:
    if current:
        raise JavaReportEvidenceError(f"no-source task retained stale reports: {plan.task}")
    if plan.tool == "test" and plan.required:
        raise JavaReportEvidenceError(f"required test task has no source: {plan.task}")


def _validate_required_globs(
    plan: provider.JavaReportPlan,
    current: tuple[ReportSnapshot, ...],
) -> None:
    if not plan.required:
        return
    matched = {item.glob for item in current}
    missing = tuple(report_glob for report_glob in plan.globs if report_glob not in matched)
    if missing:
        raise JavaReportEvidenceError(f"required report evidence is missing: {missing[0]}")


def _validate_freshness(
    plan: provider.JavaReportPlan,
    current: tuple[ReportSnapshot, ...],
    previous: tuple[ReportSnapshot, ...],
) -> None:
    old = {_snapshot_key(item): item for item in _plan_snapshots(plan, previous)}
    if any(_unchanged(old.get(_snapshot_key(item)), item) for item in current):
        raise JavaReportEvidenceError(f"executed task retained stale reports: {plan.task}")


def _snapshot_key(item: ReportSnapshot) -> tuple[str, tuple[str, ...], str, str]:
    return item.tool, item.tasks, item.glob, item.path


def _unchanged(previous: ReportSnapshot | None, current: ReportSnapshot) -> bool:
    if previous is None:
        return False
    return (
        previous.sha256,
        previous.size,
        previous.mtime_ns,
    ) == (current.sha256, current.size, current.mtime_ns)
