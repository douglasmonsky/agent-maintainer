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

from pathlib import Path

from agent_maintainer.catalogs.catalog import make_checks
from agent_maintainer.core.args import apply_cli_overrides, parse_args
from agent_maintainer.core.config import load_config
from agent_maintainer.verify.history import build_run_id
from agent_maintainer.verify.locking import VerificationLock, build_fingerprint
from agent_maintainer.verify.result_summary import (
    apply_optional_skip_policy,
    context_log_dir,
    print_result_summary,
)
from agent_maintainer.verify.run_steps import (
    collect_results,
    log_dir_for,
    write_artifacts_if_enabled,
)


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
    run_id = build_run_id(args.profile, fingerprint.to_dict())
    with VerificationLock(log_dir=log_dir, fingerprint=fingerprint) as verifier_lock:
        if verifier_lock.reused is not None:
            return print_reused_result(log_dir, verifier_lock.reused.exit_code)

        checks = make_checks(config, args.base_ref, args.compare_branch, staged=args.staged)
        selected = [check for check in checks if args.profile in check.profiles]
        results = collect_results(args, config, selected, log_dir)
        results = apply_optional_skip_policy(results, args.fail_on_optional_skip)
        write_artifacts_if_enabled(args, config, log_dir, results, run_id)
        exit_code = print_result_summary(
            args.profile,
            results,
            context_log_dir_value=context_log_dir(config, log_dir, run_id),
            run_id=run_id,
        )
        verifier_lock.write_result(exit_code)
        return exit_code


def print_reused_result(log_dir: Path, exit_code: int) -> int:
    """Print compact output for a same-state reused verifier result."""

    if exit_code == 0:
        print("PASS")
        return 0
    last_failure = log_dir / "LAST_FAILURE.md"
    print(f"FAIL: reused verifier result for same repository state. See {last_failure}.")
    return exit_code


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
