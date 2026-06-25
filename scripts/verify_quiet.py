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
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.guardrail_args import apply_cli_overrides, parse_args
from scripts.guardrail_catalog import make_checks
from scripts.guardrail_config import GuardrailConfig, load_config
from scripts.guardrail_executor import run_check
from scripts.guardrail_layout import layout_failures
from scripts.guardrail_models import Check, CheckResult
from scripts.guardrail_reporting import print_failures, print_success

LOG_DIR = Path(".verify-logs")


def emit_layout_failure(failures: list[str]) -> CheckResult:
    LOG_DIR.mkdir(exist_ok=True)
    failure_lines = "\n".join(f"  {failure}" for failure in failures)
    output = f"Guardrail layout/configuration failed:\n\n{failure_lines}"
    (LOG_DIR / "guardrail-layout.log").write_text(f"{output}\n", encoding="utf-8")
    return CheckResult("guardrail-layout", passed=False, output=output)


def collect_results(
    args: argparse.Namespace, config: GuardrailConfig, selected: list[Check]
) -> list[CheckResult]:
    layout = layout_failures(config, args.profile)
    if layout:
        return [emit_layout_failure(layout)]
    return [run_check(check, LOG_DIR, args.max_lines, args.max_chars) for check in selected]


def apply_optional_skip_policy(
    results: list[CheckResult], fail_on_optional_skip: bool
) -> list[CheckResult]:
    if not fail_on_optional_skip:
        return results
    return [
        (
            CheckResult(
                result.name,
                passed=False,
                output=f"optional check skipped: {result.output}",
                skipped=False,
            )
            if result.skipped
            else result
        )
        for result in results
    ]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = apply_cli_overrides(load_config(), args)
    checks = make_checks(config, args.base_ref, args.compare_branch, staged=args.staged)
    selected = [check for check in checks if args.profile in check.profiles]
    results = collect_results(args, config, selected)
    results = apply_optional_skip_policy(results, args.fail_on_optional_skip)

    failures = [result for result in results if not result.passed]
    skipped = [result for result in results if result.skipped]

    if not failures:
        print_success(skipped)
        return 0

    print_failures(args.profile, failures, skipped)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
