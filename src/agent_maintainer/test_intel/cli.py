"""Command-line interface for test intelligence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel import (
    changed_report,
    crosshair_candidates,
    crosshair_reporting,
    hypothesis_candidates,
    hypothesis_reporting,
)
from agent_maintainer.test_intel import (
    run_changed as run_changed_tests,
)
from agent_maintainer.test_intel.changed import changed_source_paths
from agent_maintainer.test_intel.mutation import cli as mutation_cli

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
FORMAT_CHOICES = (FORMAT_TEXT, FORMAT_JSON)
ACTION_STORE_TRUE = "store_true"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse test-intelligence command arguments."""

    parser = argparse.ArgumentParser(prog="python -m agent_maintainer test-intel")
    subparsers = parser.add_subparsers(dest="command", required=True)
    changed_parser = subparsers.add_parser(
        "changed",
        help="Show likely tests for changed source files.",
    )
    changed_parser.add_argument("--base-ref", default="HEAD")
    changed_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    changed_parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )
    run_changed_parser = subparsers.add_parser(
        "run-changed",
        help="Run tests affected by changed Python source and test files.",
    )
    run_changed_parser.add_argument("--base-ref", default="HEAD")
    run_changed_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    hypothesis_parser = subparsers.add_parser(
        "hypothesis-candidates",
        help="Suggest advisory Hypothesis property-test candidates.",
    )
    hypothesis_parser.add_argument("--changed", action=ACTION_STORE_TRUE)
    hypothesis_parser.add_argument("--base-ref", default="HEAD")
    hypothesis_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    hypothesis_parser.add_argument(
        "--limit",
        type=int,
        default=hypothesis_candidates.DEFAULT_LIMIT,
    )
    hypothesis_parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )
    mutation_cli.add_parsers(subparsers.add_parser)
    crosshair_parser = subparsers.add_parser(
        "crosshair-candidates",
        help="Suggest advisory CrossHair contract-analysis candidates.",
    )
    crosshair_parser.add_argument("--changed", action=ACTION_STORE_TRUE)
    crosshair_parser.add_argument("--base-ref", default="HEAD")
    crosshair_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    crosshair_parser.add_argument(
        "--limit",
        type=int,
        default=crosshair_candidates.DEFAULT_LIMIT,
    )
    crosshair_parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Run test-intelligence command."""

    args = parse_args(argv)
    handlers = {
        "changed": run_changed,
        "run-changed": run_changed_tests_from_cli,
        "hypothesis-candidates": run_hypothesis_candidates,
        "mutation-targets": mutation_cli.run_targets,
        "mutation-results": mutation_cli.run_results,
        "mutation-sweep": mutation_cli.run_sweep,
        "crosshair-candidates": run_crosshair_candidates,
    }
    return handlers[args.command](args)


def run_changed(args: argparse.Namespace) -> int:
    """Run changed-source test-intelligence report."""

    try:
        report = changed_report.build(
            base_ref=args.base_ref,
            staged=args.staged,
            repo_root=Path.cwd(),
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(changed_report.render(report, args.format))
    return 0


def run_changed_tests_from_cli(args: argparse.Namespace) -> int:
    """Select and execute affected tests for a commit-time diff."""

    repo_root = Path.cwd()
    config = loader.load_config()
    try:
        paths = run_changed_tests.selected_test_paths(
            config,
            base_ref=args.base_ref,
            staged=args.staged,
            repo_root=repo_root,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return run_changed_tests.run_selected_tests(paths, repo_root=repo_root)


def run_hypothesis_candidates(args: argparse.Namespace) -> int:
    """Run advisory Hypothesis candidate report."""

    repo_root = Path.cwd()
    config = loader.load_config()
    try:
        changed_source = (
            changed_source_paths(config, base_ref=args.base_ref, staged=args.staged)
            if args.changed
            else ()
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    report = hypothesis_candidates.build_hypothesis_candidate_report(
        config,
        repo_root,
        changed_only=args.changed,
        changed_source=changed_source,
        limit=args.limit,
    )
    print(render_hypothesis_report(report, args.format))
    return 0


def render_hypothesis_report(
    report: hypothesis_candidates.HypothesisCandidateReport,
    output_format: str,
) -> str:
    """Render Hypothesis candidate report in selected format."""

    if output_format == FORMAT_JSON:
        return hypothesis_reporting.render_json(report)
    return hypothesis_reporting.render_text(report)


def run_crosshair_candidates(args: argparse.Namespace) -> int:
    """Run advisory CrossHair candidate report."""

    repo_root = Path.cwd()
    config = loader.load_config()
    try:
        changed_source = (
            changed_source_paths(config, base_ref=args.base_ref, staged=args.staged)
            if args.changed
            else ()
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    report = crosshair_candidates.build_crosshair_candidate_report(
        crosshair_candidates.CrosshairCandidateRequest(
            config=config,
            repo_root=repo_root,
            changed_only=args.changed,
            changed_source=changed_source,
            limit=args.limit,
        )
    )
    print(render_crosshair_report(report, args.format))
    return 0


def render_crosshair_report(
    report: crosshair_candidates.CrosshairCandidateReport,
    output_format: str,
) -> str:
    """Render CrossHair candidate report in selected format."""

    if output_format == FORMAT_JSON:
        return crosshair_reporting.render_json(report)
    return crosshair_reporting.render_text(report)
