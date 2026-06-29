"""Command-line interface for non-mutating repair plans."""

from __future__ import annotations

import argparse
import sys

from agent_maintainer.core.config import load_config
from agent_maintainer.repair_plan.models import RepairPlan, RepairPlanRequest
from agent_maintainer.repair_plan.planning import build_repair_plan
from agent_maintainer.repair_plan.rendering import render_json, render_markdown

FORMAT_JSON = "json"
FORMAT_MARKDOWN = "markdown"
DEFAULT_BUDGET = 12_000


def main(argv: list[str] | None = None) -> int:
    """Run repair-plan command."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_config()
    request = RepairPlanRequest(
        ratchet=args.ratchet,
        check=args.check,
        target=args.target,
        pack_budget=config.context_pack_budget_chars,
    )
    plan = build_repair_plan(request)
    output = render_selected_format(plan, output_format=args.format, budget=args.budget)
    print(output, end="" if output.endswith("\n") else "\n")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse repair-plan command arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer repair-plan")
    focus = parser.add_mutually_exclusive_group()
    focus.add_argument("--ratchet", action="store_true", help="Plan next ratchet repair.")
    focus.add_argument("--check", help="Plan repair for one verifier check.")
    focus.add_argument("--target", help="Plan repair for one path.")
    parser.add_argument(
        "--format",
        choices=(FORMAT_MARKDOWN, FORMAT_JSON),
        default=FORMAT_MARKDOWN,
    )
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    return parser.parse_args(argv)


def render_selected_format(plan: RepairPlan, *, output_format: str, budget: int) -> str:
    """Render selected repair-plan output format."""
    if output_format == FORMAT_JSON:
        return render_json(plan, budget=budget)
    return render_markdown(plan, budget=budget)


if __name__ == "__main__":
    sys.exit(main())
