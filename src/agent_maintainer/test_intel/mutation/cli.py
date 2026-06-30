"""CLI adapter for mutation test-intelligence commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel.changed import changed_source_paths
from agent_maintainer.test_intel.mutation import results, results_reporting, sweep_cli, targets

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
FORMAT_CHOICES = (FORMAT_TEXT, FORMAT_JSON)
ACTION_STORE_TRUE = "store_true"


def add_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add mutation intelligence subcommands."""
    add_targets_parser(subparsers)
    add_results_parser(subparsers)
    sweep_cli.add_parser(subparsers)


def add_targets_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add advisory mutation-target parser."""
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
        default=targets.DEFAULT_LIMIT,
    )
    mutation_parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )


def add_results_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add mutation-results parser."""
    parser = subparsers.add_parser(
        "mutation-results",
        help="Summarize exported Mutmut result statistics.",
    )
    parser.add_argument(
        "--path",
        default="mutants/mutmut-cicd-stats.json",
        help="Path to mutmut-cicd-stats.json.",
    )
    parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default=FORMAT_TEXT,
    )


def run_targets(args: argparse.Namespace) -> int:
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
    report = targets.build_mutation_target_report(
        targets.MutationTargetRequest(
            config=config,
            repo_root=repo_root,
            changed_only=args.changed,
            changed_source=changed_source,
            ratchet_enabled=args.ratchet,
            base_ref=args.base_ref,
            limit=args.limit,
        ),
    )
    print(render_target_report(report, args.format))
    return 0


def render_target_report(
    report: targets.MutationTargetReport,
    output_format: str,
) -> str:
    """Render mutation target report in selected format."""
    if output_format == FORMAT_JSON:
        return results_reporting.render_json(report)
    return results_reporting.render_text(report)


def run_results(args: argparse.Namespace) -> int:
    """Run mutation result stats summary."""
    try:
        source = results.read_result_source(Path(args.path))
    except (OSError, ValueError) as exc:
        print(f"mutmut stats unavailable: {exc}", file=sys.stderr)
        return 1
    print(render_results(source, args.format))
    return 0


def render_results(
    source: results.MutationResultSource,
    output_format: str,
) -> str:
    """Render mutation result stats in selected format."""
    if output_format == FORMAT_JSON:
        return results.render_json(source.stats, source=source)
    return results.render_text(source.stats, source=source)


def run_sweep(args: argparse.Namespace) -> int:
    """Run advisory mutation sweep planning or execution."""
    return sweep_cli.run(args)
