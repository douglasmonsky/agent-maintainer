"""Hermetic command-only runner for grouped Java/Gradle checks."""

from __future__ import annotations

import argparse
import os

# Security: this module executes only a repository-confined checked wrapper.
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.core import artifact_environment
from agent_maintainer.ecosystems.java import (
    artifacts,
    errors,
    jacoco_thresholds,
    observations,
    provider,
    report_evidence,
    wrapper,
)
from agent_maintainer.ecosystems.java.ratchets import validate_spotless_ratchet_ref

MIN_GIT_HASH_LENGTH = 7
MAX_GIT_HASH_LENGTH = 64


@dataclass(frozen=True)
class _RunPlan:
    gradle_args: tuple[str, ...]
    findings_baseline: str
    spotbugs_baseline: str
    jacoco_ratchet_ref: str
    jacoco_line_property: str
    jacoco_branch_property: str
    diagnostic_artifacts_dir: str
    tasks: tuple[str, ...]
    wrapper: wrapper.ResolvedGradleWrapper
    reports: tuple[provider.JavaReportPlan, ...]
    pre_run_reports: tuple[observations.ReportSnapshot, ...]


@dataclass(frozen=True)
class _CoverageThresholds:
    payloads: tuple[dict[str, object], ...]
    passed: bool


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
    plan = _plan_run(workspace, group, profile)
    completed = _run_wrapper(
        plan.wrapper.executable,
        plan.wrapper.gradle_root,
        plan.gradle_args,
        plan.tasks,
    )
    payload = _execution_payload(workspace, group, profile, plan, completed.returncode)
    if completed.returncode != 0:
        return artifacts.RunOutcome(
            artifacts.artifact_path(
                workspace,
                group,
                fallback_dir=plan.diagnostic_artifacts_dir,
            ),
            payload,
            completed.returncode,
        )
    return _successful_outcome(workspace, group, plan, completed.stdout, payload)


def _plan_run(workspace: Path, group: provider.JavaGroup, profile: str) -> _RunPlan:
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
    return _RunPlan(
        config.java.gradle_args,
        config.java.findings_baseline,
        config.java.spotbugs_baseline,
        config.java.jacoco_ratchet_ref,
        config.java.jacoco_line_property,
        config.java.jacoco_branch_property,
        config.diagnostic_artifacts_dir,
        tasks,
        resolved_wrapper,
        report_plans,
        pre_run_reports,
    )


def _execution_payload(
    workspace: Path,
    group: provider.JavaGroup,
    profile: str,
    plan: _RunPlan,
    exit_code: int,
) -> dict[str, object]:
    payload = artifacts.base_payload(group, profile)
    payload.update(
        artifacts.execution_payload(
            workspace=workspace,
            wrapper=plan.wrapper,
            gradle_args=plan.gradle_args,
            tasks=plan.tasks,
            exit_code=exit_code,
        )
    )
    return payload


def _successful_outcome(
    workspace: Path,
    group: provider.JavaGroup,
    plan: _RunPlan,
    output: str,
    payload: dict[str, object],
) -> artifacts.RunOutcome:
    observation = observations.build_gradle_observation(
        plan.tasks,
        output,
        0,
        plan.pre_run_reports,
    )
    evidence = report_evidence.collect_report_evidence(
        workspace,
        plan.wrapper.gradle_root,
        plan.reports,
        observation,
        plan.findings_baseline,
    )
    coverage_thresholds = _coverage_threshold_reports(workspace, plan, evidence)
    payload["observation"] = observation.to_payload()
    if plan.reports:
        reports_payload = evidence.to_payload()
        if coverage_thresholds.payloads:
            reports_payload["coverage_thresholds"] = coverage_thresholds.payloads
        reports_payload["source_commit"] = _repository_head(workspace)
        payload["reports"] = reports_payload
        payload["reports_parsed"] = evidence.report_count > 0
        evidence_passed = evidence.passed and coverage_thresholds.passed
        payload["evidence_status"] = "validated" if evidence_passed else "regression"
    spotbugs_payload = evidence.spotbugs_payload()
    if plan.spotbugs_baseline and spotbugs_payload is not None:
        payload["spotbugs"] = spotbugs_payload
    policy_exit_code = 0 if evidence.passed and coverage_thresholds.passed else 1
    if policy_exit_code != 0:
        payload["status"] = "report-failed"
        payload["exit_code"] = policy_exit_code
    return artifacts.RunOutcome(
        artifacts.artifact_path(
            workspace,
            group,
            fallback_dir=plan.diagnostic_artifacts_dir,
        ),
        payload,
        policy_exit_code,
    )


def _coverage_threshold_reports(
    workspace: Path,
    plan: _RunPlan,
    evidence: report_evidence.JavaReportEvidence,
) -> _CoverageThresholds:
    properties = jacoco_thresholds.JacocoPropertyNames(
        plan.jacoco_line_property,
        plan.jacoco_branch_property,
    )
    reports = tuple(
        (
            fact,
            jacoco_thresholds.evaluate_thresholds(
                workspace,
                gradle_root=plan.wrapper.gradle_root,
                base_ref=plan.jacoco_ratchet_ref,
                properties=properties,
                coverage=fact.coverage,
            ),
        )
        for fact in evidence.coverage
    )
    return _CoverageThresholds(
        payloads=tuple(_coverage_threshold_payload(fact, report) for fact, report in reports),
        passed=all(report.passed for _fact, report in reports),
    )


def _coverage_threshold_payload(
    fact: report_evidence.JacocoCoverageFact,
    report: jacoco_thresholds.JacocoThresholdReport,
) -> dict[str, object]:
    return {
        "scope": fact.scope,
        "label": fact.label,
        "current_line": str(report.current.line),
        "current_branch": str(report.current.branch),
        "base_line": str(report.base.line),
        "base_branch": str(report.base.branch),
        "line_headroom": str(report.line_headroom),
        "branch_headroom": str(report.branch_headroom),
        "regressions": report.regressions,
    }


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
    except (TypeError, ValueError) as exc:
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
    valid = (
        completed.returncode == 0
        and MIN_GIT_HASH_LENGTH <= len(head) <= MAX_GIT_HASH_LENGTH
        and set(head) <= set("0123456789abcdef")
    )
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
