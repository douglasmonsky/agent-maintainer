"""CLI adapter for advisory TypeScript LCOV changed-line coverage."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from agent_maintainer.test_intel import (
    typescript_coverage,
    typescript_coverage_reporting,
)

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
FORMAT_CHOICES = (FORMAT_TEXT, FORMAT_JSON)


def add_parser(parser_factory: Callable[..., argparse.ArgumentParser]) -> None:
    """Add the advisory TypeScript coverage subcommand."""

    parser = parser_factory(
        "typescript-coverage",
        help="Report advisory LCOV coverage for changed TypeScript lines.",
    )
    parser.add_argument(
        "--lcov",
        type=Path,
        default=typescript_coverage.DEFAULT_LCOV_PATH,
        help="Path to an existing LCOV artifact.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path("."),
        help="Repository-relative root for relative LCOV SF paths.",
    )
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--format", choices=FORMAT_CHOICES, default=FORMAT_TEXT)


def run(args: argparse.Namespace) -> int:
    """Build and render one advisory TypeScript coverage report."""

    try:
        report = typescript_coverage.build_report(
            typescript_coverage.TypeScriptCoverageRequest(
                repo_root=Path.cwd(),
                lcov_path=args.lcov,
                source_root=args.source_root,
                base_ref=args.base_ref,
                staged=args.staged,
            )
        )
    except typescript_coverage.TypeScriptCoverageError as exc:
        print(f"TypeScript coverage unavailable: {exc}", file=sys.stderr)
        return 1
    print(render(report, args.format))
    return 0


def render(
    report: typescript_coverage.TypeScriptCoverageReport,
    output_format: str,
) -> str:
    """Render a report in the selected format."""

    if output_format == FORMAT_JSON:
        return typescript_coverage_reporting.render_json(report)
    return typescript_coverage_reporting.render_text(report)
