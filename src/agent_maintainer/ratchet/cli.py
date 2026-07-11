"""Command-line interface for ratchet baselines."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from agent_maintainer.core.config import load_config
from agent_maintainer.ratchet import baseline, models
from agent_maintainer.ratchet.findings import DEFAULT_CHECKS
from agent_maintainer.ratchet.ranking import changed_paths, ranked_targets
from agent_maintainer.ratchet.reporting import render_targets_json, render_targets_text
from agent_maintainer.ratchet.status import status_report

ParserFactory = Callable[[str], argparse.ArgumentParser]


def main(argv: list[str] | None = None) -> int:
    """Run ratchet command."""

    args = parse_args(argv or sys.argv[1:])
    if args.command == "baseline":
        return baseline_command(args)
    if args.command == "status":
        return status_command(args)
    if args.command == "next":
        return next_command(args)
    if args.command == "explain":
        return explain_command()
    return 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse ratchet command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer ratchet")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_status_parser(subparsers.add_parser)
    add_next_parser(subparsers.add_parser)
    add_explain_parser(subparsers.add_parser)
    add_baseline_parser(subparsers.add_parser)
    return parser.parse_args(argv)


def add_status_parser(parser_factory: ParserFactory) -> None:
    """Add status subcommand parser."""

    status_parser = parser_factory("status")
    status_parser.add_argument("--baseline")
    status_parser.add_argument("--base-ref", default="HEAD")
    status_parser.add_argument("--format", choices=("text", "json"), default="text")


def add_next_parser(parser_factory: ParserFactory) -> None:
    """Add next-target subcommand parser."""

    next_parser = parser_factory("next")
    next_parser.add_argument("--baseline")
    next_parser.add_argument("--base-ref", default="HEAD")
    next_parser.add_argument("--limit", type=int)
    next_parser.add_argument("--format", choices=("text", "json"), default="text")


def add_explain_parser(parser_factory: ParserFactory) -> None:
    """Add explain subcommand parser."""

    parser_factory("explain")


def add_baseline_parser(
    parser_factory: ParserFactory,
) -> None:
    """Add baseline subcommands."""

    baseline_parser = parser_factory("baseline")
    baseline_subparsers = baseline_parser.add_subparsers(
        dest="baseline_command",
        required=True,
    )
    add_baseline_write_parser(baseline_subparsers.add_parser, "create", force_default=False)
    add_baseline_write_parser(baseline_subparsers.add_parser, "refresh", force_default=True)


def add_baseline_write_parser(
    parser_factory: ParserFactory,
    name: str,
    *,
    force_default: bool,
) -> None:
    """Add baseline write command parser."""

    parser = parser_factory(name)
    parser.add_argument("--baseline")
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--notes", default="")
    parser.add_argument("--check", action="append", choices=DEFAULT_CHECKS)
    parser.set_defaults(force=force_default)
    parser.add_argument("--force", action="store_true", default=force_default)


def baseline_command(args: argparse.Namespace) -> int:
    """Create or refresh a ratchet baseline."""

    path = selected_baseline_path(args)
    current_baseline = baseline.create_baseline(
        base_ref=args.base_ref,
        notes=args.notes,
        checks=selected_checks(args),
    )
    try:
        baseline.write_baseline(path, current_baseline, force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"ratchet baseline written: {path}")
    print(f"findings: {len(current_baseline.findings)}")
    return 0


def status_command(args: argparse.Namespace) -> int:
    """Print ratchet status."""

    path = selected_baseline_path(args)
    if not path.exists():
        print(f"ratchet baseline not found: {path}", file=sys.stderr)
        return 1
    report = status_report(baseline.read_baseline(path), base_ref=args.base_ref)
    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0
    print_status(path, report)
    return 0


def next_command(args: argparse.Namespace) -> int:
    """Print ranked ratchet targets."""

    path = selected_baseline_path(args)
    if not path.exists():
        print(f"ratchet baseline not found: {path}", file=sys.stderr)
        return 1
    limit = selected_limit(args)
    report = status_report(baseline.read_baseline(path), base_ref=args.base_ref)
    targets = ranked_targets(
        report,
        changed_path_set=changed_paths(args.base_ref),
        limit=limit,
    )
    if args.format == "json":
        print(render_targets_json(targets))
        return 0
    print(render_targets_text(targets))
    return 0


def explain_command() -> int:
    """Explain supported ratchet checks."""

    checks = ", ".join(DEFAULT_CHECKS)
    print("Ratchet baselines compare current findings to a saved JSON baseline.")
    print(f"Supported checks: {checks}")
    print("Default baseline: .agent-maintainer/ratchet-baseline.json")
    return 0


def selected_baseline_path(args: argparse.Namespace) -> Path:
    """Return CLI or configured baseline path."""

    if args.baseline:
        return Path(args.baseline)
    return baseline.default_baseline_path()


def selected_checks(args: argparse.Namespace) -> tuple[str, ...]:
    """Return checks selected for baseline generation."""

    return tuple(args.check) if args.check else DEFAULT_CHECKS


def selected_limit(args: argparse.Namespace) -> int:
    """Return CLI or configured target limit."""

    if args.limit is not None:
        return args.limit
    return load_config().ratchet_target_limit


def print_status(path: Path, report: models.RatchetStatusReport) -> None:
    """Print compact text status report."""

    counts = report.counts()
    print(f"ratchet baseline: {path}")
    print(
        "status: "
        f"new={counts['new']} "
        f"worsened={counts['worsened']} "
        f"unchanged={counts['unchanged']} "
        f"improved={counts['improved']} "
        f"resolved={counts['resolved']}",
    )
    if report.stale_reasons:
        print("stale:")
        for reason in report.stale_reasons:
            print(f"- {reason}")


if __name__ == "__main__":
    sys.exit(main())
