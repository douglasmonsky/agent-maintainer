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
from dataclasses import replace
from pathlib import Path

from guardrail_lib.verify.artifacts import RunContext, write_run_artifacts
from scripts.guardrail_args import apply_cli_overrides, parse_args
from scripts.guardrail_catalog import make_checks
from scripts.guardrail_config import GuardrailConfig, load_config
from scripts.guardrail_executor import run_check, utc_timestamp
from scripts.guardrail_layout import layout_failures
from scripts.guardrail_models import Check, CheckResult
from scripts.guardrail_reporting import print_failures, print_success


def log_dir_for(config: GuardrailConfig) -> Path:
    """Return the configured verifier log and artifact directory."""

    return Path(config.diagnostic_artifacts_dir)


def emit_layout_failure(failures: list[str], log_dir: Path) -> CheckResult:
    """Write and return a synthetic failure for invalid guardrail layout."""

    timestamp = utc_timestamp()
    log_dir.mkdir(parents=True, exist_ok=True)
    failure_lines = "\n".join(f"  {failure}" for failure in failures)
    output = f"Guardrail layout/configuration failed:\n\n{failure_lines}"
    log_path = log_dir / "guardrail-layout.log"
    log_path.write_text(f"{output}\n", encoding="utf-8")
    return CheckResult(
        "guardrail-layout",
        passed=False,
        output=output,
        log_path=str(log_path),
        started_at=timestamp,
        ended_at=timestamp,
    )


def collect_results(
    args,
    config: GuardrailConfig,
    selected: list[Check],
    log_dir: Path | None = None,
) -> list[CheckResult]:
    """Run selected checks after validating layout requirements."""

    selected_log_dir = log_dir or log_dir_for(config)
    layout = layout_failures(config, args.profile)
    if layout:
        return [emit_layout_failure(layout, selected_log_dir)]
    return [
        run_check(check, selected_log_dir, args.max_lines, args.max_chars) for check in selected
    ]


def apply_optional_skip_policy(
    results: list[CheckResult], fail_on_optional_skip: bool
) -> list[CheckResult]:
    """Convert optional skips into failures when the caller asks for strictness."""

    if not fail_on_optional_skip:
        return results
    return [
        (
            replace(
                result,
                passed=False,
                output=f"optional check skipped: {result.output}",
                skipped=False,
            )
            if result.skipped
            else result
        )
        for result in results
    ]


def write_artifacts_if_enabled(
    args,
    config: GuardrailConfig,
    log_dir: Path,
    results: list[CheckResult],
) -> None:
    """Write verifier artifacts when diagnostics are enabled."""

    if not config.diagnostic_artifacts_enabled:
        return
    write_run_artifacts(
        log_dir,
        RunContext(
            repo_root=Path.cwd(),
            profile=args.profile,
            base_ref=args.base_ref,
            compare_branch=args.compare_branch,
            staged=args.staged,
            config=config,
        ),
        results,
    )


def main(argv: list[str]) -> int:
    """Run the selected verifier profile and print compact results."""

    args = parse_args(argv)
    config = apply_cli_overrides(load_config(), args)
    log_dir = log_dir_for(config)
    checks = make_checks(config, args.base_ref, args.compare_branch, staged=args.staged)
    selected = [check for check in checks if args.profile in check.profiles]
    results = collect_results(args, config, selected, log_dir)
    results = apply_optional_skip_policy(results, args.fail_on_optional_skip)
    write_artifacts_if_enabled(args, config, log_dir, results)

    failures = [result for result in results if not result.passed]
    skipped = [result for result in results if result.skipped]
    warnings = [result for result in results if result.warning]

    if not failures:
        print_success(skipped, warnings)
        return 0

    print_failures(args.profile, failures, skipped)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
