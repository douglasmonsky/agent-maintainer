"""Runtime event summary command."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.runtime_events.export import (
    EXPORT_FORMATS,
    JSONL_FORMAT,
    export_runtime_events,
)
from agent_maintainer.runtime_events.read import read_runtime_events
from agent_maintainer.runtime_events.summary import (
    RuntimeEventSummary,
    render_rows_text,
    render_summary_text,
    summarize_runtime_events,
)
from agent_maintainer.runtime_events.waste import (
    RuntimeEventWasteReport,
    render_waste_text,
    summarize_runtime_waste,
)

JSON_FORMAT = "json"
TEXT_FORMAT = "text"


def main(argv: list[str] | None = None) -> int:
    """Run runtime event subcommands."""
    args = parse_args([] if argv is None else argv)
    read_result = read_runtime_events(args.events_dir, file_limit=args.file_limit)
    if args.command == "export":
        export = export_runtime_events(read_result, output_format=args.format)
        print(export.text, end="")
        return 0
    summary = summarize_runtime_events(
        read_result,
        recent_limit=args.limit,
        slow_limit=args.limit,
    )
    waste_report = summarize_runtime_waste(read_result, repo_root=Path.cwd())
    print(_render(args.command, args.format, summary, waste_report))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse runtime event command arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer events")
    _add_common_options(parser, suppress_defaults=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in _subcommands().items():
        command_parser = subparsers.add_parser(command, help=help_text)
        if command == "export":
            _add_export_options(command_parser)
        else:
            _add_common_options(command_parser, suppress_defaults=True)
    return parser.parse_args(argv)


def _add_common_options(
    parser: argparse.ArgumentParser,
    *,
    suppress_defaults: bool,
) -> None:
    """Add common event parser options."""
    default_events_dir = (
        argparse.SUPPRESS
        if suppress_defaults
        else Path(
            MaintainerConfig.runtime_events_dir,
        )
    )
    default_limit = argparse.SUPPRESS if suppress_defaults else 8
    default_file_limit = argparse.SUPPRESS if suppress_defaults else None
    default_format = argparse.SUPPRESS if suppress_defaults else TEXT_FORMAT
    parser.add_argument("--events-dir", type=Path, default=default_events_dir)
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--file-limit", type=int, default=default_file_limit)
    parser.add_argument(
        "--format",
        choices=(TEXT_FORMAT, JSON_FORMAT),
        default=default_format,
    )


def _add_export_options(parser: argparse.ArgumentParser) -> None:
    """Add export-specific parser options."""
    parser.add_argument("--events-dir", type=Path, default=argparse.SUPPRESS)
    parser.add_argument("--limit", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--file-limit", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--format", choices=EXPORT_FORMATS, default=JSONL_FORMAT)


def _subcommands() -> dict[str, str]:
    """Return runtime event subcommands."""
    return {
        "summary": "Show runtime event aggregate counts.",
        "failures": "Show failing runtime events.",
        "slow-checks": "Show slow check events.",
        "recent": "Show recent runtime events.",
        "waste": "Show duplicated verification cadence waste signals.",
        "export": "Export local runtime event artifacts.",
    }


def _render(
    command: str,
    output_format: str,
    summary: RuntimeEventSummary,
    waste_report: RuntimeEventWasteReport,
) -> str:
    if output_format == JSON_FORMAT:
        return _render_json(command, summary, waste_report)
    return _render_text(command, summary, waste_report)


def _render_json(
    command: str,
    summary: RuntimeEventSummary,
    waste_report: RuntimeEventWasteReport,
) -> str:
    if command == "waste":
        return waste_report.to_json()
    return summary.to_json()


def _render_text(
    command: str,
    summary: RuntimeEventSummary,
    waste_report: RuntimeEventWasteReport,
) -> str:
    if command == "failures":
        return render_rows_text("Runtime Event Failures", summary.failures)
    if command == "slow-checks":
        return render_rows_text("Runtime Event Slow Checks", summary.slow_checks)
    if command == "recent":
        return render_rows_text("Runtime Event Recent", summary.recent)
    if command == "waste":
        return render_waste_text(waste_report)
    return render_summary_text(summary)
