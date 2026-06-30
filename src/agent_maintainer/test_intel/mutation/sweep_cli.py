"""CLI adapter for advisory mutation sweep planning and execution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel.changed import changed_source_paths
from agent_maintainer.test_intel.mutation import sweep as mutation_sweep
from agent_maintainer.test_intel.mutation import (
    sweep_execution as mutation_sweep_execution,
)
from agent_maintainer.test_intel.mutation import sweep_executor as mutation_sweep_executor
from agent_maintainer.test_intel.mutation import sweep_reporting as mutation_sweep_reporting

FORMAT_JSON = "json"
FORMAT_TEXT = "text"
FORMAT_CHOICES = (FORMAT_TEXT, FORMAT_JSON)
ACTION_STORE_TRUE = "store_true"
ACTION_STORE_FALSE = "store_false"


def add_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Add advisory mutation sweep parser."""

    sweep_parser = subparsers.add_parser(
        "mutation-sweep",
        help="Plan or execute advisory deep mutation sweep candidates.",
    )
    sweep_parser.add_argument("--changed", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--base-ref", default="HEAD")
    sweep_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--execute", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--limit", type=int, default=mutation_sweep.DEFAULT_LIMIT)
    sweep_parser.add_argument(
        "--candidate-limit",
        type=int,
        default=None,
        help="Maximum ranked candidates to execute; defaults to 1 with --execute.",
    )
    sweep_parser.add_argument(
        "--target-limit",
        type=int,
        default=mutation_sweep.DEFAULT_TARGET_LIMIT,
    )
    sweep_parser.add_argument(
        "--time-budget-minutes",
        type=int,
        default=mutation_sweep.DEFAULT_TIME_BUDGET_MINUTES,
    )
    sweep_parser.add_argument(
        "--survivor-threshold",
        type=int,
        default=mutation_sweep.DEFAULT_SURVIVOR_THRESHOLD,
    )
    sweep_parser.add_argument(
        "--continue-on-no-new-findings",
        action=ACTION_STORE_FALSE,
        dest="stop_when_no_new_findings",
        default=True,
    )
    sweep_parser.add_argument(
        "--output-dir",
        type=Path,
        default=mutation_sweep_execution.DEFAULT_OUTPUT_DIR,
    )
    sweep_parser.add_argument("--keep-worktree", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--fail-fast", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--format", choices=FORMAT_CHOICES, default=FORMAT_TEXT)


def run(args: argparse.Namespace) -> int:
    """Run advisory deep mutation sweep planning or execution."""

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
    report = mutation_sweep.build_mutation_sweep_report(
        mutation_sweep.MutationSweepRequest(
            config=config,
            repo_root=repo_root,
            base_ref=args.base_ref,
            changed_only=args.changed,
            changed_source=changed_source,
            limit=args.limit,
            target_limit=args.target_limit,
            time_budget_minutes=args.time_budget_minutes,
            survivor_threshold=args.survivor_threshold,
            stop_when_no_new_findings=args.stop_when_no_new_findings,
        ),
    )
    if args.execute:
        execution_report = mutation_sweep_executor.execute_mutation_sweep(
            report,
            mutation_sweep_execution.MutationSweepExecutionRequest(
                repo_root=repo_root,
                output_dir=args.output_dir,
                candidate_limit=candidate_limit(args.candidate_limit),
                time_budget_minutes=args.time_budget_minutes,
                survivor_threshold=args.survivor_threshold,
                keep_worktree=args.keep_worktree,
                fail_fast=args.fail_fast,
            ),
        )
        print(render_execution(execution_report, args.format))
        return 1 if execution_report.has_failures else 0
    print(render(report, args.format))
    return 0


def render(report: mutation_sweep.MutationSweepReport, output_format: str) -> str:
    """Render mutation sweep report in selected format."""

    if output_format == FORMAT_JSON:
        return mutation_sweep_reporting.render_json(report)
    return mutation_sweep_reporting.render_text(report)


def render_execution(
    report: mutation_sweep_execution.MutationSweepExecutionReport,
    output_format: str,
) -> str:
    """Render mutation sweep execution report in selected format."""

    if output_format == FORMAT_JSON:
        return mutation_sweep_reporting.render_execution_json(report)
    return mutation_sweep_reporting.render_execution_text(report)


def candidate_limit(value: int | None) -> int:
    """Return execution candidate limit."""

    if value is None:
        return mutation_sweep_execution.DEFAULT_EXECUTION_CANDIDATE_LIMIT
    return value
