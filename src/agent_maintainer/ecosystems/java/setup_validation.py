"""Reviewed setup-only Java validation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class JavaValidationAction(StrEnum):
    """Ordered actions permitted after reviewed Java setup edits."""

    WRAPPER_VERSION = "wrapper-version"
    DISCOVER_TASKS = "discover-tasks"
    OBSERVE_REPORTS = "observe-reports"
    CREATE_SPOTBUGS_BASELINE = "create-spotbugs-baseline"
    DOCTOR = "doctor"
    FULL_VERIFICATION = "full-verification"


@dataclass(frozen=True)
class JavaValidationStep:
    """One command or evidence action with explicit gates."""

    action: JavaValidationAction
    command: tuple[str, ...]
    requires_approval: bool = False
    requires_success_of: JavaValidationAction | None = None


@dataclass(frozen=True)
class JavaSetupValidationPlan:
    """The exact reviewed post-edit Java validation sequence."""

    steps: tuple[JavaValidationStep, ...]


def plan_java_setup_validation(
    wrapper_command: str,
    *,
    report_tasks: tuple[str, ...] = (),
    create_spotbugs_baseline: bool = False,
) -> JavaSetupValidationPlan:
    """Build the setup-only sequence without executing any command."""
    if not wrapper_command:
        raise ValueError("wrapper command is required")
    if create_spotbugs_baseline and not report_tasks:
        raise ValueError("SpotBugs baseline setup requires explicit report tasks")
    if report_tasks and not create_spotbugs_baseline:
        raise ValueError("report observation is only planned for explicit baseline setup")
    steps = [
        JavaValidationStep(
            JavaValidationAction.WRAPPER_VERSION,
            (wrapper_command, "--version"),
        ),
        JavaValidationStep(
            JavaValidationAction.DISCOVER_TASKS,
            (wrapper_command, "tasks", "--all"),
            requires_approval=True,
            requires_success_of=JavaValidationAction.WRAPPER_VERSION,
        ),
    ]
    previous = JavaValidationAction.DISCOVER_TASKS
    if create_spotbugs_baseline:
        steps.extend(
            (
                JavaValidationStep(
                    JavaValidationAction.OBSERVE_REPORTS,
                    (wrapper_command, *report_tasks),
                    requires_success_of=previous,
                ),
                JavaValidationStep(
                    JavaValidationAction.CREATE_SPOTBUGS_BASELINE,
                    (),
                    requires_success_of=JavaValidationAction.OBSERVE_REPORTS,
                ),
            )
        )
        previous = JavaValidationAction.CREATE_SPOTBUGS_BASELINE
    steps.extend(
        (
            JavaValidationStep(
                JavaValidationAction.DOCTOR,
                ("agent-maintainer", "doctor"),
                requires_success_of=previous,
            ),
            JavaValidationStep(
                JavaValidationAction.FULL_VERIFICATION,
                ("agent-maintainer", "verify", "--profile", "full"),
                requires_success_of=JavaValidationAction.DOCTOR,
            ),
        )
    )
    return JavaSetupValidationPlan(tuple(steps))
