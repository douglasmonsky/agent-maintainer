"""Command-line interface for test intelligence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel.changed import changed_source_paths
from agent_maintainer.test_intel.coverage import coverage_for_changed_sources
from agent_maintainer.test_intel.mapping import likely_tests_for_changes
from agent_maintainer.test_intel.models import TestIntelReport
from agent_maintainer.test_intel.reporting import (
    render_json,
    render_text,
    suggested_actions,
)

FORMAT_JSON = "json"
FORMAT_TEXT = "text"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse test-intelligence command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer test-intel")
    subparsers = parser.add_subparsers(dest="command", required=True)
    changed_parser = subparsers.add_parser(
        "changed",
        help="Show likely tests for changed source files.",
    )
    changed_parser.add_argument("--base-ref", default="HEAD")
    changed_parser.add_argument("--staged", action="store_true")
    changed_parser.add_argument(
        "--format",
        choices=(FORMAT_TEXT, FORMAT_JSON),
        default=FORMAT_TEXT,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Run test-intelligence command."""

    args = parse_args(argv)
    if args.command == "changed":
        return run_changed(args)
    return 2


def run_changed(args: argparse.Namespace) -> int:
    """Run changed-source test-intelligence report."""

    try:
        report = build_changed_report(
            base_ref=args.base_ref,
            staged=args.staged,
            repo_root=Path.cwd(),
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(render_report(report, args.format))
    return 0


def build_changed_report(*, base_ref: str, staged: bool, repo_root: Path) -> TestIntelReport:
    """Build changed-source test-intelligence report."""

    config = loader.load_config()
    changed_source = changed_source_paths(config, base_ref=base_ref, staged=staged)
    matches = likely_tests_for_changes(changed_source, config, repo_root)
    coverage = coverage_for_changed_sources(repo_root, changed_source)
    return TestIntelReport(
        changed_source=changed_source,
        likely_tests=matches,
        coverage=coverage,
        suggested_actions=suggested_actions(matches),
    )


def render_report(report: TestIntelReport, output_format: str) -> str:
    """Render report in selected output format."""

    if output_format == FORMAT_JSON:
        return render_json(report)
    return render_text(report)
