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
from agent_maintainer.ecosystems.java.ratchets import validate_spotless_ratchet_ref
from agent_maintainer.ecosystems.java.reports.xml import (
    JavaXmlError,
    XmlLimits,
    local_name,
    parse_bounded_xml,
)
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


def _check_spotless_ratchet(
    repo_root: Path,
    java: JavaGradleConfig,
) -> tuple[DoctorResult, ...]:
    if not java.spotless_ratchet_ref:
        return ()
    validation = validate_spotless_ratchet_ref(repo_root, java.spotless_ratchet_ref)
    if validation.available:
        return (
            DoctorResult(
                "java-spotless-ratchet",
                OK,
                f"Spotless ratchet reference is available: {validation.ref}.",
                state=ACTIVE,
            ),
        )
    hint = validation.ci_fetch_guidance or "Configure a valid explicit Git reference."
    return (
        DoctorResult(
            "java-spotless-ratchet",
            WARNING,
            validation.reason,
            state=MISSING,
            hint=hint,
        ),
    )


def _check_spotbugs_baseline(
    repo_root: Path,
    java: JavaGradleConfig,
) -> tuple[DoctorResult, ...]:
    if not java.spotbugs_baseline:
        return ()
    return (_spotbugs_baseline_result(repo_root, java.spotbugs_baseline),)


def _spotbugs_baseline_result(repo_root: Path, configured_path: str) -> DoctorResult:
    try:
        baseline = _resolve_spotbugs_baseline(repo_root, configured_path)
    except OSError as exc:
        return _missing_spotbugs_baseline(configured_path, str(exc))
    except ValueError:
        return DoctorResult(
            "java-spotbugs-baseline",
            WARNING,
            "SpotBugs baseline resolves outside the repository.",
            state=UNSAFE_CONFIG,
            hint="Use a repository-confined regular FindBugsFilter XML file.",
        )
    try:
        root = parse_bounded_xml(baseline, limits=XmlLimits())
    except (JavaXmlError, OSError) as exc:
        return _missing_spotbugs_baseline(configured_path, str(exc))
    if local_name(root.tag) != "FindBugsFilter":
        return _missing_spotbugs_baseline(
            configured_path,
            "root element must be FindBugsFilter",
        )
    return DoctorResult(
        "java-spotbugs-baseline",
        OK,
        f"Native SpotBugs baseline is readable: {configured_path}.",
        state=ACTIVE,
    )


def _resolve_spotbugs_baseline(repo_root: Path, configured_path: str) -> Path:
    canonical_root = repo_root.resolve(strict=True)
    baseline = (canonical_root / configured_path).resolve(strict=True)
    baseline.relative_to(canonical_root)
    if not baseline.is_file():
        raise FileNotFoundError("not a regular file")
    return baseline


def _missing_spotbugs_baseline(path: str, reason: str) -> DoctorResult:
    return DoctorResult(
        "java-spotbugs-baseline",
        WARNING,
        f"SpotBugs baseline is not usable at {path}: {reason}.",
        state=MISSING,
        hint="Create the reviewed native baseline from successful fresh report evidence.",
    )


def _deferred_policy_fields(java: JavaGradleConfig) -> tuple[str, ...]:
    defaults = JavaGradleConfig()
    configured = (
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
        *_check_spotless_ratchet(repo_root, config.java),
        *_check_spotbugs_baseline(repo_root, config.java),
    )
