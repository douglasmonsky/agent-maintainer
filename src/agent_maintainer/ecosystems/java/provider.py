"""Profile-aware grouped Java/Gradle check planning."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.models import CI_PROFILE, FULL_PROFILE, PRECOMMIT_PROFILE, Check

JavaGroup = Literal["format", "static", "tests"]

_GROUP_PROFILES: dict[JavaGroup, tuple[str, ...]] = {
    "format": (PRECOMMIT_PROFILE,),
    "static": (FULL_PROFILE, CI_PROFILE),
    "tests": (FULL_PROFILE, CI_PROFILE),
}


class JavaProviderConfigurationError(ValueError):
    """Raised when selected Java verification cannot be planned safely."""


@dataclass(frozen=True)
class _ToolPlan:
    name: str
    tasks: tuple[str, ...]
    profiles: tuple[str, ...]
    task_field: str


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
            _group_check(group, profiles, context.config.diagnostic_artifacts_dir)
            for group in _GROUP_PROFILES
            if (profiles := _selected_group_profiles(config, group))
        ]


def plan_group(
    config: JavaGradleConfig,
    group: JavaGroup,
    profile: str,
) -> tuple[str, ...]:
    """Return ordered, de-duplicated tasks for one group and verifier profile."""
    if not config.enabled or profile not in _GROUP_PROFILES[group]:
        return ()
    tasks: dict[str, None] = {}
    for tool in _tool_plans(config, group):
        if tool.name not in config.checks or profile not in tool.profiles:
            continue
        if not tool.tasks:
            raise JavaProviderConfigurationError(
                f"selected Java tool '{tool.name}' has no tasks in java.{tool.task_field}"
            )
        tasks.update(dict.fromkeys(tool.tasks))
    return tuple(tasks)


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
    permitted = frozenset(_GROUP_PROFILES[group])
    return frozenset(
        profile
        for tool in _tool_plans(config, group)
        if tool.name in config.checks
        for profile in tool.profiles
        if profile in permitted
    )


def _tool_plans(config: JavaGradleConfig, group: JavaGroup) -> tuple[_ToolPlan, ...]:
    spotless = _ToolPlan(
        "spotless",
        config.spotless_tasks,
        config.spotless_profiles,
        "spotless_tasks",
    )
    if group == "format":
        return (spotless,)
    if group == "static":
        return (
            spotless,
            _ToolPlan(
                "spotbugs",
                config.spotbugs_tasks,
                config.spotbugs_profiles,
                "spotbugs_tasks",
            ),
            _ToolPlan(
                "checkstyle",
                config.checkstyle_tasks,
                config.checkstyle_profiles,
                "checkstyle_tasks",
            ),
            _ToolPlan("pmd", config.pmd_tasks, config.pmd_profiles, "pmd_tasks"),
        )
    return (
        _ToolPlan("test", config.test_tasks, config.test_profiles, "test_tasks"),
        _ToolPlan(
            "jacoco",
            (*config.jacoco_report_tasks, *config.jacoco_verify_tasks),
            config.jacoco_profiles,
            "jacoco_report_tasks/jacoco_verify_tasks",
        ),
    )
