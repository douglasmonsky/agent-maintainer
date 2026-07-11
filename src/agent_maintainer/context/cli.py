"""Command-line interface for safe context expansion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_context import estimate as context_estimate
from agent_context import failures as context_failures
from agent_context.reading import diff as diff_reader
from agent_context.reading import diff_git
from agent_context.reading import files as file_reader
from agent_context.reading import logs as log_reader
from agent_maintainer.context import recall
from agent_maintainer.context.pack import cli as pack_cli

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
STORE_TRUE = "store_true"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse context command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer context")
    parser.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_diff_parser(lambda: subparsers.add_parser("diff", help="Show bounded Git diff context."))
    add_estimate_parser(
        lambda: subparsers.add_parser("estimate", help="Estimate context expansion size.")
    )
    add_file_parser(lambda: subparsers.add_parser("file", help="Show safe bounded file context."))
    add_failures_parser(
        lambda: subparsers.add_parser("failures", help="Show bounded verifier failures.")
    )
    add_log_parser(lambda: subparsers.add_parser("log", help="Show bounded verifier log output."))
    add_ledger_parser(lambda: subparsers.add_parser("ledger", help="Manage context recall ledger."))
    add_recall_parser(
        lambda: subparsers.add_parser("recall", help="Show context recall ledger items.")
    )
    pack_cli.add_pack_parser(
        lambda: subparsers.add_parser("pack", help="Write bounded repair context pack.")
    )
    return parser.parse_args(argv)


def add_diff_parser(parser_factory: pack_cli.ParserFactory) -> None:
    """Register diff subcommand."""

    parser = parser_factory()
    parser.add_argument("--summary", action=STORE_TRUE)
    parser.add_argument("--name-only", action=STORE_TRUE)
    parser.add_argument("--path")
    parser.add_argument("--hunks", type=int)
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--staged", action=STORE_TRUE)
    parser.add_argument("--limit", type=int, default=diff_git.DEFAULT_DIFF_PATH_LIMIT)
    parser.add_argument("--budget", type=int, default=context_failures.DEFAULT_CONTEXT_BUDGET)


def add_estimate_parser(parser_factory: pack_cli.ParserFactory) -> None:
    """Register estimate subcommand."""

    parser = parser_factory()
    parser.add_argument("--file", type=Path)
    parser.add_argument("--log")
    parser.add_argument("--diff", action=STORE_TRUE)
    parser.add_argument("--summary", action=STORE_TRUE)
    parser.add_argument("--head", type=int)
    parser.add_argument("--tail", type=int)
    parser.add_argument("--lines")
    parser.add_argument("--budget", type=int, default=context_failures.DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_file_parser(parser_factory: pack_cli.ParserFactory) -> None:
    """Register file subcommand."""

    parser = parser_factory()
    parser.add_argument("path", type=Path)
    parser.add_argument("--outline", action=STORE_TRUE)
    parser.add_argument("--symbols", action=STORE_TRUE)
    parser.add_argument("--symbol")
    parser.add_argument("--lines")
    parser.add_argument("--around", type=int)
    parser.add_argument("--context", type=int, default=file_reader.DEFAULT_FILE_CONTEXT_LINES)
    parser.add_argument("--budget", type=int, default=context_failures.DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_failures_parser(parser_factory: pack_cli.ParserFactory) -> None:
    """Register failures subcommand."""

    parser = parser_factory()
    parser.add_argument("--check")
    parser.add_argument("--limit", type=int, default=context_failures.DEFAULT_FAILURE_LIMIT)
    parser.add_argument("--budget", type=int, default=context_failures.DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_log_parser(parser_factory: pack_cli.ParserFactory) -> None:
    """Register log subcommand."""

    parser = parser_factory()
    parser.add_argument("check")
    parser.add_argument("--head", type=int)
    parser.add_argument("--tail", type=int)
    parser.add_argument("--lines")
    parser.add_argument("--budget", type=int, default=context_failures.DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--confirm-large", action=STORE_TRUE)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_ledger_parser(
    parser_factory: pack_cli.ParserFactory,
) -> None:
    """Register recall ledger mutation subcommands."""
    parser = parser_factory()
    ledger_subparsers = parser.add_subparsers(dest="ledger_command", required=True)
    add_parser = ledger_subparsers.add_parser("add", help="Add a recall ledger item.")
    add_parser.add_argument("--kind", required=True, choices=sorted(recall.VALID_KINDS))
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--path", action="append")
    add_parser.add_argument("--artifact", action="append")
    add_parser.add_argument("--command", action="append", dest="rehydrate_command")
    add_parser.add_argument("--tag", action="append")
    add_parser.add_argument("--value", action="append")
    add_parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_recall_parser(
    parser_factory: pack_cli.ParserFactory,
) -> None:
    """Register recall lookup subcommand."""
    parser = parser_factory()
    parser.add_argument("--kind", choices=sorted(recall.VALID_KINDS))
    parser.add_argument("--query")
    parser.add_argument("--limit", type=int, default=recall.DEFAULT_RECALL_LIMIT)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def main(argv: list[str]) -> int:
    """Run context command."""

    args = parse_args(argv)
    try:
        return run_context_command(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def run_context_command(args: argparse.Namespace) -> int:
    """Run parsed context subcommand."""

    runner = {
        "diff": run_diff,
        "estimate": run_estimate,
        "failures": run_failures,
        "file": run_file,
        "ledger": run_ledger,
        "log": run_log,
        "pack": pack_cli.run_pack,
        "recall": run_recall,
    }.get(args.command)
    if runner is not None:
        return runner(args)
    return 2


def run_estimate(args: argparse.Namespace) -> int:
    """Run estimate subcommand."""

    estimate = context_estimate.estimate_context(
        context_estimate.EstimateRequest(
            log_dir=args.log_dir,
            file_path=args.file,
            log_check=args.log,
            log_request=log_reader.LogRequest(
                head=args.head,
                tail=args.tail,
                line_range=args.lines,
            ),
            diff=args.diff,
            diff_summary=args.summary,
            budget=args.budget,
        ),
    )
    output = (
        context_estimate.render_estimate_json(estimate)
        if args.format == FORMAT_JSON
        else context_estimate.render_estimate_text(estimate)
    )
    print(output)
    return 0


def run_diff(args: argparse.Namespace) -> int:
    """Run diff subcommand."""

    result = diff_reader.render_diff(
        diff_git.DiffRequest(
            repo=Path.cwd(),
            base_ref=args.base_ref,
            staged=args.staged,
            summary=args.summary,
            name_only=args.name_only,
            path=args.path,
            limit=args.limit,
            hunks=args.hunks,
            budget=args.budget,
        ),
    )
    print(result.text)
    return 0


def run_file(args: argparse.Namespace) -> int:
    """Run file subcommand."""

    context = file_reader.select_file_context(
        file_reader.FileRequest(
            path=args.path,
            outline=args.outline,
            symbols=args.symbols,
            symbol=args.symbol,
            line_range=args.lines,
            around=args.around,
            context_lines=args.context,
            budget=args.budget,
        ),
    )
    output = (
        file_reader.render_file_json(context)
        if args.format == FORMAT_JSON
        else file_reader.render_file_text(context)
    )
    print(output)
    return 1 if context.refused else 0


def run_failures(args: argparse.Namespace) -> int:
    """Run failures subcommand."""

    records = context_failures.failure_records(
        args.log_dir,
        check_name=args.check,
        limit=args.limit,
    )
    output = (
        context_failures.render_failures_json(records, log_dir=args.log_dir)
        if args.format == FORMAT_JSON
        else context_failures.render_failures_text(
            records,
            log_dir=args.log_dir,
            budget=args.budget,
        )
    )
    print(output)
    return 0


def run_ledger(args: argparse.Namespace) -> int:
    """Run ledger mutation subcommands."""
    if args.ledger_command != "add":
        return 2
    item = recall.add_item(
        args.log_dir,
        recall.RecallInput(
            kind=args.kind,
            summary=args.summary,
            paths=tuple(args.path or ()),
            artifacts=tuple(args.artifact or ()),
            commands=tuple(args.rehydrate_command or ()),
            tags=tuple(args.tag or ()),
            values=tuple(args.value or ()),
        ),
    )
    output = (
        recall.render_item_json(item)
        if args.format == FORMAT_JSON
        else recall.render_item_text(item)
    )
    print(output)
    return 0


def run_recall(args: argparse.Namespace) -> int:
    """Run recall lookup subcommand."""
    items = recall.recall_items(
        args.log_dir,
        kind=args.kind,
        query=args.query,
        limit=args.limit,
    )
    output = (
        recall.render_items_json(items)
        if args.format == FORMAT_JSON
        else recall.render_recall_text(items)
    )
    print(output)
    return 0


def run_log(args: argparse.Namespace) -> int:
    """Run log subcommand."""

    selection = log_reader.select_log(
        args.log_dir,
        args.check,
        log_reader.LogRequest(
            head=args.head,
            tail=args.tail,
            line_range=args.lines,
            budget=args.budget,
            confirm_large=args.confirm_large,
        ),
    )
    output = (
        log_reader.render_log_json(selection)
        if args.format == FORMAT_JSON
        else log_reader.render_log_text(selection)
    )
    print(output)
    return 1 if selection.refused else 0
