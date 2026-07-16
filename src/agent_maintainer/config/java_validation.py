"""Resolved-policy validation for Java/Gradle configuration."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from agent_maintainer.config.issues import ConfigIssue
from agent_maintainer.config.java import JAVA_TOOLS, REPORT_TOOLS, JavaGradleConfig

JAVA_TASK_PATTERN = re.compile(r"^:?[A-Za-z0-9][A-Za-z0-9_.-]*(?::[A-Za-z0-9][A-Za-z0-9_.-]*)*$")
MAX_GRADLE_WORKERS = 4096
MAX_GRADLE_WORKER_DIGITS = 4
JAVA_PROFILE_RULES = (
    ("spotless_profiles", frozenset(("precommit", "full", "ci"))),
    ("spotbugs_profiles", frozenset(("full", "ci"))),
    ("checkstyle_profiles", frozenset(("full", "ci"))),
    ("pmd_profiles", frozenset(("full", "ci"))),
    ("test_profiles", frozenset(("full", "ci"))),
    ("jacoco_profiles", frozenset(("full", "ci"))),
)


def _unsafe_java_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or bool(re.match(r"^[A-Za-z]:", normalized))
    )


def _java_path_issues(
    values: tuple[str, ...],
    key: str,
    source: str,
) -> tuple[ConfigIssue, ...]:
    return tuple(
        ConfigIssue(source, key, f"path must be relative and confined: {value}")
        for value in values
        if _unsafe_java_path(value)
    )


def _java_arg_issues(args: tuple[str, ...], *, source: str) -> tuple[ConfigIssue, ...]:
    fixed = frozenset(("--console=plain", "--continue", "--stacktrace", "--offline"))
    issues: list[ConfigIssue] = []
    for argument in args:
        valid = argument in fixed or re.fullmatch(
            r"--warning-mode=(?:all|fail|summary|none)", argument
        )
        workers = re.fullmatch(r"--max-workers=([0-9]+)", argument)
        if workers is not None:
            digits = workers.group(1)
            valid = (
                len(digits) <= MAX_GRADLE_WORKER_DIGITS and 1 <= int(digits) <= MAX_GRADLE_WORKERS
            )
        if not valid:
            issues.append(
                ConfigIssue(source, "java.gradle_args", f"unsupported argument: {argument}")
            )
    return tuple(issues)


def _java_task_issues(
    tasks: tuple[str, ...],
    key: str,
    source: str,
) -> tuple[ConfigIssue, ...]:
    issues = [
        ConfigIssue(source, key, f"invalid Gradle task: {task}")
        for task in tasks
        if JAVA_TASK_PATTERN.fullmatch(task) is None
    ]
    if len(tasks) != len(set(tasks)):
        issues.append(ConfigIssue(source, key, "task names must be unique"))
    return tuple(issues)


def _java_choice_issues(
    values: tuple[str, ...],
    allowed: frozenset[str],
    key: str,
    source: str,
) -> tuple[ConfigIssue, ...]:
    return tuple(
        ConfigIssue(source, key, f"unsupported value: {value}")
        for value in values
        if value not in allowed
    )


def java_issues(
    java: JavaGradleConfig,
    *,
    source: str,
) -> tuple[ConfigIssue, ...]:
    """Return all fail-closed Java/Gradle configuration issues."""
    issues: list[ConfigIssue] = []
    issues.extend(_java_choice_issues(java.checks, JAVA_TOOLS, "java.checks", source))
    issues.extend(_java_profile_issues(java, source))
    issues.extend(_java_configured_task_issues(java, source))
    issues.extend(_java_arg_issues(java.gradle_args, source=source))
    issues.extend(_java_configured_path_issues(java, source))
    issues.extend(_java_report_issues(java, source))
    return tuple(issues)


def _java_profile_issues(java: JavaGradleConfig, source: str) -> tuple[ConfigIssue, ...]:
    configured = (
        ("spotless_profiles", java.spotless_profiles),
        ("spotbugs_profiles", java.spotbugs_profiles),
        ("checkstyle_profiles", java.checkstyle_profiles),
        ("pmd_profiles", java.pmd_profiles),
        ("test_profiles", java.test_profiles),
        ("jacoco_profiles", java.jacoco_profiles),
    )
    allowed_by_name = dict(JAVA_PROFILE_RULES)
    return tuple(
        issue
        for name, values in configured
        for issue in _java_choice_issues(values, allowed_by_name[name], f"java.{name}", source)
    )


def _java_configured_task_issues(
    java: JavaGradleConfig,
    source: str,
) -> tuple[ConfigIssue, ...]:
    configured = (
        ("spotless_tasks", java.spotless_tasks),
        ("spotbugs_tasks", java.spotbugs_tasks),
        ("checkstyle_tasks", java.checkstyle_tasks),
        ("pmd_tasks", java.pmd_tasks),
        ("test_tasks", java.test_tasks),
        ("jacoco_report_tasks", java.jacoco_report_tasks),
        ("jacoco_verify_tasks", java.jacoco_verify_tasks),
    )
    return tuple(
        issue
        for name, tasks in configured
        for issue in _java_task_issues(tasks, f"java.{name}", source)
    )


def _java_configured_path_issues(
    java: JavaGradleConfig,
    source: str,
) -> tuple[ConfigIssue, ...]:
    configured = (
        ("gradle_root", (java.gradle_root,)),
        ("source_roots", java.source_roots),
        ("test_roots", java.test_roots),
        ("findings_baseline", (java.findings_baseline,)),
        ("spotbugs_baseline", (java.spotbugs_baseline,) if java.spotbugs_baseline else ()),
    )
    return tuple(
        issue
        for name, values in configured
        for issue in _java_path_issues(values, f"java.{name}", source)
    )


def _java_report_issues(java: JavaGradleConfig, source: str) -> tuple[ConfigIssue, ...]:
    issues: list[ConfigIssue] = []
    for index, report in enumerate(java.reports):
        prefix = f"java.reports.{index}"
        issues.extend(_java_choice_issues((report.tool,), REPORT_TOOLS, f"{prefix}.tool", source))
        issues.extend(_java_task_issues(report.tasks, f"{prefix}.tasks", source))
        if not report.tasks:
            issues.append(ConfigIssue(source, f"{prefix}.tasks", "must not be empty"))
        if not report.globs:
            issues.append(ConfigIssue(source, f"{prefix}.globs", "must not be empty"))
        issues.extend(_java_path_issues(report.globs, f"{prefix}.globs", source))
    return tuple(issues)
