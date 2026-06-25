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
import os
import sys
from dataclasses import replace
from pathlib import Path

from scripts.guardrail_catalog import make_checks
from scripts.guardrail_config import VALID_MODES, GuardrailConfig, apply_mode, load_config
from scripts.guardrail_executor import run_check
from scripts.guardrail_layout import layout_failures
from scripts.guardrail_models import Check, CheckResult
from scripts.guardrail_reporting import print_failures, print_success

LOG_DIR = Path(".verify-logs")
DEFAULT_MAX_LINES_PER_FAILURE = 50
DEFAULT_MAX_CHARS_PER_FAILURE = 8_000


def parse_csv_like(values: list[str] | None) -> tuple[str, ...] | None:
    if not values:
        return None
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    normalized = tuple(item.rstrip("/") or "." for item in items if item)
    return normalized or None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("fast", "precommit", "full", "ci"),
        default="full",
    )
    parser.add_argument("--base-ref", default=os.getenv("BASE_REF", "HEAD"))
    parser.add_argument("--compare-branch", default=os.getenv("COMPARE_BRANCH", "origin/main"))
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES_PER_FAILURE)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS_PER_FAILURE)
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Use staged changes for diff-based checks.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        help="Apply a guardrail preset for this run before other CLI overrides.",
    )

    parser.add_argument(
        "--source-root",
        action="append",
        help="Configured Python source root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--test-root",
        action="append",
        help="Configured Python test root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--coverage-source",
        action="append",
        help="Coverage source passed to pytest-cov. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--package-path",
        action="append",
        help="Package/source paths for static analysis. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--file-length-path",
        action="append",
        help="Paths scanned by the file-length check. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--vulture-path",
        action="append",
        help="Paths scanned by vulture. May be repeated or comma-separated.",
    )
    parser.add_argument("--coverage-fail-under", type=int)
    parser.add_argument("--diff-cover-fail-under", type=int)
    parser.add_argument("--require-tests", action="store_true", default=None)
    parser.add_argument("--no-require-tests", action="store_false", dest="require_tests")
    parser.add_argument("--enable-pip-audit", action="store_true", default=None)
    parser.add_argument("--disable-pip-audit", action="store_false", dest="enable_pip_audit")
    parser.add_argument("--enable-wemake", action="store_true", default=None)
    parser.add_argument("--disable-wemake", action="store_false", dest="enable_wemake")
    parser.add_argument(
        "--fail-on-optional-skip",
        action="store_true",
        help="Treat skipped optional integrations, such as absent .importlinter, as failures.",
    )
    return parser.parse_args(argv)


def apply_cli_overrides(config: GuardrailConfig, args: argparse.Namespace) -> GuardrailConfig:
    if args.mode is not None:
        config = apply_mode(config, args.mode)

    updates: dict[str, object] = {}

    tuple_overrides = {
        "source_roots": parse_csv_like(args.source_root),
        "test_roots": parse_csv_like(args.test_root),
        "coverage_source": parse_csv_like(args.coverage_source),
        "package_paths": parse_csv_like(args.package_path),
        "file_length_paths": parse_csv_like(args.file_length_path),
        "vulture_paths": parse_csv_like(args.vulture_path),
    }
    scalar_overrides = {
        "coverage_fail_under": args.coverage_fail_under,
        "diff_cover_fail_under": args.diff_cover_fail_under,
        "require_tests": args.require_tests,
        "enable_pip_audit": args.enable_pip_audit,
        "enable_wemake": args.enable_wemake,
    }

    updates.update({field: value for field, value in tuple_overrides.items() if value is not None})
    updates.update({field: value for field, value in scalar_overrides.items() if value is not None})

    return replace(config, **updates)


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
