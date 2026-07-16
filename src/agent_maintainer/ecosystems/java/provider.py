"""Profile-aware grouped Java/Gradle check planning."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.ecosystems.java.errors import JavaConfigurationError
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import CI_PROFILE, FULL_PROFILE, PRECOMMIT_PROFILE, Check

JavaGroup = Literal["format", "static", "tests"]


@dataclass(frozen=True)
class _GroupSpec:
    name: JavaGroup
    values: tuple[str, ...]


_GROUP_PROFILES: tuple[_GroupSpec, ...] = (
    _GroupSpec("format", (PRECOMMIT_PROFILE,)),
    _GroupSpec("static", (FULL_PROFILE, CI_PROFILE)),
    _GroupSpec("tests", (FULL_PROFILE, CI_PROFILE)),
)
_GROUP_TOOLS: tuple[_GroupSpec, ...] = (
    _GroupSpec("format", ("spotless",)),
    _GroupSpec("static", ("spotless", "spotbugs", "checkstyle", "pmd")),
    _GroupSpec("tests", ("test", "jacoco")),
)


class JavaProviderConfigurationError(JavaConfigurationError, ValueError):
    """Raised when selected Java verification cannot be planned safely."""


@dataclass(frozen=True)
class _ToolPlan:
    name: str
    tasks: tuple[str, ...]
    profiles: tuple[str, ...]
    task_field: str


# docsync:evidence.start evidence.java.provider_foundation
class JavaProvider:
    """Build grouped Java/Gradle checks from explicit nested configuration."""

    name = "java"

    def checks_by_name(self, context: EcosystemCheckContext) -> dict[str, Check]:
        """Return enabled Java checks keyed by stable check name."""
        return {check.name: check for check in self.checks(context)}

    def checks(self, context: EcosystemCheckContext) -> list[Check]:
        """Return only groups containing a selected tool/profile assignment."""
        config = context.config.java
        if not config.enabled:
            return []
        return [
            _group_check(spec.name, profiles, context.config.diagnostic_artifacts_dir)
            for spec in _GROUP_PROFILES
            if (profiles := _selected_group_profiles(config, spec.name))
        ]


def plan_group(
    config: JavaGradleConfig,
    group: JavaGroup,
    profile: str,
) -> tuple[str, ...]:
    """Return ordered, de-duplicated tasks for one group and verifier profile."""
    if not config.enabled or profile not in _group_profiles(group):
        return ()
    tasks: dict[str, None] = {}
    for tool in _tool_plans(config, group):
        if tool.name not in config.checks or profile not in tool.profiles:
            continue
        if not tool.tasks:
            raise JavaProviderConfigurationError(
                f"selected Java tool '{tool.name}' has no tasks in {tool.task_field}"
            )
        tasks.update(dict.fromkeys(tool.tasks))
    return tuple(tasks)


def missing_selected_task_fields(config: JavaGradleConfig) -> tuple[str, ...]:
    """Return task fields that make selected Java tools unready."""
    return tuple(
        tool.task_field
        for tool in _all_tool_plans(config)
        if tool.name in config.checks and not tool.tasks
    )


# docsync:evidence.end evidence.java.provider_foundation


def _group_check(
    group: JavaGroup,
    profiles: frozenset[str],
    artifacts_dir: str,
) -> Check:
    check_name = f"java-gradle-{group}"
    artifact_path = Path(artifacts_dir) / "java-gradle" / f"{check_name}.json"
    return Check(
        check_name,
        [
            sys.executable,
            "-m",
            "agent_maintainer.ecosystems.java.runner",
            "--group",
            group,
        ],
        profiles,
        artifact_paths=(artifact_path.as_posix(),),
    )


def _selected_group_profiles(
    config: JavaGradleConfig,
    group: JavaGroup,
) -> frozenset[str]:
    permitted = frozenset(_group_profiles(group))
    return frozenset(
        profile
        for tool in _tool_plans(config, group)
        if tool.name in config.checks
        for profile in tool.profiles
        if profile in permitted
    )


def _tool_plans(config: JavaGradleConfig, group: JavaGroup) -> tuple[_ToolPlan, ...]:
    plans = _all_tool_plans(config)
    selected_tools = _group_tools(group)
    return tuple(plan for plan in plans if plan.name in selected_tools)


def _all_tool_plans(config: JavaGradleConfig) -> tuple[_ToolPlan, ...]:
    return (
        _spotless_plan(config),
        *_static_tool_plans(config),
        *_test_tool_plans(config),
    )


def _spotless_plan(config: JavaGradleConfig) -> _ToolPlan:
    return _ToolPlan(
        "spotless",
        config.spotless_tasks,
        config.spotless_profiles,
        "java.spotless_tasks",
    )


def _static_tool_plans(config: JavaGradleConfig) -> tuple[_ToolPlan, ...]:
    return (
        _ToolPlan(
            "spotbugs",
            config.spotbugs_tasks,
            config.spotbugs_profiles,
            "java.spotbugs_tasks",
        ),
        _ToolPlan(
            "checkstyle",
            config.checkstyle_tasks,
            config.checkstyle_profiles,
            "java.checkstyle_tasks",
        ),
        _ToolPlan("pmd", config.pmd_tasks, config.pmd_profiles, "java.pmd_tasks"),
    )


def _test_tool_plans(config: JavaGradleConfig) -> tuple[_ToolPlan, ...]:
    return (
        _ToolPlan("test", config.test_tasks, config.test_profiles, "java.test_tasks"),
        _ToolPlan(
            "jacoco",
            (*config.jacoco_report_tasks, *config.jacoco_verify_tasks),
            config.jacoco_profiles,
            "java.jacoco_report_tasks/java.jacoco_verify_tasks",
        ),
    )


def _group_profiles(group: JavaGroup) -> tuple[str, ...]:
    return next(spec.values for spec in _GROUP_PROFILES if spec.name == group)


def _group_tools(group: JavaGroup) -> tuple[str, ...]:
    return next(spec.values for spec in _GROUP_TOOLS if spec.name == group)
