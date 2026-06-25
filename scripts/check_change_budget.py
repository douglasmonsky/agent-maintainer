#!/usr/bin/env python3
"""Fail extreme, hard-to-review Python diffs.

This is intentionally a change-budget gate, not a universal review policy. It
excludes common generated/lock/binary files and focuses on Python source spread.
Source and test roots are configurable through [tool.ai_guardrails], environment
variables, or CLI flags.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass, replace

from guardrail_config import GuardrailConfig, load_config, path_matches_roots

NUMSTAT_FIELD_COUNT = 3

EXCLUDED_SUFFIXES = (
    ".lock",
    ".snap",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
)
EXCLUDED_NAMES = {
    "uv.lock",
    "poetry.lock",
    "pdm.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int
    deleted: int

    @property
    def changed(self) -> int:
        return self.added + self.deleted


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
        "base_ref",
        nargs="?",
        default="HEAD",
        help="Git ref to compare against. Use origin/main in CI.",
    )
    parser.add_argument(
        "--source-root", action="append", help="Source root. May be repeated or comma-separated."
    )
    parser.add_argument(
        "--test-root", action="append", help="Test root. May be repeated or comma-separated."
    )
    parser.add_argument("--warn-lines", type=int)
    parser.add_argument("--block-lines", type=int)
    parser.add_argument("--warn-files", type=int)
    parser.add_argument("--block-files", type=int)
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Exit nonzero for soft-budget warnings. Useful for agent hooks.",
    )
    return parser.parse_args(argv)


def apply_cli_overrides(config: GuardrailConfig, args: argparse.Namespace) -> GuardrailConfig:
    updates: dict[str, object] = {}
    source_roots = parse_csv_like(args.source_root)
    test_roots = parse_csv_like(args.test_root)
    if source_roots is not None:
        updates["source_roots"] = source_roots
    if test_roots is not None:
        updates["test_roots"] = test_roots
    return replace(config, **updates)


def should_exclude(path: str) -> bool:
    name = path.rsplit("/", maxsplit=1)[-1]
    return name in EXCLUDED_NAMES or path.endswith(EXCLUDED_SUFFIXES)


def is_python_source(path: str, source_roots: tuple[str, ...]) -> bool:
    return path.endswith(".py") and path_matches_roots(path, source_roots)


def is_python_test(path: str, test_roots: tuple[str, ...]) -> bool:
    return path.endswith(".py") and path_matches_roots(path, test_roots)


def run_git_numstat(base_ref: str) -> list[FileChange]:
    git = shutil.which("git") or "git"
    try:
        result = subprocess.run(  # nosec B603
            [git, "diff", "--numstat", base_ref, "--"],
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        raise RuntimeError(f"Could not calculate diff against {base_ref!r}: {stderr}") from exc

    changes: list[FileChange] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != NUMSTAT_FIELD_COUNT:
            continue
        added_raw, deleted_raw, path = parts
        if added_raw == "-" or deleted_raw == "-" or should_exclude(path):
            continue
        changes.append(FileChange(path=path, added=int(added_raw), deleted=int(deleted_raw)))
    return changes


def changed_python_files(
    changes: list[FileChange], config: GuardrailConfig
) -> tuple[list[FileChange], list[FileChange]]:
    py_source_changes = [
        change for change in changes if is_python_source(change.path, config.source_roots)
    ]
    py_test_changes = [
        change for change in changes if is_python_test(change.path, config.test_roots)
    ]
    return py_source_changes, py_test_changes


def budget_messages(
    args: argparse.Namespace,
    config: GuardrailConfig,
    py_source_changes: list[FileChange],
    py_test_changes: list[FileChange],
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    failures: list[str] = []
    failures.extend(line_budget_failures(args, config, py_source_changes, warnings))
    failures.extend(file_budget_failures(args, config, py_source_changes, warnings))

    if py_source_changes and not py_test_changes and config.require_tests:
        warnings.append("Python source changed, but no configured Python test files changed.")

    return failures, warnings


def line_budget_failures(
    args: argparse.Namespace,
    config: GuardrailConfig,
    py_source_changes: list[FileChange],
    warnings: list[str],
) -> list[str]:
    total = sum(change.changed for change in py_source_changes)
    warn_limit = args.warn_lines or config.change_warn_lines
    block_limit = args.block_lines or config.change_block_lines
    if total > block_limit:
        return [
            f"Python source diff is too large: {total} changed lines (block limit: {block_limit})."
        ]
    if total > warn_limit:
        warnings.append(
            f"Large Python source diff: {total} changed lines (warning threshold: {warn_limit})."
        )
    return []


def file_budget_failures(
    args: argparse.Namespace,
    config: GuardrailConfig,
    py_source_changes: list[FileChange],
    warnings: list[str],
) -> list[str]:
    total = len(py_source_changes)
    warn_limit = args.warn_files or config.change_warn_files
    block_limit = args.block_files or config.change_block_files
    if total > block_limit:
        return [f"Too many Python source files touched: {total} (block limit: {block_limit})."]
    if total > warn_limit:
        warnings.append(
            f"Many Python source files touched: {total} (warning threshold: {warn_limit})."
        )
    return []


def print_failure_report(failures: list[str], warnings: list[str]) -> None:
    print("Change budget failed:\n")
    for failure in failures:
        print(f"  BLOCK: {failure}")
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  WARN: {warning}")
    print("\nSplit the work into smaller commits/tasks or document why this is mechanical.")


def print_warning_report(warnings: list[str]) -> None:
    print("Change budget warnings:\n")
    for warning in warnings:
        print(f"  WARN: {warning}")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = apply_cli_overrides(load_config(), args)

    try:
        changes = run_git_numstat(args.base_ref)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    py_source_changes, py_test_changes = changed_python_files(changes, config)
    failures, warnings = budget_messages(args, config, py_source_changes, py_test_changes)

    if failures:
        print_failure_report(failures, warnings)
        return 1

    if warnings:
        print_warning_report(warnings)
        if args.warnings_as_errors:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
