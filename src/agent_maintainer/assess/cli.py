"""Assessment command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from agent_maintainer.assess import (
    debt_score,
    efficacy,
    file_baseline_lifecycle,
    file_baselines,
    java_baselines,
    repair_fact_coverage,
    repair_fact_coverage_reporting,
    reporting,
    reviewability,
    setup_advisor,
)
from agent_maintainer.assess import (
    evidence as assess_evidence,
)
from agent_maintainer.assess.efficacy_reporting import render_text as render_efficacy_text
from agent_maintainer.assess.models import RepoEvidence
from agent_maintainer.config import loader as config_loader
from agent_maintainer.config.schema import MaintainerConfig

DEFAULT_TARGET = Path(".")
STORE_TRUE = "store_true"


def main(argv: list[str] | None = None) -> int:
    """Run assessment subcommands."""
    args = parse_args([] if argv is None else argv)
    target = args.target.resolve()
    if args.command == "java-baseline":
        return _run_java_baseline(args, target)
    if args.command == "file-baselines":
        return _run_file_baselines(args, target)
    repo_evidence = assess_evidence.collect_evidence(target, max_files=args.max_files)
    status = 1
    if args.command == "setup":
        status = _run_setup(args, repo_evidence)
    if args.command == "debt":
        status = _run_debt(args, target, repo_evidence)
    if args.command == "reviewability":
        status = _run_reviewability(args, target)
    if args.command == "repair-fact-coverage":
        status = _run_repair_fact_coverage(args, target)
    if args.command == "efficacy":
        status = _run_efficacy(args, target)
    return status


def _run_setup(args: argparse.Namespace, repo_evidence: RepoEvidence) -> int:
    """Run setup assessment."""
    report = setup_advisor.build_setup_report(repo_evidence)
    print(
        reporting.render_json(report) if args.json else reporting.render_setup_text(report),
    )
    return 0


def _run_debt(
    args: argparse.Namespace,
    target: Path,
    repo_evidence: RepoEvidence,
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
    try:
        with _working_directory(target):
            config = config_loader.load_config()
            if args.file_baseline_operation != "report":
                return _run_file_baseline_lifecycle(args, target, config)
            if args.dry_run:
                raise ValueError("--dry-run requires file-baselines create or prune")
            report = file_baselines.build_file_baseline_report(
                target,
                config,
                base_ref=args.base_ref,
                staged=args.staged,
            )
    except (OSError, TypeError, ValueError) as exc:
        print(f"file-baselines: {exc}", file=sys.stderr)
        return 2
    print(
        reporting.render_json(report)
        if args.json
        else reporting.render_file_baselines_text(report),
    )
    return 1 if report.mode == "blocking" and not report.passed else 0


def _run_file_baseline_lifecycle(
    args: argparse.Namespace,
    target: Path,
    config: MaintainerConfig,
) -> int:
    """Run explicit create, inspect, or prune for per-path file ceilings."""
    if args.file_baseline_operation == "inspect":
        summary = file_baseline_lifecycle.inspect_configured(target, config)
        print(file_baseline_lifecycle.render_summary(summary, json_output=args.json), end="")
        return 0
    operation = (
        file_baseline_lifecycle.create_candidate
        if args.file_baseline_operation == "create"
        else file_baseline_lifecycle.prune_candidate
    )
    destination, candidate = operation(target, config)
    rendered = file_baseline_lifecycle.render_candidate(candidate)
    if not args.dry_run:
        file_baseline_lifecycle.write_candidate(
            destination,
            candidate,
            overwrite=args.file_baseline_operation == "prune",
        )
    print(rendered, end="")
    return 0


def _run_java_baseline(args: argparse.Namespace, target: Path) -> int:
    """Run one explicit Java findings baseline lifecycle operation."""
    try:
        config = config_loader.load_config(target)
        configured_path = config.java.findings_baseline
        if args.java_baseline_operation == "inspect":
            summary = java_baselines.inspect_configured(target, configured_path)
            print(java_baselines.render_summary(summary, json_output=args.json), end="")
            return 0
        operation = (
            java_baselines.create_from_artifact
            if args.java_baseline_operation == "create"
            else java_baselines.prune_from_artifact
        )
        destination, candidate = operation(target, configured_path, args.artifact)
        rendered = java_baselines.render_candidate(candidate)
        if not args.dry_run:
            java_baselines.write_candidate(
                destination,
                candidate,
                overwrite=args.java_baseline_operation == "prune",
            )
        print(rendered, end="")
        return 0
    except (OSError, TypeError, ValueError) as exc:
        print(f"java-baseline: {exc}", file=sys.stderr)
        return 2


def _run_repair_fact_coverage(args: argparse.Namespace, target: Path) -> int:
    """Run repair-fact coverage assessment."""

    log_dir = args.log_dir if args.log_dir.is_absolute() else target / args.log_dir
    report = repair_fact_coverage.build_repair_fact_coverage_report(
        target,
        log_dir=log_dir,
        run_limit=args.run_limit,
    )
    output = (
        repair_fact_coverage_reporting.render_json(report)
        if args.json
        else repair_fact_coverage_reporting.render_text(report)
    )
    print(output)
    return 0


def _run_efficacy(args: argparse.Namespace, target: Path) -> int:
    """Run local agent efficacy assessment."""

    events_dir = args.events_dir if args.events_dir.is_absolute() else target / args.events_dir
    log_dir = args.log_dir if args.log_dir.is_absolute() else target / args.log_dir
    report = efficacy.build_efficacy_report(
        target,
        events_dir=events_dir,
        log_dir=log_dir,
        event_file_limit=args.event_file_limit,
    )
    print(report.to_json() if args.json else render_efficacy_text(report))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse assessment arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer assess")
    subparsers = parser.add_subparsers(dest="command", required=True)
    setup = subparsers.add_parser("setup", help="Recommend track, preset, and gates.")
    setup.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    setup.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
    )
    setup.add_argument("--json", action=STORE_TRUE)
    debt = subparsers.add_parser("debt", help="Render advisory Technical Debt Score.")
    debt.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    debt.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
    )
    debt.add_argument("--json", action=STORE_TRUE)
    debt.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    debt.add_argument("--no-write", action=STORE_TRUE)
    reviewability_parser = subparsers.add_parser(
        "reviewability",
        help="Render advisory changed-file reviewability summary.",
    )
    reviewability_parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    reviewability_parser.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
    )
    reviewability_parser.add_argument("--json", action=STORE_TRUE)
    reviewability_parser.add_argument("--base-ref", default="origin/main")
    reviewability_parser.add_argument("--staged", action=STORE_TRUE)

    file_baselines_parser = subparsers.add_parser(
        "file-baselines",
        help="Render advisory provider-neutral file baseline summary.",
    )
    file_baselines_parser.add_argument(
        "file_baseline_operation",
        nargs="?",
        choices=("report", "create", "inspect", "prune"),
        default="report",
    )
    file_baselines_parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    file_baselines_parser.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
        help=argparse.SUPPRESS,
    )
    file_baselines_parser.add_argument("--json", action=STORE_TRUE)
    file_baselines_parser.add_argument("--base-ref", default="origin/main")
    file_baselines_parser.add_argument("--staged", action=STORE_TRUE)
    file_baselines_parser.add_argument("--dry-run", action=STORE_TRUE)
    _add_java_baseline_parser(subparsers.add_parser)
    repair_fact_parser = subparsers.add_parser(
        "repair-fact-coverage",
        help="Assess structured repair facts for recent failures.",
    )
    repair_fact_parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    repair_fact_parser.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
        help=argparse.SUPPRESS,
    )
    repair_fact_parser.add_argument("--json", action=STORE_TRUE)
    repair_fact_parser.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    repair_fact_parser.add_argument("--run-limit", type=int, default=10)
    _add_efficacy_parser(subparsers.add_parser)
    return parser.parse_args(argv)


def _add_java_baseline_parser(
    add_parser: Callable[..., argparse.ArgumentParser],
) -> None:
    """Add explicit Java findings baseline lifecycle parsers."""
    lifecycle = add_parser(
        "java-baseline",
        help="Create, inspect, or prune the Java findings baseline.",
    )
    operations = lifecycle.add_subparsers(dest="java_baseline_operation", required=True)
    for name in ("create", "prune"):
        operation = operations.add_parser(name)
        operation.add_argument("--target", type=Path, default=DEFAULT_TARGET)
        operation.add_argument(
            "--artifact",
            type=Path,
            default=Path(".verify-logs/java-gradle/java-gradle-static.json"),
        )
        operation.add_argument("--dry-run", action=STORE_TRUE)
    inspect = operations.add_parser("inspect")
    inspect.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    inspect.add_argument("--json", action=STORE_TRUE)


def _add_efficacy_parser(
    add_parser: Callable[..., argparse.ArgumentParser],
) -> None:
    """Add efficacy assessment parser."""

    efficacy_parser = add_parser(
        "efficacy",
        help="Assess local agent efficacy metrics.",
    )
    efficacy_parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    efficacy_parser.add_argument(
        "--max-files",
        type=int,
        default=assess_evidence.DEFAULT_MAX_EVIDENCE_FILES,
        help=argparse.SUPPRESS,
    )
    efficacy_parser.add_argument("--json", action=STORE_TRUE)
    efficacy_parser.add_argument(
        "--events-dir",
        type=Path,
        default=Path(".verify-logs/events"),
    )
    efficacy_parser.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    efficacy_parser.add_argument(
        "--event-file-limit",
        type=int,
        default=efficacy.DEFAULT_EVENT_FILE_LIMIT,
    )


@contextmanager
def _working_directory(path: Path) -> Generator[None, None, None]:
    """Temporarily load config relative to a target repository."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
