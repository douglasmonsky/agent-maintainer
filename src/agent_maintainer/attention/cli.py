"""Attention ledger CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.attention import builder, rendering

JSON_FORMAT = "json"
TEXT_FORMAT = "text"


def main(argv: list[str] | None = None) -> int:  # noqa: C901, PLR0911
    """Run attention CLI."""
    args = parse_args(argv)
    target = args.target.resolve()
    output = target / args.output
    if args.command == "update":
        try:
            ledger = _build_ledger(args, target)
        except ValueError as exc:
            print(f"attention argument error: {exc}", file=sys.stderr)
            return 2
        builder.write_attention_ledger(ledger, output)
        if args.format == JSON_FORMAT:
            print(rendering.render_ledger_json(ledger))
        else:
            print(f"Result: PASS\nAttention ledger: {output}\nFiles: {ledger.file_count}")
        return 0
    try:
        ledger = _load_or_build(args, target=target, output=output)
    except ValueError as exc:
        print(f"attention argument error: {exc}", file=sys.stderr)
        return 2
    if args.command == "top":
        if args.format == JSON_FORMAT:
            print(rendering.render_top_json(ledger, limit=args.limit))
        else:
            print(rendering.render_top_text(ledger, limit=args.limit))
        return 0
    if args.command == "explain":
        score = next((item for item in ledger.files if item.path == args.path), None)
        print(rendering.render_explain_text(score, path=args.path))
        return 0
    if args.command == "changed":
        print(rendering.render_changed_text(ledger, limit=args.limit))
        return 0
    return 2


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse attention CLI arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer attention")
    _add_common_options(parser, suppress_defaults=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update", help="Write attention ledger.")
    _add_common_options(update_parser, suppress_defaults=True)
    update_parser.add_argument("--format", choices=(TEXT_FORMAT, JSON_FORMAT), default=TEXT_FORMAT)

    top_parser = subparsers.add_parser("top", help="Show top scored files.")
    _add_common_options(top_parser, suppress_defaults=True)
    top_parser.add_argument("--limit", type=int, default=10)
    top_parser.add_argument("--format", choices=(TEXT_FORMAT, JSON_FORMAT), default=TEXT_FORMAT)

    explain_parser = subparsers.add_parser("explain", help="Explain one file score.")
    _add_common_options(explain_parser, suppress_defaults=True)
    explain_parser.add_argument("path")

    changed_parser = subparsers.add_parser("changed", help="Show changed scored files.")
    _add_common_options(changed_parser, suppress_defaults=True)
    changed_parser.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    if argv is not None:
        args.priority_path = _priority_paths(argv)
    return args


def _priority_paths(argv: list[str]) -> list[str]:
    """Return priority path values in their original command-line order."""

    return [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "--priority-path"]


def _add_common_options(parser: argparse.ArgumentParser, *, suppress_defaults: bool) -> None:
    """Add common attention options."""
    target_default = argparse.SUPPRESS if suppress_defaults else Path.cwd()
    output_default = argparse.SUPPRESS if suppress_defaults else builder.DEFAULT_OUTPUT_PATH
    log_default = argparse.SUPPRESS if suppress_defaults else Path(".verify-logs")
    events_default = argparse.SUPPRESS if suppress_defaults else Path(".verify-logs/events")
    priority_default = argparse.SUPPRESS if suppress_defaults else []
    parser.add_argument("--target", type=Path, default=target_default, help="Repository root.")
    parser.add_argument(
        "--output",
        type=Path,
        default=output_default,
        help="Attention ledger JSON path relative to target.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=log_default,
        help="Verifier log directory relative to target.",
    )
    parser.add_argument(
        "--events-dir",
        type=Path,
        default=events_default,
        help="Runtime events directory relative to target.",
    )
    parser.add_argument(
        "--priority-path",
        action="append",
        default=priority_default,
        help="Repository-relative path that must survive background sampling; repeatable.",
    )


def _load_or_build(args: argparse.Namespace, *, target: Path, output: Path):
    """Load existing ledger, or build in memory when absent."""
    existing = builder.read_attention_ledger(output, workspace_root=target)
    if existing is not None:
        return existing
    return _build_ledger(args, target)


def _build_ledger(args: argparse.Namespace, target: Path):
    """Build one attention ledger from shared CLI options."""

    return builder.build_attention_ledger(
        target,
        log_dir=args.log_dir,
        events_dir=args.events_dir,
        priority_paths=tuple(args.priority_path or ()),
    )
