"""Assessment command-line interface."""

from __future__ import annotations

import argparse
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from agent_maintainer.assess import (
    debt_score,
    file_baselines,
    reporting,
    reviewability,
    setup_advisor,
)
from agent_maintainer.assess import (
    evidence as assess_evidence,
)
from agent_maintainer.config import loader as config_loader


def main(argv: list[str] | None = None) -> int:
    """Run assessment subcommands."""
    args = parse_args([] if argv is None else argv)
    target = args.target.resolve()
    repo_evidence = assess_evidence.collect_evidence(target, max_files=args.max_files)
    if args.command == "setup":
        return _run_setup(args, repo_evidence)
    if args.command == "debt":
        return _run_debt(args, target, repo_evidence)
    if args.command == "reviewability":
        return _run_reviewability(args, target)
    if args.command == "file-baselines":
        return _run_file_baselines(args, target)
    return 1


def _run_setup(args: argparse.Namespace, repo_evidence) -> int:
    """Run setup assessment."""
    report = setup_advisor.build_setup_report(repo_evidence)
    print(
        reporting.render_json(report) if args.json else reporting.render_setup_text(report),
    )
    return 0


def _run_debt(
    args: argparse.Namespace,
    target: Path,
    repo_evidence,
) -> int:
    """Run technical debt assessment."""
    with _working_directory(target):
        config = config_loader.load_config()
        log_dir = args.log_dir if args.log_dir.is_absolute() else target / args.log_dir
        report = debt_score.build_debt_report(repo_evidence, config, log_dir=log_dir)
        if not args.no_write:
            debt_score.write_debt_artifacts(report, log_dir)
    print(
        reporting.render_json(report) if args.json else reporting.render_debt_text(report),
    )
    return 0


def _run_reviewability(args: argparse.Namespace, target: Path) -> int:
    """Run provider-aware reviewability assessment."""
    with _working_directory(target):
        config = config_loader.load_config()
        report = reviewability.build_reviewability_report(
            target,
            config,
            base_ref=args.base_ref,
            staged=args.staged,
        )
    print(
        reporting.render_json(report) if args.json else reporting.render_reviewability_text(report),
    )
    return 0


def _run_file_baselines(args: argparse.Namespace, target: Path) -> int:
    """Run provider-neutral file baseline assessment."""
    with _working_directory(target):
        config = config_loader.load_config()
        report = file_baselines.build_file_baseline_report(
            target,
            config,
            base_ref=args.base_ref,
            staged=args.staged,
        )
    print(
        reporting.render_json(report)
        if args.json
        else reporting.render_file_baselines_text(report),
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse assessment arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer assess")
    subparsers = parser.add_subparsers(dest="command", required=True)
    setup = subparsers.add_parser("setup", help="Recommend track, preset, and gates.")
    setup.add_argument("--target", type=Path, default=Path("."))
    setup.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
    )
    setup.add_argument("--json", action="store_true")
    debt = subparsers.add_parser("debt", help="Render advisory Technical Debt Score.")
    debt.add_argument("--target", type=Path, default=Path("."))
    debt.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
    )
    debt.add_argument("--json", action="store_true")
    debt.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    debt.add_argument("--no-write", action="store_true")
    reviewability_parser = subparsers.add_parser(
        "reviewability",
        help="Render advisory changed-file reviewability summary.",
    )
    reviewability_parser.add_argument("--target", type=Path, default=Path("."))
    reviewability_parser.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
    )
    reviewability_parser.add_argument("--json", action="store_true")
    reviewability_parser.add_argument("--base-ref", default="origin/main")
    reviewability_parser.add_argument("--staged", action="store_true")

    file_baselines_parser = subparsers.add_parser(
        "file-baselines",
        help="Render advisory provider-neutral file baseline summary.",
    )
    file_baselines_parser.add_argument("--target", type=Path, default=Path("."))
    file_baselines_parser.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
        help=argparse.SUPPRESS,
    )
    file_baselines_parser.add_argument("--json", action="store_true")
    file_baselines_parser.add_argument("--base-ref", default="origin/main")
    file_baselines_parser.add_argument("--staged", action="store_true")
    return parser.parse_args(argv)


@contextmanager
def _working_directory(path: Path) -> Generator[None, None, None]:
    """Temporarily load config relative to a target repository."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
