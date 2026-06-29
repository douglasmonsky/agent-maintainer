"""Command-line interface for static report generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.report.html import generate_html_report


def main(argv: list[str] | None = None) -> int:
    """Run report subcommands."""
    args = parse_args([] if argv is None else argv)
    if args.command == "html":
        output = generate_html_report(args.log_dir, args.output)
        print(output)
        return 0
    return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse report command arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    html_parser = subparsers.add_parser("html", help="Generate static HTML report.")
    html_parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path(".verify-logs"),
        help="Verifier artifact directory.",
    )
    html_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML path; defaults to .verify-logs/report/index.html.",
    )
    return parser.parse_args(argv)
