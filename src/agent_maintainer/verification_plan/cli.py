"""Command line for diff-aware verification planning."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.config.issues import ConfigValidationError
from agent_maintainer.verification_plan.planner import (
    DEFAULT_POLICY_PATH,
    build_verification_plan,
)
from agent_maintainer.verification_plan.policy import PolicyError
from agent_maintainer.verification_plan.reporting import render_json, render_text


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse public verification-plan options."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer verify-plan")
    parser.add_argument("--target", type=Path, default=Path("."))
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Render one plan and return exact success, enforcement, or error status."""
    args = parse_args(argv)
    try:
        report = build_verification_plan(
            args.target,
            base_ref=args.base_ref,
            staged=args.staged,
            policy_path=args.policy,
        )
    except (ConfigValidationError, PolicyError, RuntimeError) as exc:
        print(f"FAIL verify-plan: {exc}", file=sys.stderr)
        return 2
    output = render_json(report) if args.json else render_text(report)
    print(output, end="")
    return 1 if args.enforce and report.blocking_findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
