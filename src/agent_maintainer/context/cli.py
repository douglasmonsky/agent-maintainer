"""Command-line interface for safe context expansion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.context import (
    compression_backends,
    headroom_backend,
    pack_rendering,
    packs,
)
from agent_maintainer.context.diff import render_diff
from agent_maintainer.context.diff_git import DEFAULT_DIFF_PATH_LIMIT, DiffRequest
from agent_maintainer.context.estimate import (
    EstimateRequest,
    estimate_context,
    render_estimate_json,
    render_estimate_text,
)
from agent_maintainer.context.failures import (
    DEFAULT_CONTEXT_BUDGET,
    DEFAULT_FAILURE_LIMIT,
    failure_records,
    render_failures_json,
    render_failures_text,
)
from agent_maintainer.context.files import (
    DEFAULT_FILE_CONTEXT_LINES,
    FileRequest,
    render_file_json,
    render_file_text,
    select_file_context,
)
from agent_maintainer.context.logs import LogRequest, render_log_json, render_log_text, select_log
from agent_maintainer.core.config import load_config

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
STORE_TRUE = "store_true"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse context command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer context")
    parser.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_diff_parser(subparsers)
    add_estimate_parser(subparsers)
    add_file_parser(subparsers)
    add_failures_parser(subparsers)
    add_log_parser(subparsers)
    add_pack_parser(subparsers)
    return parser.parse_args(argv)


def add_diff_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register diff subcommand."""

    parser = subparsers.add_parser("diff", help="Show bounded Git diff context.")
    parser.add_argument("--summary", action=STORE_TRUE)
    parser.add_argument("--name-only", action=STORE_TRUE)
    parser.add_argument("--path")
    parser.add_argument("--hunks", type=int)
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--staged", action=STORE_TRUE)
    parser.add_argument("--limit", type=int, default=DEFAULT_DIFF_PATH_LIMIT)
    parser.add_argument("--budget", type=int, default=DEFAULT_CONTEXT_BUDGET)


def add_estimate_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register estimate subcommand."""

    parser = subparsers.add_parser("estimate", help="Estimate context expansion size.")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--log")
    parser.add_argument("--diff", action=STORE_TRUE)
    parser.add_argument("--summary", action=STORE_TRUE)
    parser.add_argument("--head", type=int)
    parser.add_argument("--tail", type=int)
    parser.add_argument("--lines")
    parser.add_argument("--budget", type=int, default=DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_file_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register file subcommand."""

    parser = subparsers.add_parser("file", help="Show safe bounded file context.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--outline", action=STORE_TRUE)
    parser.add_argument("--symbols", action=STORE_TRUE)
    parser.add_argument("--symbol")
    parser.add_argument("--lines")
    parser.add_argument("--around", type=int)
    parser.add_argument("--context", type=int, default=DEFAULT_FILE_CONTEXT_LINES)
    parser.add_argument("--budget", type=int, default=DEFAULT_CONTEXT_BUDGET)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


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
    parser.add_argument("--confirm-large", action=STORE_TRUE)
    parser.add_argument("--format", choices=(FORMAT_TEXT, FORMAT_JSON), default=FORMAT_TEXT)


def add_pack_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register context pack subcommand."""

    parser = subparsers.add_parser("pack", help="Write bounded repair context pack.")
    parser.add_argument("--budget", type=int)
    parser.add_argument("--check")
    parser.add_argument("--file", action="append", type=Path, default=[])
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument(
        "--compress",
        choices=(
            compression_backends.BACKEND_NONE,
            compression_backends.BACKEND_TRUNCATE,
            compression_backends.BACKEND_EXTRACTIVE,
            headroom_backend.BACKEND_HEADROOM,
        ),
    )
    parser.add_argument("--require-compression", action=STORE_TRUE)
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
        "log": run_log,
        "pack": run_pack,
    }.get(args.command)
    if runner is not None:
        return runner(args)
    return 2


def run_estimate(args: argparse.Namespace) -> int:
    """Run estimate subcommand."""

    estimate = estimate_context(
        EstimateRequest(
            log_dir=args.log_dir,
            file_path=args.file,
            log_check=args.log,
            log_request=LogRequest(head=args.head, tail=args.tail, line_range=args.lines),
            diff=args.diff,
            diff_summary=args.summary,
            budget=args.budget,
        ),
    )
    output = (
        render_estimate_json(estimate)
        if args.format == FORMAT_JSON
        else render_estimate_text(estimate)
    )
    print(output)
    return 0


def run_diff(args: argparse.Namespace) -> int:
    """Run diff subcommand."""

    result = render_diff(
        DiffRequest(
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

    context = select_file_context(
        FileRequest(
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
    output = render_file_json(context) if args.format == FORMAT_JSON else render_file_text(context)
    print(output)
    return 1 if context.refused else 0


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


def run_pack(args: argparse.Namespace) -> int:
    """Run context pack subcommand."""

    config = load_config()
    budget = args.budget if isinstance(args.budget, int) else config.context_pack_budget_chars
    try:
        pack = packs.write_context_pack(
            packs.ContextPackRequest(
                log_dir=args.log_dir,
                budget=budget,
                check=args.check,
                files=tuple(args.file),
                base_ref=args.base_ref,
                baseline_path=Path(config.ratchet_baseline_path),
                failure_limit=config.context_max_failure_items,
                target_limit=config.ratchet_target_limit,
                compression_backend=compression_backend(args, config),
                compression_target_chars=compression_target_chars(budget, config),
                compression_required=(
                    args.require_compression
                    or getattr(config, "context_compression_require_backend", False)
                ),
            )
        )
    except (
        headroom_backend.CompressionBackendError,
        headroom_backend.CompressionBackendUnavailable,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    output = (
        pack_rendering.render_pack_json(pack.payload)
        if args.format == FORMAT_JSON
        else pack.markdown
    )
    print(output.rstrip())
    for warning in pack.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    return 0


def compression_backend(args: argparse.Namespace, config: object) -> str:
    """Return requested compression backend for context packs."""

    if args.compress:
        return args.compress
    if getattr(config, "context_compression_enabled", False):
        return str(getattr(config, "context_compression_backend", ""))
    return ""


def compression_target_chars(budget: int, config: object) -> int:
    """Return target character count for compressed supporting items."""

    ratio = getattr(config, "context_compression_target_ratio", 0.5)
    return max(1, int(budget * ratio))
