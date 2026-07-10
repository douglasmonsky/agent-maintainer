"""Command line interface for DocSync."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from docsync.commands import core as core_commands
from docsync.commands import object_markers
from docsync.commands import trace as trace_commands

CommandHandler = Callable[[argparse.Namespace], int]


def main(argv: list[str] | None = None) -> int:
    """Run the DocSync command interface."""
    parser = _build_parser()
    args = parser.parse_args(_normalize_global_options(argv))
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
        help="Repository root. Defaults to current directory.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_core_commands(subparsers)
    return parser


def _normalize_global_options(argv: list[str] | None) -> list[str] | None:
    """Allow global options before or after subcommands."""
    if argv is None:
        return None
    moved, remaining = _split_global_options(list(argv))
    return [*moved, *remaining]


def _split_global_options(values: list[str]) -> tuple[list[str], list[str]]:
    moved: list[str] = []
    remaining: list[str] = []
    index = 0
    while index < len(values):
        index = _move_one_global_option(values, index, moved, remaining)
    return moved, remaining


def _move_one_global_option(
    values: list[str],
    index: int,
    moved: list[str],
    remaining: list[str],
) -> int:
    value = values[index]
    if value == "--repo-root" and index + 1 < len(values):
        moved.extend(values[index : index + 2])
        return index + 2
    if value.startswith("--repo-root="):
        moved.append(value)
        return index + 1
    remaining.append(value)
    return index + 1


# docsync:evidence.start evidence.docsync.cli_commands
def _add_core_commands(subparsers: Any) -> None:
    """Register core commands."""
    _add_init_command(subparsers)
    _add_index_command(subparsers)
    _add_freshness_command(subparsers)
    _add_check_command(subparsers)
    _add_doctor_command(subparsers)
    _add_prompt_command(subparsers)
    _add_repair_command(subparsers)
    _add_attest_command(subparsers)
    _add_trace_commands(subparsers)


def _add_init_command(subparsers: Any) -> None:
    parser = subparsers.add_parser("init", help="Create .docsync files.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--agents",
        action="store_true",
        help="Append the DocSync policy section to AGENTS.md.",
    )
    parser.set_defaults(handler=core_commands.init_main_from_args)


def _add_index_command(subparsers: Any) -> None:
    parser = subparsers.add_parser("index", help="Build index JSON.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--trace", type=Path, default=None)
    parser.set_defaults(handler=core_commands.index_main_from_args)


def _add_check_command(subparsers: Any) -> None:
    parser = subparsers.add_parser("check", help="Run DocSync checks.")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--trace", type=Path, default=None)
    parser.add_argument(
        "--write-reports",
        action="store_true",
        help="Write JSON and SARIF reports under the configured output root.",
    )
    parser.set_defaults(handler=core_commands.check_main_from_args)


def _add_doctor_command(subparsers: Any) -> None:
    parser = subparsers.add_parser("doctor", help="Validate DocSync setup.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--trace", type=Path, default=None)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe DocSync repairs before validation.",
    )
    parser.set_defaults(handler=core_commands.doctor_main_from_args)


def _add_prompt_command(subparsers: Any) -> None:
    parser = subparsers.add_parser("prompt", help="Write review prompt.")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--trace", type=Path, default=None)
    parser.set_defaults(handler=core_commands.prompt_main_from_args)


def _add_repair_command(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "repair-object-end-markers",
        help="Insert explicit Markdown object end markers.",
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--trace", type=Path, default=None)
    parser.add_argument("--write", action="store_true")
    parser.set_defaults(handler=object_markers.repair_object_end_markers_main_from_args)


def _add_attest_command(subparsers: Any) -> None:
    parser = subparsers.add_parser("attest", help="Create changed-claim attestation.")
    parser.add_argument("claim_id")
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--reason", required=True)
    parser.set_defaults(handler=core_commands.attest_main_from_args)


def _add_freshness_command(subparsers: Any) -> None:
    """Register passive freshness metadata command."""
    parser = subparsers.add_parser(
        "freshness",
        help="Write passive DocSync freshness metadata.",
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--trace", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    parser.set_defaults(handler=core_commands.freshness_main_from_args)


def _add_trace_commands(subparsers: Any) -> None:
    """Register trace authoring commands."""
    parser = subparsers.add_parser("trace", help="Author trace.yml entries.")
    trace_subparsers = parser.add_subparsers(dest="trace_command", required=True)
    _add_trace_document_command(trace_subparsers)
    _add_trace_object_command(trace_subparsers)
    _add_trace_evidence_command(trace_subparsers)
    _add_trace_claim_command(trace_subparsers)
    parser = trace_subparsers.add_parser("list", help="List trace IDs.")
    parser.add_argument("--trace", type=Path, default=None)
    parser.set_defaults(handler=trace_commands.list_main_from_args)


def _add_trace_document_command(trace_subparsers: Any) -> None:
    parser = trace_subparsers.add_parser("add-document", help="Add a document.")
    trace_commands.add_common_options(parser)
    parser.add_argument("document_id")
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--audience", required=True)
    parser.set_defaults(handler=trace_commands.add_document_main_from_args)


def _add_trace_object_command(trace_subparsers: Any) -> None:
    parser = trace_subparsers.add_parser("add-object", help="Add a doc object.")
    trace_commands.add_common_options(parser)
    parser.add_argument("object_id")
    parser.add_argument("--document", required=True)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--heading-level", type=int, default=None)
    parser.add_argument("--heading-text", default=None)
    parser.add_argument("--insert-marker", action="store_true")
    parser.set_defaults(handler=trace_commands.add_object_main_from_args)


def _add_trace_evidence_command(trace_subparsers: Any) -> None:
    parser = trace_subparsers.add_parser("add-evidence", help="Add evidence.")
    trace_commands.add_common_options(parser)
    parser.add_argument("evidence_id")
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--description", default=None)
    parser.add_argument("--insert-region", action="store_true")
    parser.set_defaults(handler=trace_commands.add_evidence_main_from_args)


def _add_trace_claim_command(trace_subparsers: Any) -> None:
    parser = trace_subparsers.add_parser("add-claim", help="Add a claim.")
    trace_commands.add_common_options(parser)
    parser.add_argument("claim_id")
    parser.add_argument("--object", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--severity", required=True)
    parser.add_argument("--evidence", action="append", required=True)
    parser.set_defaults(handler=trace_commands.add_claim_main_from_args)


# docsync:evidence.end evidence.docsync.cli_commands
