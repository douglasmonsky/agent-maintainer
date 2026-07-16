"""Hermetic command-only runner for grouped Java/Gradle checks."""

from __future__ import annotations

import argparse
import os
import re

# Security: this module executes only a repository-confined checked wrapper.
import subprocess  # nosec B404
import sys
import tomllib
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.core import artifact_environment
from agent_maintainer.ecosystems.java import (
    artifacts,
    errors,
    observations,
    provider,
    report_evidence,
    wrapper,
)
from agent_maintainer.ecosystems.java.ratchets import validate_spotless_ratchet_ref


def main(argv: list[str] | None = None) -> int:
    """Run one configured Gradle group and return its policy exit status."""
    args = _parser().parse_args(argv)
    group: provider.JavaGroup = args.group
    workspace = Path.cwd().resolve(strict=True)
    profile = os.environ.get(artifact_environment.VERIFY_PROFILE_ENV, "")
    try:
        outcome = run_group(workspace, group, profile)
    except (errors.JavaConfigurationError, OSError) as exc:
        outcome = _configuration_error_outcome(workspace, group, profile, exc)
    return _write_outcome(outcome, workspace)


def run_group(workspace: Path, group: provider.JavaGroup, profile: str) -> artifacts.RunOutcome:
    """Run one explicit Java group and return its bounded artifact outcome."""
    if not profile:
        profile_field = artifact_environment.VERIFY_PROFILE_ENV
        raise provider.JavaProviderConfigurationError(
            f"{profile_field} is required for profile-aware Java task planning"
        )
    config = _load_java_config(workspace)
    tasks = provider.plan_group(config.java, group, profile)
    if not tasks:
        raise provider.JavaProviderConfigurationError(
            f"Java group '{group}' has no selected tasks for profile '{profile}'"
        )
    resolved_wrapper = wrapper.resolve_gradle_wrapper(workspace, config.java.gradle_root)
    _validate_spotless_execution(
        resolved_wrapper.gradle_root,
        tasks,
        config.java.spotless_tasks,
        config.java.spotless_ratchet_ref,
    )
    report_plans = provider.plan_reports(config.java, tasks)
    pre_run_reports = observations.snapshot_reports(
        resolved_wrapper.gradle_root,
        tuple(plan.expectation() for plan in report_plans),
        tasks,
    )
    completed = _run_wrapper(
        resolved_wrapper.executable,
        resolved_wrapper.gradle_root,
        config.java.gradle_args,
        tasks,
    )
    payload = artifacts.base_payload(group, profile)
    payload.update(
        artifacts.execution_payload(
            workspace=workspace,
            wrapper=resolved_wrapper,
            gradle_args=config.java.gradle_args,
            tasks=tasks,
            exit_code=completed.returncode,
        )
    )
    if completed.returncode != 0:
        return artifacts.RunOutcome(
            artifacts.artifact_path(
                workspace,
                group,
                fallback_dir=config.diagnostic_artifacts_dir,
            ),
            payload,
            completed.returncode,
        )
    observation = observations.build_gradle_observation(
        tasks,
        completed.stdout,
        completed.returncode,
        pre_run_reports,
    )
    evidence = report_evidence.collect_report_evidence(
        workspace,
        resolved_wrapper.gradle_root,
        report_plans,
        observation,
        config.java.findings_baseline,
    )
    payload["observation"] = observation.to_payload()
    if report_plans:
        reports_payload = evidence.to_payload()
        reports_payload["source_commit"] = _repository_head(workspace)
        payload["reports"] = reports_payload
        payload["reports_parsed"] = evidence.report_count > 0
        payload["evidence_status"] = "validated" if evidence.passed else "regression"
    spotbugs_payload = evidence.spotbugs_payload()
    if config.java.spotbugs_baseline and spotbugs_payload is not None:
        payload["spotbugs"] = spotbugs_payload
    policy_exit_code = 0 if evidence.passed else 1
    if policy_exit_code != 0:
        payload["status"] = "report-failed"
        payload["exit_code"] = policy_exit_code
    return artifacts.RunOutcome(
        artifacts.artifact_path(workspace, group, fallback_dir=config.diagnostic_artifacts_dir),
        payload,
        policy_exit_code,
    )


def _validate_spotless_execution(
    gradle_root: Path,
    tasks: tuple[str, ...],
    spotless_tasks: tuple[str, ...],
    ratchet_ref: str,
) -> None:
    selected = tuple(task for task in tasks if task in spotless_tasks)
    mutating = next((task for task in selected if _is_spotless_apply_task(task)), "")
    if mutating:
        raise provider.JavaProviderConfigurationError(
            f"mutating Spotless task is forbidden during verification: {mutating}"
        )
    if not selected or not ratchet_ref:
        return
    validation = validate_spotless_ratchet_ref(gradle_root, ratchet_ref)
    if validation.available:
        return
    message = " ".join(filter(None, (validation.reason, validation.ci_fetch_guidance)))
    raise provider.JavaProviderConfigurationError(message)


def _is_spotless_apply_task(task: str) -> bool:
    name = task.rsplit(":", maxsplit=1)[-1]
    return name.startswith("spotless") and name.endswith("Apply")


def _load_java_config(workspace: Path):
    try:
        return loader.load_config(workspace)
    except (TypeError, tomllib.TOMLDecodeError) as exc:
        raise errors.JavaConfigurationError(str(exc)) from exc


def _run_wrapper(
    executable: Path,
    gradle_root: Path,
    gradle_args: tuple[str, ...],
    tasks: tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    command = [os.fspath(executable), *gradle_args, *tasks]
    # Security: executable confinement and argv validation happen before this call.
    completed = subprocess.run(  # nosec B603
        command,
        cwd=gradle_root,
        shell=False,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    return completed


def _repository_head(workspace: Path) -> str:
    """Return the current immutable Git identity without failing verification."""
    completed = subprocess.run(  # nosec B603
        ("git", "-C", os.fspath(workspace), "rev-parse", "HEAD"),
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    head = completed.stdout.strip().lower()
    valid = completed.returncode == 0 and re.fullmatch(r"[0-9a-f]{7,64}", head)
    return head if valid else "unknown"


def _configuration_error_outcome(
    workspace: Path,
    group: provider.JavaGroup,
    profile: str,
    exc: Exception,
) -> artifacts.RunOutcome:
    payload = artifacts.base_payload(group, profile)
    payload.update(
        status="configuration-error",
        exit_code=artifacts.CONFIGURATION_EXIT_CODE,
        error=artifacts.sanitize_text(str(exc), workspace),
    )
    return artifacts.RunOutcome(
        artifacts.artifact_path(workspace, group),
        payload,
        artifacts.CONFIGURATION_EXIT_CODE,
    )


def _write_outcome(outcome: artifacts.RunOutcome, workspace: Path) -> int:
    try:
        artifacts.write_artifact(outcome.artifact_path, outcome.payload)
    except OSError as exc:
        message = artifacts.sanitize_text(f"could not write Java artifact: {exc}", workspace)
        print(message, file=sys.stderr)
        return artifacts.CONFIGURATION_EXIT_CODE
    return outcome.exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one Java/Gradle verification group")
    parser.add_argument("--group", required=True, choices=("format", "static", "tests"))
    return parser


if __name__ == "__main__":
    sys.exit(main())
