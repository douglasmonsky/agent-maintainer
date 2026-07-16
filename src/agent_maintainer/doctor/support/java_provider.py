"""Static doctor checks for the experimental Java/Gradle provider."""

from __future__ import annotations

import shutil
from pathlib import Path

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.doctor.support.models import (
    ACTIVE,
    MISSING,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)
from agent_maintainer.doctor.support.providers import path_with_local_bins
from agent_maintainer.ecosystems.java.provider import missing_selected_task_fields
from agent_maintainer.ecosystems.java.wrapper import GradleWrapperError, resolve_gradle_wrapper


def _check_java_wrapper(repo_root: Path, config: MaintainerConfig) -> DoctorResult:
    try:
        wrapper = resolve_gradle_wrapper(repo_root, config.java.gradle_root)
    except (GradleWrapperError, OSError) as exc:
        return DoctorResult(
            "java-gradle-wrapper",
            WARNING,
            f"Java Gradle wrapper is not ready: {exc}.",
            state=MISSING,
            hint="Commit a repository-confined executable Gradle wrapper at java.gradle_root.",
        )
    relative_wrapper = wrapper.executable.relative_to(wrapper.workspace).as_posix()
    return DoctorResult(
        "java-gradle-wrapper",
        OK,
        f"Checked-in Gradle wrapper is ready: {relative_wrapper}.",
        state=ACTIVE,
    )


def _check_java_runtime(repo_root: Path) -> DoctorResult:
    if shutil.which("java", path=path_with_local_bins(repo_root)) is None:
        return DoctorResult(
            "java-runtime",
            WARNING,
            "Java runtime is unavailable on PATH.",
            state=MISSING,
            hint="Install the repository's required JDK and expose java on PATH.",
        )
    return DoctorResult(
        "java-runtime",
        OK,
        "Java runtime is available on PATH.",
        state=ACTIVE,
    )


def _check_java_task_config(config: MaintainerConfig) -> DoctorResult:
    if not config.java.checks:
        return DoctorResult(
            "java-gradle-config",
            WARNING,
            "Java provider is enabled but no checks are selected.",
            state=UNSAFE_CONFIG,
            hint="Select explicit tools in [tool.agent_maintainer.java].checks.",
        )
    missing_fields = missing_selected_task_fields(config.java)
    if missing_fields:
        joined = ", ".join(missing_fields)
        return DoctorResult(
            "java-gradle-config",
            WARNING,
            f"Selected Java tools have no configured tasks: {joined}.",
            state=UNSAFE_CONFIG,
            hint=(
                "Configure exact checked-in Gradle task names; normal doctor does not "
                "discover tasks."
            ),
        )
    deferred_fields = _deferred_policy_fields(config.java)
    if deferred_fields:
        joined = ", ".join(deferred_fields)
        return DoctorResult(
            "java-gradle-config",
            WARNING,
            f"Java foundation does not yet enforce configured policy fields: {joined}.",
            state=UNSAFE_CONFIG,
            hint="Use defaults until the setup, baseline, and coverage phases are enabled.",
        )
    selected = ", ".join(config.java.checks)
    return DoctorResult(
        "java-gradle-config",
        OK,
        f"Configured Java Gradle tools: {selected}.",
        state=ACTIVE,
    )


def _deferred_policy_fields(java: JavaGradleConfig) -> tuple[str, ...]:
    defaults = JavaGradleConfig()
    configured = (
        ("java.spotless_ratchet_ref", bool(java.spotless_ratchet_ref)),
        ("java.spotbugs_baseline", bool(java.spotbugs_baseline)),
        ("java.jacoco_line_property", java.jacoco_line_property != defaults.jacoco_line_property),
        (
            "java.jacoco_branch_property",
            java.jacoco_branch_property != defaults.jacoco_branch_property,
        ),
    )
    return tuple(name for name, changed in configured if changed)


def check_java_provider(
    repo_root: Path,
    config: MaintainerConfig,
) -> tuple[DoctorResult, ...]:
    """Return static Java/Gradle foundation health without executing Gradle."""
    if not config.java.enabled:
        return ()
    return (
        _check_java_wrapper(repo_root, config),
        _check_java_runtime(repo_root),
        _check_java_task_config(config),
    )
