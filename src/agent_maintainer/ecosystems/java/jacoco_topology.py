"""Truthful JaCoCo coverage scope validation for Gradle project topologies."""

from __future__ import annotations

from agent_maintainer.config.java import JavaGradleConfig, JavaReportExpectation


def topology_problem(
    config: JavaGradleConfig,
    reports: tuple[JavaReportExpectation, ...],
) -> str | None:
    """Return a fail-closed topology problem without combining project coverage."""
    if "jacoco" not in config.checks:
        return None
    if not reports:
        return "selected JaCoCo tasks have no coverage reports"
    aggregate = tuple(report for report in reports if report.coverage_scope == "aggregate")
    projects = tuple(report for report in reports if report.coverage_scope == "project")
    if aggregate and projects:
        return "JaCoCo coverage cannot mix aggregate and project reports"
    if aggregate:
        return _aggregate_problem(aggregate)
    return _project_problem(config.projects, projects)


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
    missing = tuple(project for project in expected_projects if project not in labels)
    if missing:
        return f"JaCoCo coverage report is missing Gradle project: {missing[0]}"
    extra = tuple(label for label in labels if label not in expected_projects)
    if extra:
        return f"JaCoCo coverage report labels an unknown Gradle project: {extra[0]}"
    return None
