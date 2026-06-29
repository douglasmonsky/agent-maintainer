"""Command line interface for Archguard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from archguard.decision_notes import (
    DEFAULT_DECISION_ROOTS,
    DEFAULT_POLICY_PATTERNS,
    decision_check_failures,
    new_decision_note,
)
from archguard.impact import (
    load_architecture,
    render_boundary,
    render_impact,
    render_map,
)
from archguard.tach_config import tach_config_issues


def main(argv: list[str] | None = None) -> int:
    """Run the Archguard CLI."""
    parser = argparse.ArgumentParser(prog="archguard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    map_parser = subparsers.add_parser("map")
    map_parser.set_defaults(handler=map_main_from_args)
    impact_parser = subparsers.add_parser("impact")
    impact_parser.add_argument("path", type=Path)
    impact_parser.set_defaults(handler=impact_main_from_args)
    boundary_parser = subparsers.add_parser("explain-boundary")
    boundary_parser.add_argument("source", type=Path)
    boundary_parser.add_argument("target", type=Path)
    boundary_parser.set_defaults(handler=boundary_main_from_args)
    tach_parser = subparsers.add_parser("tach-config")
    tach_parser.add_argument(
        "--strict-root-module",
        action="store_true",
        help='Require root_module = "forbid".',
    )
    tach_parser.set_defaults(handler=tach_config_main_from_args)

    decision_parser = subparsers.add_parser("decision-check")
    decision_parser.add_argument("--base-ref", default="HEAD")
    decision_parser.add_argument("--staged", action="store_true")
    decision_parser.add_argument(
        "--decision-root",
        action="append",
        default=[],
        help="Directory containing architecture decision notes. May be repeated.",
    )
    decision_parser.add_argument(
        "--policy-pattern",
        action="append",
        default=[],
        help="Architecture policy pattern to watch. May be repeated.",
    )
    decision_parser.set_defaults(handler=decision_check_main_from_args)

    decision_group = subparsers.add_parser("decision")
    decision_subparsers = decision_group.add_subparsers(
        dest="decision_command",
        required=True,
    )
    new_parser = decision_subparsers.add_parser("new")
    new_parser.add_argument("slug")
    new_parser.add_argument(
        "--decision-root",
        default=DEFAULT_DECISION_ROOTS[0],
        help="Directory where the decision note should be created.",
    )

    new_parser.set_defaults(handler=decision_new_main_from_args)
    args = parser.parse_args(argv)
    return args.handler(args)


def console_main() -> None:
    """Console-script entrypoint for Archguard."""
    sys.exit(main(sys.argv[1:]))


def tach_config_main(argv: list[str] | None = None) -> int:
    """Run Tach configuration validation as a standalone CLI."""
    parser = argparse.ArgumentParser(description="Validate Tach architecture configuration.")
    parser.add_argument(
        "--strict-root-module",
        action="store_true",
        help='Require root_module = "forbid".',
    )
    return tach_config_main_from_args(parser.parse_args(argv))


def map_main_from_args(_args: argparse.Namespace) -> int:
    """Run map command from parsed args."""

    return map_main()


def impact_main_from_args(args: argparse.Namespace) -> int:
    """Run impact command from parsed args."""

    return impact_main(args.path)


def boundary_main_from_args(args: argparse.Namespace) -> int:
    """Run boundary command from parsed args."""

    return boundary_main(args.source, args.target)


def map_main() -> int:
    """Print Tach module ownership map."""

    architecture = load_architecture(Path.cwd())
    print(render_map(architecture))
    return 0


def impact_main(path: Path) -> int:
    """Print architecture impact for one path."""

    architecture = load_architecture(Path.cwd())
    print(render_impact(Path.cwd(), architecture, path))
    return 0


def boundary_main(source: Path, target: Path) -> int:
    """Print boundary explanation between two paths."""

    architecture = load_architecture(Path.cwd())
    print(render_boundary(Path.cwd(), architecture, source, target))
    return 0


def tach_config_main_from_args(args: argparse.Namespace) -> int:
    """Validate tach.toml and print discovered configuration issues."""
    issues = tach_config_issues(Path.cwd(), require_strict_root=args.strict_root_module)
    if not issues:
        print("tach.toml configured for architecture checks.")
        return 0
    for issue in issues:
        print(issue)
    return 1


def decision_check_main_from_args(args: argparse.Namespace) -> int:
    """Run the architecture decision-note gate."""
    decision_roots = tuple(args.decision_root) or DEFAULT_DECISION_ROOTS
    policy_patterns = tuple(args.policy_pattern) or DEFAULT_POLICY_PATTERNS
    failures = decision_check_failures(
        Path.cwd(),
        base_ref=args.base_ref,
        staged=args.staged,
        decision_roots=decision_roots,
        policy_patterns=policy_patterns,
    )
    if not failures:
        print("architecture decision notes cover architecture policy changes.")
        return 0
    for failure in failures:
        print(failure)
    return 1


def decision_new_main_from_args(args: argparse.Namespace) -> int:
    """Create a new architecture decision note."""
    path = new_decision_note(
        Path.cwd(),
        args.slug,
        decision_root=args.decision_root,
    )
    print(f"Created architecture decision note: {path}")
    return 0
