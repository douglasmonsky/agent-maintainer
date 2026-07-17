"""Command handlers for explicit Java and provider-neutral baseline lifecycles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.assess import (
    file_baseline_lifecycle,
    file_baselines,
    java_baselines,
    reporting,
)
from agent_maintainer.assess.models import FileBaselineReport
from agent_maintainer.config import loader as config_loader
from agent_maintainer.config.schema import MaintainerConfig


def run_file_baselines(args: argparse.Namespace, target: Path) -> int:
    """Run provider-neutral file baseline reporting or lifecycle operations."""
    try:
        result = _file_baseline_result(args, target)
    except (OSError, TypeError, ValueError) as exc:
        print(f"file-baselines: {exc}", file=sys.stderr)
        return 2
    if isinstance(result, int):
        return result
    print(
        reporting.render_json(result)
        if args.json
        else reporting.render_file_baselines_text(result),
    )
    return 1 if result.mode == "blocking" and not result.passed else 0


def run_java_baseline(args: argparse.Namespace, target: Path) -> int:
    """Run one explicit Java findings baseline lifecycle operation."""
    try:
        return _java_baseline_operation(args, target)
    except (OSError, TypeError, ValueError) as exc:
        print(f"java-baseline: {exc}", file=sys.stderr)
        return 2


def _file_baseline_result(
    args: argparse.Namespace,
    target: Path,
) -> int | FileBaselineReport:
    config = config_loader.load_config(target)
    if args.file_baseline_operation != "report":
        return _run_file_baseline_lifecycle(args, target, config)
    if args.dry_run:
        raise ValueError("--dry-run requires file-baselines create or prune")
    return file_baselines.build_file_baseline_report(
        target,
        config,
        base_ref=args.base_ref,
        staged=args.staged,
    )


def _run_file_baseline_lifecycle(
    args: argparse.Namespace,
    target: Path,
    config: MaintainerConfig,
) -> int:
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


def _java_baseline_operation(args: argparse.Namespace, target: Path) -> int:
    configured_path = config_loader.load_config(target).java.findings_baseline
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
