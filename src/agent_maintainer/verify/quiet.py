#!/usr/bin/env python3
"""Run repository quality checks with low-noise output.

Passing checks are silent except for explicitly skipped optional integrations.
Failed checks print a capped, actionable summary and write full raw logs to
.verify-logs/.

Profiles:
- fast:       cheap checks suitable after file edits
- precommit: medium checks suitable before local commits
- full:       local full verification
- ci:         full verification plus changed-code coverage
- security:   manual security checks, such as full-history scans
- manual:     slow or expensive optional checks outside normal full
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path

from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.core import args as cli_args
from agent_maintainer.core import config as core_config
from agent_maintainer.verify import (
    async_jobs,
    background_wait,
    partial_runs,
    profile_overlap,
    runtime_eventing,
)
from agent_maintainer.verify.locking import (
    VerificationFingerprint,
    VerificationLock,
    build_fingerprint,
)
from agent_maintainer.verify.result_summary import (
    apply_optional_skip_policy,
    context_log_dir,
    print_result_summary,
)
from agent_maintainer.verify.run_steps import (
    ArtifactWriteOptions,
    collect_results,
    log_dir_for,
    write_artifacts_if_enabled,
)
from agent_run_artifacts.history import build_run_id, run_snapshot_dir

USAGE_ERROR_STATUS = partial_runs.USAGE_ERROR_STATUS


@dataclass(frozen=True)
class VerificationRun:
    """State shared by one foreground verifier run."""

    args: cli_args.ParsedArgs
    config: core_config.MaintainerConfig
    log_dir: Path
    fingerprint: VerificationFingerprint
    run_id: str


def main(argv: list[str]) -> int:
    """Run selected verifier profile and print compact results."""

    args = cli_args.parse_args(argv)
    if args.aggregate_partial is not None:
        return partial_runs.aggregate_partial_results(args)
    if not partial_runs.valid_group(args.group):
        print(f"FAIL: unknown verification group: {args.group}", file=sys.stderr)
        return USAGE_ERROR_STATUS
    config = cli_args.apply_cli_overrides(core_config.load_config(), args)
    log_dir = log_dir_for(config)
    fingerprint = replace(
        build_fingerprint(
            repo_root=Path.cwd(),
            profile=args.profile,
            base_ref=args.base_ref,
            compare_branch=args.compare_branch,
            staged=args.staged,
        ),
        group=args.group or "",
    )
    run_id = args.run_id or build_run_id(args.profile, fingerprint.to_dict())
    if _codex_background_verify(args) or args.async_verify:
        return start_async_verifier(
            args.profile,
            argv,
            log_dir,
            fingerprint.to_dict(),
            run_id,
        )
    return run_foreground_verifier(
        VerificationRun(
            args=args,
            config=config,
            log_dir=log_dir,
            fingerprint=fingerprint,
            run_id=run_id,
        )
    )


def run_foreground_verifier(run: VerificationRun) -> int:
    """Coordinate lifecycle and locking for one foreground verifier run."""

    profile_events = runtime_eventing.ProfileRuntimeEvents.create(
        run.config,
        profile=run.args.profile,
        run_id=run.run_id,
    )
    if run.args.profile == "manual":
        runtime_eventing.manual_escalation(
            profile_events,
            fingerprint=run.fingerprint.to_dict(),
        )
    with VerificationLock(
        log_dir=run.log_dir,
        fingerprint=run.fingerprint,
        reuse_result=not run.args.force,
        run_id=run.run_id,
    ) as verifier_lock:
        if verifier_lock.reused is not None:
            runtime_eventing.run_reused(
                profile_events,
                exit_code=verifier_lock.reused.exit_code,
                log_dir=run.log_dir,
                fingerprint=run.fingerprint.to_dict(),
            )
            profile_events.finished(
                status="reused",
                exit_code=verifier_lock.reused.exit_code,
                log_dir=run.log_dir,
            )
            return print_reused_result(
                run.args.profile,
                run.log_dir,
                verifier_lock.reused.exit_code,
            )
        return run_fresh_verifier(run, profile_events, verifier_lock)


def run_fresh_verifier(
    run: VerificationRun,
    profile_events: runtime_eventing.ProfileRuntimeEvents,
    verifier_lock: VerificationLock,
) -> int:
    """Execute and record a fresh verifier selection."""

    execution_log_dir = run_snapshot_dir(run.log_dir, run.run_id)
    profile_events.started(execution_log_dir)
    runtime_eventing.run_fresh(
        profile_events,
        log_dir=execution_log_dir,
        fingerprint=run.fingerprint.to_dict(),
    )
    execution_config = replace(
        run.config,
        diagnostic_artifacts_dir=str(execution_log_dir),
    )
    checks = make_checks(
        execution_config,
        run.args.base_ref,
        run.args.compare_branch,
        staged=run.args.staged,
    )
    profile_checks = [check for check in checks if run.args.profile in check.profiles]
    try:
        selected_checks = partial_runs.select_checks(profile_checks, run.args.group)
    except partial_runs.PartialRunSelectionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return USAGE_ERROR_STATUS
    results = collect_results(
        run.args,
        execution_config,
        selected_checks,
        execution_log_dir,
        runtime_events=profile_events,
    )
    results = apply_optional_skip_policy(results, run.args.fail_on_optional_skip)
    write_artifacts_if_enabled(
        run.args,
        run.config,
        run.log_dir,
        results,
        options=ArtifactWriteOptions(
            run_id=run.run_id,
            runtime_events=runtime_eventing.artifact_events_for(profile_events),
            partial=partial_runs.partial_run_context(
                run.args,
                run.fingerprint.to_dict(),
                selected_checks,
            ),
        ),
    )
    exit_code = print_result_summary(
        run.args.profile,
        results,
        context_log_dir_value=context_log_dir(run.config, run.log_dir, run.run_id),
        run_id=run.run_id,
    )
    if exit_code == 0:
        profile_overlap.print_profile_overlap_advisory(
            profile_overlap.profile_overlap_advisory(run.args.profile, run.config),
        )
    verifier_lock.write_result(exit_code)
    profile_events.finished(
        status="pass" if exit_code == 0 else "fail",
        exit_code=exit_code,
        log_dir=execution_log_dir,
    )
    return exit_code


def print_reused_result(profile: str, log_dir: Path, exit_code: int) -> int:
    """Print compact output for same-state reused verifier result."""

    if exit_code == 0:
        print("PASS")
        return 0
    last_failure = log_dir / "LAST_FAILURE.md"
    print(f"FAIL: reused verifier result for same repository state. See {last_failure}.")
    print(f"Retry: python3 -m agent_maintainer verify --profile {profile} --force")
    return exit_code


def start_async_verifier(
    profile: str,
    argv: list[str],
    log_dir: Path,
    fingerprint: dict[str, object],
    run_id: str,
) -> int:
    """Start background verifier print wait-ready capsule."""

    request = async_jobs.AsyncVerifierRequest(
        argv=argv,
        profile=profile,
        run_id=run_id,
        log_dir=log_dir,
        fingerprint=fingerprint,
    )
    try:
        launch = async_jobs.launch_async_verifier(request)
    except async_jobs.AsyncVerifierLaunchError as exc:
        print(f"FAIL async verifier launch: {exc}", file=sys.stderr)
        print(f"State: {exc.state_path}", file=sys.stderr)
        return 2
    if _codex_background_async_launch():
        registration = background_wait.register_background_verifier_wait(
            launch.run_id,
            log_dir,
        )
        print(background_wait.render_background_registration_text(registration))
        return 0
    print(async_jobs.render_async_launch(launch))
    return 0


def _codex_background_verify(args: object) -> bool:
    """Return whether Codex should background this verifier run."""

    return (
        not getattr(args, "async_verify", False)
        and not getattr(args, "run_id", "")
        and _codex_background_async_launch()
    )


def _codex_background_async_launch() -> bool:
    """Return whether async verifier launch should register a wait."""

    return background_wait.background_launch_enabled()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
