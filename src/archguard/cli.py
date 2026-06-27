"""Command line interface for Archguard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from archguard.decision_notes import (
    DEFAULT_DECISION_ROOTS,
    DEFAULT_POLICY_PATTERNS,
    decision_check_failures,
    new_decision_note,
)
from archguard.tach_config import tach_config_issues


def main(argv: list[str] | None = None) -> int:
    """Run the Archguard CLI."""
    parser = argparse.ArgumentParser(prog="archguard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tach_parser = subparsers.add_parser("tach-config")
    tach_parser.add_argument(
        "--strict-root-module",
        action="store_true",
        help='Require root_module = "forbid".',
    )

    decision_parser = subparsers.add_parser("decision-check")
    decision_parser.add_argument("--base-ref", default="HEAD")
    decision_parser.add_argument("--staged", action="store_true")
    decision_parser.add_argument(
        "--decision-root",
        action="append",
        default=[],
        help="Directory containing architecture decision notes. May be repeated.",
    )
    decision_parser.add_argument(
        "--policy-pattern",
        action="append",
        default=[],
        help="Architecture policy pattern to watch. May be repeated.",
    )

    decision_group = subparsers.add_parser("decision")
    decision_subparsers = decision_group.add_subparsers(
        dest="decision_command",
        required=True,
    )
    new_parser = decision_subparsers.add_parser("new")
    new_parser.add_argument("slug")
    new_parser.add_argument(
        "--decision-root",
        default=DEFAULT_DECISION_ROOTS[0],
        help="Directory where the decision note should be created.",
    )

    args = parser.parse_args(argv)
    if args.command == "tach-config":
        return tach_config_main_from_args(args)
    if args.command == "decision-check":
        return decision_check_main_from_args(args)
    if args.command == "decision" and args.decision_command == "new":
        return decision_new_main_from_args(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def console_main() -> None:
    """Console-script entrypoint for Archguard."""
    sys.exit(main(sys.argv[1:]))


def tach_config_main(argv: list[str] | None = None) -> int:
    """Run Tach configuration validation as a standalone CLI."""
    parser = argparse.ArgumentParser(description="Validate Tach architecture configuration.")
    parser.add_argument(
        "--strict-root-module",
        action="store_true",
        help='Require root_module = "forbid".',
    )
    return tach_config_main_from_args(parser.parse_args(argv))


def tach_config_main_from_args(args: argparse.Namespace) -> int:
    """Validate tach.toml and print discovered configuration issues."""
    issues = tach_config_issues(Path.cwd(), require_strict_root=args.strict_root_module)
    if not issues:
        print("tach.toml configured for architecture checks.")
        return 0
    for issue in issues:
        print(issue)
    return 1


def decision_check_main_from_args(args: argparse.Namespace) -> int:
    """Run the architecture decision-note gate."""
    decision_roots = tuple(args.decision_root) or DEFAULT_DECISION_ROOTS
    policy_patterns = tuple(args.policy_pattern) or DEFAULT_POLICY_PATTERNS
    failures = decision_check_failures(
        Path.cwd(),
        base_ref=args.base_ref,
        staged=args.staged,
        decision_roots=decision_roots,
        policy_patterns=policy_patterns,
    )
    if not failures:
        print("architecture decision notes cover architecture policy changes.")
        return 0
    for failure in failures:
        print(failure)
    return 1


def decision_new_main_from_args(args: argparse.Namespace) -> int:
    """Create a new architecture decision note."""
    path = new_decision_note(
        Path.cwd(),
        args.slug,
        decision_root=args.decision_root,
    )
    print(f"Created architecture decision note: {path}")
    return 0
