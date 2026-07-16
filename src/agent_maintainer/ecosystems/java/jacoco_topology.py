"""Truthful JaCoCo coverage scope validation for Gradle project topologies."""

from __future__ import annotations

from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation

GRADLE_TASK_PREFIX = ":"


def requests_jacoco(config: JavaGradleConfig, requested: frozenset[str]) -> bool:
    """Return whether one normalized requested task belongs to JaCoCo."""
    jacoco_tasks = (*config.jacoco_report_tasks, *config.jacoco_verify_tasks)
    return any(task.removeprefix(GRADLE_TASK_PREFIX) in requested for task in jacoco_tasks)


def topology_problem(
    config: JavaGradleConfig,
    reports: tuple[JavaReportExpectation, ...],
) -> str | None:
    """Return a fail-closed topology problem without combining project coverage."""
    if "jacoco" not in config.checks:
        return None
    if not reports:
        return "selected JaCoCo tasks have no coverage reports"
    return _configured_topology_problem(config, reports)


def _configured_topology_problem(
    config: JavaGradleConfig,
    reports: tuple[JavaReportExpectation, ...],
) -> str | None:
    aggregate = _reports_with_scope(reports, "aggregate")
    projects = _reports_with_scope(reports, "project")
    if aggregate and projects:
        return "JaCoCo coverage cannot mix aggregate and project reports"
    if aggregate:
        return _aggregate_problem(aggregate)
    return _project_problem(config.projects, projects)


def _reports_with_scope(
    reports: tuple[JavaReportExpectation, ...],
    scope: str,
) -> tuple[JavaReportExpectation, ...]:
    return tuple(report for report in reports if report.coverage_scope == scope)


def _aggregate_problem(reports: tuple[JavaReportExpectation, ...]) -> str | None:
    if len(reports) != 1 or len(reports[0].globs) != 1:
        return "multi-project aggregate coverage requires exactly one real aggregate report"
    return None


def _project_problem(
    expected_projects: tuple[str, ...],
    reports: tuple[JavaReportExpectation, ...],
) -> str | None:
    labels = tuple(report.coverage_label for report in reports)
    if len(labels) != len(set(labels)):
        return "JaCoCo project coverage labels must be unique"
    missing = _first_absent(expected_projects, frozenset(labels))
    if missing:
        return f"JaCoCo coverage report is missing Gradle project: {missing}"
    extra = _first_absent(labels, frozenset(expected_projects))
    if extra:
        return f"JaCoCo coverage report labels an unknown Gradle project: {extra}"
    return None


def _first_absent(values: tuple[str, ...], available: frozenset[str]) -> str:
    return next((value for value in values if value not in available), "")
