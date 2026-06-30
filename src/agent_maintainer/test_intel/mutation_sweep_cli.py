"""CLI adapter for advisory mutation sweep planning."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config import loader
from agent_maintainer.test_intel import mutation_sweep, mutation_sweep_reporting
from agent_maintainer.test_intel.changed import changed_source_paths

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
        help="Plan advisory deep mutation sweep candidates.",
    )
    sweep_parser.add_argument("--changed", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--base-ref", default="HEAD")
    sweep_parser.add_argument("--staged", action=ACTION_STORE_TRUE)
    sweep_parser.add_argument("--limit", type=int, default=mutation_sweep.DEFAULT_LIMIT)
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
    sweep_parser.add_argument("--format", choices=FORMAT_CHOICES, default=FORMAT_TEXT)


def run(args: argparse.Namespace) -> int:
    """Run advisory deep mutation sweep planning."""

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
        )
    )
    print(render(report, args.format))
    return 0


def render(report: mutation_sweep.MutationSweepReport, output_format: str) -> str:
    """Render mutation sweep report in selected format."""

    if output_format == FORMAT_JSON:
        return mutation_sweep_reporting.render_json(report)
    return mutation_sweep_reporting.render_text(report)
