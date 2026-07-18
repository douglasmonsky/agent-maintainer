"""Public contract diff, check, and snapshot commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.contracts.baseline import (
    DEFAULT_BASELINE_PATH,
    write_baseline_atomic,
)
from agent_maintainer.contracts.models import ContractBaseline, ContractReport
from agent_maintainer.contracts.reporting import render_json, render_text
from agent_maintainer.contracts.service import build_contract_report

SUCCESS = 0
UNRESOLVED = 1
INVALID = 2
DEFAULT_BASE_REF = "origin/main"


def main(argv: list[str] | None = None) -> int:
    """Run one isolated contract-ratchet command."""

    args = _parser().parse_args(argv)
    if args.command == "snapshot" and not args.write:
        print("snapshot requires --write", file=sys.stderr)
        return INVALID
    target = args.target.resolve()
    report = build_contract_report(
        target,
        base_ref=args.base_ref,
        mode=args.command,
        initialize=bool(getattr(args, "initialize", False)),
    )
    sys.stdout.write(render_json(report) if args.json else render_text(report))
    status = _status(args.command, report)
    if args.command != "snapshot" or status != SUCCESS:
        return status
    if not report.can_snapshot:
        return UNRESOLVED
    return _write_snapshot(target, report)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-maintainer contract")
    subparsers = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", type=Path, default=Path("."))
    common.add_argument("--base-ref", default=DEFAULT_BASE_REF)
    common.add_argument("--json", action="store_true")
    subparsers.add_parser("diff", parents=(common,))
    subparsers.add_parser("check", parents=(common,))
    snapshot = subparsers.add_parser("snapshot", parents=(common,))
    snapshot.add_argument("--write", action="store_true")
    snapshot.add_argument("--initialize", action="store_true")
    return parser


def _status(command: str, report: ContractReport) -> int:
    if report.errors:
        return INVALID
    if command == "diff":
        return SUCCESS
    return UNRESOLVED if report.unresolved else SUCCESS


def _write_snapshot(repo_root: Path, report: ContractReport) -> int:
    baseline = ContractBaseline(
        package_version=report.current_package_version,
        descriptors=report.descriptors,
    )
    try:
        write_baseline_atomic(repo_root, DEFAULT_BASELINE_PATH, baseline)
    except (OSError, ValueError) as exc:
        print(f"snapshot write failed: {exc}", file=sys.stderr)
        return INVALID
    return SUCCESS


if __name__ == "__main__":  # pragma: no cover - exercised through main
    raise SystemExit(main())
