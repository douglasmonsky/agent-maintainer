"""CLI for local scoring dataset examples."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.scoring.dataset import (
    DEFAULT_EXAMPLES_FILE,
    JSONL_FORMAT,
    ScoringExample,
    add_example,
    examples_json,
    examples_jsonl,
    list_all_examples,
)


def main(argv: list[str] | None = None) -> int:
    """Run scoring subcommands."""
    args = parse_args([] if argv is None else argv)
    if args.command == "examples":
        return run_examples(args)
    raise RuntimeError(f"unsupported scoring command: {args.command}")


def run_examples(args: argparse.Namespace) -> int:
    """Run scoring examples subcommands."""
    if args.examples_command == "add":
        example = ScoringExample(
            example_id=args.example_id,
            task_summary=args.task_summary,
            labels=tuple(args.label),
            expected_route=args.expected_route,
            evidence=tuple(args.evidence or ()),
            notes=args.notes,
        )
        print(add_example(example, args.examples_file))
        return 0
    if args.examples_command == "export":
        print(examples_jsonl(args.examples_file), end="")
        return 0
    if args.format == "json":
        print(examples_json(args.examples_file))
        return 0
    print_examples(args.examples_file)
    return 0


def print_examples(examples_file: Path) -> None:
    """Print scoring examples as compact text."""
    for example in list_all_examples(examples_file):
        labels = ", ".join(example.labels)
        print(f"{example.example_id}: {example.expected_route} [{labels}]")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse scoring command arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer scoring")
    subparsers = parser.add_subparsers(dest="command", required=True)
    examples = subparsers.add_parser("examples", help="Inspect labeled examples.")
    examples.add_argument("--examples-file", type=Path, default=DEFAULT_EXAMPLES_FILE)
    example_subparsers = examples.add_subparsers(dest="examples_command", required=True)
    add_parser = example_subparsers.add_parser("add", help="Append one local example.")
    add_parser.add_argument("--id", dest="example_id", required=True)
    add_parser.add_argument("--task-summary", required=True)
    add_parser.add_argument("--label", action="append", required=True)
    add_parser.add_argument("--expected-route", required=True)
    add_parser.add_argument("--evidence", action="append")
    add_parser.add_argument("--notes", default="")
    export_parser = example_subparsers.add_parser("export", help="Export examples.")
    export_parser.add_argument("--format", choices=(JSONL_FORMAT,), default=JSONL_FORMAT)
    list_parser = example_subparsers.add_parser("list", help="List bundled examples.")
    list_parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args(argv)
