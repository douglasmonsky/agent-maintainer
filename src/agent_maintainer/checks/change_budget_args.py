"""Argument parsing for change-budget checks."""

from __future__ import annotations

import argparse
from dataclasses import replace

from agent_maintainer.core.config import MaintainerConfig


def parse_csv_like(values: list[str] | None) -> tuple[str, ...] | None:
    """Normalize repeated comma-separated CLI path options."""

    if not values:
        return None
    items: list[str] = []
    for value in values:
        items.extend(part.strip() for part in value.split(","))
    normalized = tuple(item.rstrip("/") or "." for item in items if item)
    return normalized or None


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse diff-budget command-line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Fail extreme, hard-to-review Python diffs. This intentionally "
            "is a change-budget gate, not a universal review policy. It "
            "excludes common generated/lock/binary files and focuses on "
            "Python source spread. Source and test roots are configurable "
            "through [tool.agent_maintainer], environment variables, and CLI "
            "flags."
        )
    )
    parser.add_argument(
        "base_ref",
        nargs="?",
        default="HEAD",
        help="Git ref to compare against. Ignored when --staged is set.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Inspect staged changes with git diff --cached.",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        help="Source root. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--test-root",
        action="append",
        help="Test root. May be repeated or comma-separated.",
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
    parser.add_argument(
        "--missing-test-change-as-error",
        action="store_true",
        help=("Exit nonzero only when source changed without configured test changes."),
    )
    parser.add_argument(
        "--allow-source-without-test-change",
        action="store_true",
        help="Do not warn when source changes are covered by existing tests.",
    )
    return parser.parse_args(argv)


def apply_cli_overrides(
    config: MaintainerConfig,
    args: argparse.Namespace,
) -> MaintainerConfig:
    """Apply root overrides without changing unrelated maintenance settings."""

    updates: dict[str, object] = {}
    source_roots = parse_csv_like(args.source_root)
    test_roots = parse_csv_like(args.test_root)
    if source_roots is not None:
        updates["source_roots"] = source_roots
    if test_roots is not None:
        updates["test_roots"] = test_roots
    return replace(config, **updates)
