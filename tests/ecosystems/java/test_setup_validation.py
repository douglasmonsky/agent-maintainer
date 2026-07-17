"""Tests reviewed post-edit Java setup validation orchestration."""

from __future__ import annotations

from pathlib import Path

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor.support.java_provider import check_java_provider
from agent_maintainer.ecosystems.java.provider import JavaProvider
from agent_maintainer.ecosystems.java.setup_validation import (
    JavaValidationAction,
    plan_java_setup_validation,
)
from agent_maintainer.ecosystems.models import EcosystemCheckContext

SPOTBUGS_TASK = "spotbugsMain"
EXECUTABLE_MODE = 0o755


def test_baseline_validation_sequence_is_exact() -> None:
    """Opt-in native baseline setup has one ordered approval/success chain."""
    plan = plan_java_setup_validation(
        "./gradlew",
        report_tasks=(SPOTBUGS_TASK,),
        create_spotbugs_baseline=True,
    )

    assert tuple(step.action for step in plan.steps) == (
        JavaValidationAction.WRAPPER_VERSION,
        JavaValidationAction.DISCOVER_TASKS,
        JavaValidationAction.OBSERVE_REPORTS,
        JavaValidationAction.CREATE_SPOTBUGS_BASELINE,
        JavaValidationAction.DOCTOR,
        JavaValidationAction.FULL_VERIFICATION,
    )
    assert plan.steps[1].command == ("./gradlew", "tasks", "--all")
    assert plan.steps[1].requires_approval is True
    assert plan.steps[3].requires_success_of == JavaValidationAction.OBSERVE_REPORTS


def test_zero_debt_sequence_omits_baseline_steps() -> None:
    """New repositories do not observe reports or create baselines implicitly."""
    plan = plan_java_setup_validation("./gradlew")
    actions = tuple(step.action for step in plan.steps)

    assert JavaValidationAction.OBSERVE_REPORTS not in actions
    assert JavaValidationAction.CREATE_SPOTBUGS_BASELINE not in actions
    assert actions[-2:] == (
        JavaValidationAction.DOCTOR,
        JavaValidationAction.FULL_VERIFICATION,
    )


def test_verification_never_discovers_tasks() -> None:
    """Provider checks delegate configured groups without tasks --all."""
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotbugs",),
            spotbugs_tasks=(SPOTBUGS_TASK,),
        )
    )
    context = EcosystemCheckContext(config, "origin/main", ("src",))
    commands = tuple(item for check in JavaProvider().checks(context) for item in check.command)

    assert "tasks" not in commands
    assert "--all" not in commands


def test_normal_doctor_never_executes_wrapper(tmp_path: Path) -> None:
    """Static doctor inspection cannot perform setup-only task discovery."""
    marker = tmp_path / "wrapper-ran"
    wrapper = tmp_path / "gradlew"
    wrapper.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
    wrapper.chmod(EXECUTABLE_MODE)
    config = MaintainerConfig(java=JavaGradleConfig(enabled=True))

    results = check_java_provider(tmp_path, config)

    assert results
    assert not marker.exists()
