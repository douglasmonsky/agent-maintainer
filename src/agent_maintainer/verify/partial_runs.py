"""Select and aggregate independently executed verifier groups."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from agent_maintainer.models import Check
from agent_maintainer.verify.artifact_adapters import PartialRunContext
from agent_maintainer.verify.groups import (
    GROUP_NAMES,
    VerificationGroupError,
    checks_for_group,
)
from agent_run_artifacts import verification_aggregate
from agent_run_artifacts.history import atomic_write_text

AGGREGATE_ERROR_STATUS = 1
USAGE_ERROR_STATUS = 2


class PartialRunSelectionError(ValueError):
    """Raised when profile checks cannot satisfy a verifier group contract."""


def valid_group(group: str | None) -> bool:
    """Return whether an optional group is part of the verifier contract."""

    return group is None or group in GROUP_NAMES


def select_checks(checks: Sequence[Check], group: str | None) -> list[Check]:
    """Select the requested verifier group from profile checks."""

    if group is None:
        return list(checks)
    try:
        return checks_for_group(checks, group)
    except VerificationGroupError as exc:
        raise PartialRunSelectionError(str(exc)) from exc


def partial_run_context(
    args: argparse.Namespace,
    fingerprint: dict[str, object],
    selected_checks: Sequence[Check],
) -> PartialRunContext | None:
    """Return aggregate identity for one grouped run."""

    group = args.group
    if group is None:
        return None
    identity = {
        "profile": fingerprint["profile"],
        "head": fingerprint["head"],
        "base_ref": fingerprint["base_ref"],
        "compare_branch": fingerprint["compare_branch"],
        "staged": fingerprint["staged"],
        "index_hash": fingerprint["index_hash"],
        "worktree_hash": fingerprint["worktree_hash"],
        "untracked_hash": fingerprint["untracked_hash"],
        "config_hash": fingerprint["config_hash"],
        "environment_hash": fingerprint["environment_hash"],
        "selected_checks": tuple(check.name for check in selected_checks),
    }
    return PartialRunContext(group=group, required_groups=GROUP_NAMES, identity=identity)


def aggregate_partial_results(args: argparse.Namespace) -> int:
    """Aggregate partial manifests without loading or running verifier checks."""

    if args.group is not None:
        print("FAIL: --group cannot be combined with --aggregate-partial", file=sys.stderr)
        return USAGE_ERROR_STATUS
    partial_paths = [Path(path) for path in args.aggregate_partial]
    output_path = Path(args.aggregate_output)
    try:
        payload = verification_aggregate.aggregate_partial_manifests(partial_paths)
    except verification_aggregate.VerificationAggregateError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return AGGREGATE_ERROR_STATUS
    atomic_write_text(output_path, f"{json.dumps(payload, indent=2, sort_keys=True)}\n")
    print(f"PASS: aggregated {len(partial_paths)} verifier groups")
    return 0
