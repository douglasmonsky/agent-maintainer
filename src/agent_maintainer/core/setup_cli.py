"""Argument-safe bootstrap and local-integration commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.core import bootstrap as setup


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse setup command arguments before any mutation."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="install development dependencies only",
    )
    _add_target_and_preview(bootstrap_parser)
    install_parser = subparsers.add_parser(
        "install",
        help="install pre-commit and managed repo hooks",
    )
    _add_target_and_preview(install_parser)
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="replace known invalid managed config after backing it up",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Dispatch parsed setup commands."""

    args = parse_args(argv)
    if args.command == "bootstrap":
        return setup.bootstrap(target=args.target, dry_run=args.dry_run)
    if args.command == "install":
        return setup.install(
            target=args.target,
            dry_run=args.dry_run,
            force=args.force,
        )
    return 2


def _add_target_and_preview(parser: argparse.ArgumentParser) -> None:
    """Add common repository target and side-effect-free preview flags."""

    parser.add_argument(
        "--target",
        type=Path,
        help="repository root; defaults to discovery from the current directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned actions without changing files or installing packages",
    )
