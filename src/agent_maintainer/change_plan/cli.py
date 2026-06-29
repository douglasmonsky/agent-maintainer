"""Command-line interface for cohesive change plans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.change_plan import git_scope, parser, templates, validation
from agent_maintainer.change_plan.models import ACTIVE_STATUS, PLAN_DIR, PLAN_SUFFIX, ChangePlan


def main(argv: list[str] | None = None) -> int:
    """Run change-plan command."""

    args = parse_args(argv or sys.argv[1:])
    runners = {
        "new": new_command,
        "status": status_command,
        "check": check_command,
        "explain": explain_command,
    }
    return runners[args.command](args)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse change-plan command arguments."""

    argument_parser = argparse.ArgumentParser(prog="python -m agent_maintainer change-plan")
    argument_parser.add_argument("--plan-dir", type=Path, default=PLAN_DIR)
    subparsers = argument_parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a starter change plan.")
    new_parser.add_argument("slug")
    new_parser.add_argument("--kind", default="mechanical-migration")
    new_parser.add_argument("--base-ref", default="origin/main")
    new_parser.add_argument("--integration-branch", default="")
    new_parser.add_argument("--target-branch", default="main")
    new_parser.add_argument("--merge-strategy", default="squash-after-series")
    new_parser.add_argument("--expected-unit", action="append", default=[])
    new_parser.add_argument("--force", action="store_true")

    subparsers.add_parser("status", help="List change plans.")
    check_parser = subparsers.add_parser("check", help="Validate change plans.")
    check_parser.add_argument("--base-ref")
    check_parser.add_argument("--staged", action="store_true")
    check_parser.add_argument("--no-git-scope", action="store_true")
    subparsers.add_parser("explain", help="Explain cohesive change plan format.")
    return argument_parser.parse_args(argv)


def new_command(args: argparse.Namespace) -> int:
    """Create starter change plan file."""

    target = args.plan_dir / f"{args.slug}{PLAN_SUFFIX}"
    if target.exists() and not args.force:
        print(f"change plan already exists: {target}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        templates.render_plan_template(
            args.slug,
            kind=args.kind,
            base_ref=args.base_ref,
            integration_branch=templates.IntegrationBranchTemplate(
                branch=args.integration_branch,
                target_branch=args.target_branch,
                merge_strategy=args.merge_strategy,
                expected_units=tuple(args.expected_unit),
            ),
        ),
        encoding="utf-8",
    )
    print(target.as_posix())
    return 0


def status_command(args: argparse.Namespace) -> int:
    """Print compact change-plan status."""

    plans, issues = load_plans(args.plan_dir)
    if not plans and not issues:
        print("No change plans found.")
        return 0
    for plan in plans:
        metadata = plan.metadata
        plan_path = plan.path.as_posix()
        expiry = metadata.expires.isoformat()
        print(
            f"{plan_path}: status={metadata.status} expires={expiry} base_ref={metadata.base_ref}"
        )
    print_issues(issues)
    return 1 if issues else 0


def check_command(args: argparse.Namespace) -> int:
    """Validate change plans and optional current Git scope."""

    plans, issues = load_plans(args.plan_dir)
    current_branch = ""
    for plan in plans:
        issues.extend(validation.validate_plan(plan))
        if not args.no_git_scope and plan.metadata.status == ACTIVE_STATUS:
            current_branch = current_branch or git_scope.current_branch(Path.cwd())
            issues.extend(validation.branch_state_issues(plan, current_branch))
            base_ref = args.base_ref or plan.metadata.base_ref
            changes = git_scope.git_changes(Path.cwd(), base_ref=base_ref, staged=args.staged)
            issues.extend(git_scope.scope_issues(plan, changes))
    if issues:
        print_issues(issues)
        return 1
    print("PASS change plans")
    return 0


def explain_command(_args: argparse.Namespace) -> int:
    """Explain cohesive change plan format."""

    print("Cohesive change plans live in .agent-maintainer/change-plans/<slug>.md")
    print("Use TOML front matter between +++ delimiters.")
    print("Required sections:")
    for section in validation.REQUIRED_SECTIONS:
        print(f"- {section}")
    return 0


def load_plans(plan_dir: Path) -> tuple[list[ChangePlan], list[validation.ValidationIssue]]:
    """Load all change plans from a directory."""

    plans: list[ChangePlan] = []
    issues: list[validation.ValidationIssue] = []
    for path in sorted(plan_dir.glob(f"*{PLAN_SUFFIX}")):
        try:
            plans.append(parser.parse_plan(path))
        except parser.PlanParseError as exc:
            issues.append(validation.ValidationIssue(path=path.as_posix(), message=str(exc)))
    return plans, issues


def print_issues(issues: list[validation.ValidationIssue]) -> None:
    """Print validation issues."""

    for issue in issues:
        print(f"FAIL {issue.path}: {issue.message}")


if __name__ == "__main__":
    sys.exit(main())
