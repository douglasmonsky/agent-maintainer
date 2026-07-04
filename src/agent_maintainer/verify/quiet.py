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

from dataclasses import replace
from pathlib import Path

from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.core.args import apply_cli_overrides, parse_args
from agent_maintainer.core.config import load_config
from agent_maintainer.verify import async_jobs, profile_overlap, runtime_eventing
from agent_maintainer.verify.locking import VerificationLock, build_fingerprint
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


def main(argv: list[str]) -> int:
    """Run selected verifier profile and print compact results."""

    args = parse_args(argv)
    config = apply_cli_overrides(load_config(), args)
    log_dir = log_dir_for(config)
    fingerprint = build_fingerprint(
        repo_root=Path.cwd(),
        profile=args.profile,
        base_ref=args.base_ref,
        compare_branch=args.compare_branch,
        staged=args.staged,
    )
    run_id = args.run_id or build_run_id(args.profile, fingerprint.to_dict())
    if args.async_verify:
        return start_async_verifier(
            args.profile,
            argv,
            log_dir,
            fingerprint.to_dict(),
            run_id,
        )

    profile_events = runtime_eventing.ProfileRuntimeEvents.create(
        config,
        profile=args.profile,
        run_id=run_id,
    )
    with VerificationLock(
        log_dir=log_dir,
        fingerprint=fingerprint,
        reuse_result=not args.force,
        run_id=run_id,
    ) as verifier_lock:
        if verifier_lock.reused is not None:
            runtime_eventing.run_reused(
                profile_events,
                exit_code=verifier_lock.reused.exit_code,
                log_dir=log_dir,
            )
            profile_events.finished(
                status="reused",
                exit_code=verifier_lock.reused.exit_code,
                log_dir=log_dir,
            )
            return print_reused_result(args.profile, log_dir, verifier_lock.reused.exit_code)

        execution_log_dir = run_snapshot_dir(log_dir, run_id)
        profile_events.started(execution_log_dir)
        runtime_eventing.run_fresh(profile_events, log_dir=execution_log_dir)
        execution_config = replace(
            config,
            diagnostic_artifacts_dir=str(execution_log_dir),
        )
        checks = make_checks(
            execution_config,
            args.base_ref,
            args.compare_branch,
            staged=args.staged,
        )
        results = collect_results(
            args,
            execution_config,
            [check for check in checks if args.profile in check.profiles],
            execution_log_dir,
            runtime_events=profile_events,
        )
        results = apply_optional_skip_policy(results, args.fail_on_optional_skip)
        write_artifacts_if_enabled(
            args,
            config,
            log_dir,
            results,
            options=ArtifactWriteOptions(
                run_id=run_id,
                runtime_events=runtime_eventing.artifact_events_for(profile_events),
            ),
        )
        exit_code = print_result_summary(
            args.profile,
            results,
            context_log_dir_value=context_log_dir(config, log_dir, run_id),
            run_id=run_id,
        )
        if exit_code == 0:
            profile_overlap.print_profile_overlap_advisory(
                profile_overlap.profile_overlap_advisory(args.profile, config),
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
    """Start background verifier and print wait-ready capsule."""
    request = async_jobs.AsyncVerifierRequest(
        argv=argv,
        profile=profile,
        run_id=run_id,
        log_dir=log_dir,
        fingerprint=fingerprint,
    )
    print(async_jobs.render_async_launch(async_jobs.launch_async_verifier(request)))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
