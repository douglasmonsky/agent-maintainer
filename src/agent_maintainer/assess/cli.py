"""Assessment command-line interface."""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from agent_maintainer.assess.debt_score import build_debt_report, write_debt_artifacts
from agent_maintainer.assess.evidence import collect_evidence
from agent_maintainer.assess.reporting import (
    render_debt_text,
    render_json,
    render_setup_text,
)
from agent_maintainer.assess.setup_advisor import build_setup_report
from agent_maintainer.config.loader import load_config


def main(argv: list[str] | None = None) -> int:
    """Run assessment subcommands."""
    args = parse_args([] if argv is None else argv)
    target = args.target.resolve()
    if args.command == "setup":
        report = build_setup_report(collect_evidence(target))
        print(render_json(report) if args.json else render_setup_text(report))
        return 0
    if args.command == "debt":
        with _working_directory(target):
            config = load_config()
        log_dir = args.log_dir if args.log_dir.is_absolute() else target / args.log_dir
        report = build_debt_report(collect_evidence(target), config, log_dir=log_dir)
        if not args.no_write:
            write_debt_artifacts(report, log_dir)
        print(render_json(report) if args.json else render_debt_text(report))
        return 0
    return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse assessment arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer assess")
    subparsers = parser.add_subparsers(dest="command", required=True)
    setup = subparsers.add_parser("setup", help="Recommend track, preset, and gates.")
    setup.add_argument("--target", type=Path, default=Path("."))
    setup.add_argument("--json", action="store_true")
    debt = subparsers.add_parser("debt", help="Render advisory Technical Debt Score.")
    debt.add_argument("--target", type=Path, default=Path("."))
    debt.add_argument("--json", action="store_true")
    debt.add_argument("--log-dir", type=Path, default=Path(".verify-logs"))
    debt.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    """Temporarily load config relative to a target repository."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
