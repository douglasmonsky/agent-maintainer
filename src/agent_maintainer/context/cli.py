"""Command-line interface for safe context expansion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.context.failures import (
    DEFAULT_CONTEXT_BUDGET,
    DEFAULT_FAILURE_LIMIT,
    failure_records,
    render_failures_json,
    render_failures_text,
)
from agent_maintainer.context.logs import LogRequest, render_log_json, render_log_text, select_log

FORMAT_JSON = "json"
FORMAT_TEXT = "text"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse context command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer context")
    parser.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_failures_parser(subparsers)
    add_log_parser(subparsers)
    return parser.parse_args(argv)


def add_failures_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register failures subcommand."""

    parser = subparsers.add_parser("failures", help="Show bounded verifier failures.")
    parser.add_argument("--check")
    parser.add_argument("--limit", type=int, default=DEFAULT_FAILURE_LIMIT)
    parser.add_argument("--budget", type=int, default=DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_log_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register log subcommand."""

    parser = subparsers.add_parser("log", help="Show bounded verifier log output.")
    parser.add_argument("check")
    parser.add_argument("--head", type=int)
    parser.add_argument("--tail", type=int)
    parser.add_argument("--lines")
    parser.add_argument("--budget", type=int, default=DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--confirm-large", action="store_true")
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

    if args.command == "failures":
        return run_failures(args)
    if args.command == "log":
        return run_log(args)
    return 2


def run_failures(args: argparse.Namespace) -> int:
    """Run failures subcommand."""

    records = failure_records(args.log_dir, check_name=args.check, limit=args.limit)
    output = (
        render_failures_json(records, log_dir=args.log_dir)
        if args.format == FORMAT_JSON
        else render_failures_text(records, log_dir=args.log_dir, budget=args.budget)
    )
    print(output)
    return 0


def run_log(args: argparse.Namespace) -> int:
    """Run log subcommand."""

    selection = select_log(
        args.log_dir,
        args.check,
        LogRequest(
            head=args.head,
            tail=args.tail,
            line_range=args.lines,
            budget=args.budget,
            confirm_large=args.confirm_large,
        ),
    )
    output = (
        render_log_json(selection) if args.format == FORMAT_JSON else render_log_text(selection)
    )
    print(output)
    return 1 if selection.refused else 0
