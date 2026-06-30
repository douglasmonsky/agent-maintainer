"""Command-line interface for test intelligence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel import (
    crosshair_candidates,
    crosshair_reporting,
    hypothesis_candidates,
    hypothesis_reporting,
    mutation_reporting,
    mutation_results,
    mutation_sweep_cli,
    mutation_targets,
)
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
    mutation_parser = subparsers.add_parser(
        "mutation-targets",
        help="Suggest advisory mutation testing targets.",
    )
    mutation_parser.add_argument("--changed", action=ACTION_STORE_TRUE)
    mutation_parser.add_argument("--ratchet", action=ACTION_STORE_TRUE)
    mutation_parser.add_argument("--base-ref", default="HEAD")
    mutation_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    mutation_parser.add_argument(
        "--limit",
        type=int,
        default=mutation_targets.DEFAULT_LIMIT,
    )
    mutation_parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )
    mutation_results_parser = subparsers.add_parser(
        "mutation-results",
        help="Summarize exported Mutmut result statistics.",
    )
    mutation_results_parser.add_argument(
        "--path",
        default="mutants/mutmut-cicd-stats.json",
        help="Path to mutmut-cicd-stats.json.",
    )
    mutation_results_parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )
    mutation_sweep_cli.add_parser(subparsers)
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
        "hypothesis-candidates": run_hypothesis_candidates,
        "mutation-targets": run_mutation_targets,
        "mutation-results": run_mutation_results,
        "mutation-sweep": mutation_sweep_cli.run,
        "crosshair-candidates": run_crosshair_candidates,
    }
    return handlers[args.command](args)


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
    coverage = coverage_for_changed_sources(
        repo_root,
        changed_source,
        base_ref=base_ref,
        staged=staged,
    )
    return TestIntelReport(
        changed_source=changed_source,
        likely_tests=matches,
        coverage=coverage,
        suggested_actions=suggested_actions(matches),
    )


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


def run_mutation_targets(args: argparse.Namespace) -> int:
    """Run advisory mutation target report."""

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
    report = mutation_targets.build_mutation_target_report(
        mutation_targets.MutationTargetRequest(
            config=config,
            repo_root=repo_root,
            changed_only=args.changed,
            ratchet_enabled=args.ratchet,
            base_ref=args.base_ref,
            changed_source=changed_source,
            limit=args.limit,
        )
    )
    print(render_mutation_report(report, args.format))
    return 0


def render_mutation_report(
    report: mutation_targets.MutationTargetReport,
    output_format: str,
) -> str:
    """Render mutation target report in selected format."""

    if output_format == FORMAT_JSON:
        return mutation_reporting.render_json(report)
    return mutation_reporting.render_text(report)


def run_mutation_results(args: argparse.Namespace) -> int:
    """Run mutation result stats summary."""

    try:
        source = mutation_results.read_result_source(Path(args.path))
    except (OSError, ValueError) as exc:
        print(f"mutmut stats unavailable: {exc}", file=sys.stderr)
        return 1
    print(render_mutation_results(source, args.format))
    return 0


def render_mutation_results(
    source: mutation_results.MutationResultSource,
    output_format: str,
) -> str:
    """Render mutation result stats in selected format."""

    if output_format == FORMAT_JSON:
        return mutation_results.render_json(source.stats, source=source)
    return mutation_results.render_text(source.stats, source=source)


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


def render_report(report: TestIntelReport, output_format: str) -> str:
    """Render report in selected output format."""

    if output_format == FORMAT_JSON:
        return render_json(report)
    return render_text(report)
