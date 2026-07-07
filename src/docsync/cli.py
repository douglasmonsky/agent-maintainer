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
    normalized = list(argv)
    moved: list[str] = []
    index = 0
    while index < len(normalized):
        value = normalized[index]
        if value == "--repo-root" and index + 1 < len(normalized):
            moved.extend(normalized[index : index + 2])
            del normalized[index : index + 2]
            continue
        if value.startswith("--repo-root="):
            moved.append(value)
            del normalized[index]
            continue
        index += 1
    return [*moved, *normalized]


# docsync:evidence.start evidence.docsync.cli_commands
def _add_core_commands(subparsers: Any) -> None:
    init_parser = subparsers.add_parser("init", help="Create .docsync files.")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument(
        "--agents",
        action="store_true",
        help="Append the DocSync policy section to AGENTS.md.",
    )
    init_parser.set_defaults(handler=core_commands.init_main_from_args)

    index_parser = subparsers.add_parser("index", help="Build index JSON.")
    index_parser.add_argument("--config", type=Path, default=None)
    index_parser.add_argument("--trace", type=Path, default=None)
    index_parser.set_defaults(handler=core_commands.index_main_from_args)

    _add_freshness_command(subparsers)
    check_parser = subparsers.add_parser("check", help="Run DocSync checks.")
    check_parser.add_argument("--base", default="origin/main")
    check_parser.add_argument("--config", type=Path, default=None)
    check_parser.add_argument("--trace", type=Path, default=None)
    check_parser.set_defaults(handler=core_commands.check_main_from_args)

    doctor_parser = subparsers.add_parser("doctor", help="Validate DocSync setup.")
    doctor_parser.add_argument("--config", type=Path, default=None)
    doctor_parser.add_argument("--trace", type=Path, default=None)
    doctor_parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe DocSync repairs before validation.",
    )
    doctor_parser.set_defaults(handler=core_commands.doctor_main_from_args)

    prompt_parser = subparsers.add_parser("prompt", help="Write review prompt.")
    prompt_parser.add_argument("--base", default="origin/main")
    prompt_parser.add_argument("--config", type=Path, default=None)
    prompt_parser.add_argument("--trace", type=Path, default=None)
    prompt_parser.set_defaults(handler=core_commands.prompt_main_from_args)

    repair_parser = subparsers.add_parser(
        "repair-object-end-markers",
        help="Insert explicit Markdown object end markers.",
    )
    repair_parser.add_argument("--config", type=Path, default=None)
    repair_parser.add_argument("--trace", type=Path, default=None)
    repair_parser.add_argument("--write", action="store_true")
    repair_parser.set_defaults(handler=object_markers.repair_object_end_markers_main_from_args)

    attest_parser = subparsers.add_parser("attest", help="Create changed-claim attestation.")
    attest_parser.add_argument("claim_id")
    attest_parser.add_argument("--evidence", action="append", required=True)
    attest_parser.add_argument("--reason", required=True)
    attest_parser.set_defaults(handler=core_commands.attest_main_from_args)
    _add_trace_commands(subparsers)


def _add_freshness_command(subparsers: Any) -> None:
    """Register passive freshness metadata command."""
    freshness_parser = subparsers.add_parser(
        "freshness",
        help="Write passive DocSync freshness metadata.",
    )
    freshness_parser.add_argument("--config", type=Path, default=None)
    freshness_parser.add_argument("--trace", type=Path, default=None)
    freshness_parser.add_argument("--output", type=Path, default=None)
    freshness_parser.add_argument("--no-write", action="store_true")
    freshness_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    freshness_parser.set_defaults(handler=core_commands.freshness_main_from_args)


def _add_trace_commands(subparsers: Any) -> None:
    """Register trace authoring commands."""
    trace_parser = subparsers.add_parser("trace", help="Author trace.yml entries.")
    trace_subparsers = trace_parser.add_subparsers(dest="trace_command", required=True)

    document = trace_subparsers.add_parser("add-document", help="Add a document.")
    trace_commands.add_common_options(document)
    document.add_argument("document_id")
    document.add_argument("--path", type=Path, required=True)
    document.add_argument("--title", required=True)
    document.add_argument("--audience", required=True)
    document.set_defaults(handler=trace_commands.add_document_main_from_args)

    doc_object = trace_subparsers.add_parser("add-object", help="Add a doc object.")
    trace_commands.add_common_options(doc_object)
    doc_object.add_argument("object_id")
    doc_object.add_argument("--document", required=True)
    doc_object.add_argument("--path", type=Path, required=True)
    doc_object.add_argument("--marker", required=True)
    doc_object.add_argument("--heading-level", type=int, default=None)
    doc_object.add_argument("--heading-text", default=None)
    doc_object.add_argument("--insert-marker", action="store_true")
    doc_object.set_defaults(handler=trace_commands.add_object_main_from_args)

    evidence = trace_subparsers.add_parser("add-evidence", help="Add evidence.")
    trace_commands.add_common_options(evidence)
    evidence.add_argument("evidence_id")
    evidence.add_argument("--path", type=Path, required=True)
    evidence.add_argument("--type", required=True)
    evidence.add_argument("--description", default=None)
    evidence.add_argument("--insert-region", action="store_true")
    evidence.set_defaults(handler=trace_commands.add_evidence_main_from_args)

    claim = trace_subparsers.add_parser("add-claim", help="Add a claim.")
    trace_commands.add_common_options(claim)
    claim.add_argument("claim_id")
    claim.add_argument("--object", required=True)
    claim.add_argument("--text", required=True)
    claim.add_argument("--severity", required=True)
    claim.add_argument("--evidence", action="append", required=True)
    claim.set_defaults(handler=trace_commands.add_claim_main_from_args)

    list_parser = trace_subparsers.add_parser("list", help="List trace IDs.")
    list_parser.add_argument("--trace", type=Path, default=None)
    list_parser.set_defaults(handler=trace_commands.list_main_from_args)


# docsync:evidence.end evidence.docsync.cli_commands
