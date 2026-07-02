"""Command line interface for DocSync."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from docsync.commands import core as core_commands

CommandHandler = Callable[[argparse.Namespace], int]


def main(argv: list[str] | None = None) -> int:
    """Run the DocSync command interface."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler: CommandHandler = args.handler
    return handler(args)


def console_main() -> None:
    """Console script entrypoint."""
    sys.exit(main(sys.argv[1:]))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsync",
        description="Documentation traceability freshness checks.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_core_commands(subparsers)
    return parser


def _add_core_commands(subparsers: Any) -> None:
    init_parser = subparsers.add_parser("init", help="Create .docsync files.")
    init_parser.add_argument("--force", action="store_true")
    init_parser.set_defaults(handler=core_commands.init_main_from_args)

    index_parser = subparsers.add_parser("index", help="Build index JSON.")
    index_parser.add_argument("--config", type=Path, default=None)
    index_parser.add_argument("--trace", type=Path, default=None)
    index_parser.set_defaults(handler=core_commands.index_main_from_args)

    check_parser = subparsers.add_parser("check", help="Run DocSync checks.")
    check_parser.add_argument("--base", default="origin/main")
    check_parser.add_argument("--config", type=Path, default=None)
    check_parser.add_argument("--trace", type=Path, default=None)
    check_parser.set_defaults(handler=core_commands.check_main_from_args)

    doctor_parser = subparsers.add_parser("doctor", help="Validate DocSync setup.")
    doctor_parser.add_argument("--config", type=Path, default=None)
    doctor_parser.add_argument("--trace", type=Path, default=None)
    doctor_parser.set_defaults(handler=core_commands.doctor_main_from_args)

    prompt_parser = subparsers.add_parser("prompt", help="Write review prompt files.")
    prompt_parser.add_argument("--base", default="origin/main")
    prompt_parser.add_argument("--config", type=Path, default=None)
    prompt_parser.add_argument("--trace", type=Path, default=None)
    prompt_parser.set_defaults(handler=core_commands.prompt_main_from_args)

    attest_parser = subparsers.add_parser("attest", help="Create an attestation.")
    attest_parser.add_argument("claim_id")
    attest_parser.add_argument("--reason", required=True)
    attest_parser.add_argument("--evidence", action="append", required=True)
    attest_parser.set_defaults(handler=core_commands.attest_main_from_args)
