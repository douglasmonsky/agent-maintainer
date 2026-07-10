"""Initialize package-first maintainer adoption files."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_maintainer.core.scaffold import planning, transaction
from agent_maintainer.core.scaffold.presets import DEFAULT_PRESET, PRESETS
from agent_maintainer.core.scaffold.templates import (
    CORE_TRACK,
    TRACKS,
    StarterFile,
    starter_files_for_preset,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse initializer arguments."""
    parser = argparse.ArgumentParser(prog="python -m agent_maintainer init")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="repository root to initialize",
    )
    parser.add_argument(
        "--track",
        choices=TRACKS,
        default=CORE_TRACK,
        help="adoption track to initialize",
    )
    parser.add_argument(
        "--preset",
        choices=PRESETS,
        default=DEFAULT_PRESET,
        help="starter policy preset to write into config",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing generated files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print planned writes without changing files",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Write starter maintainer files for a package-first install."""
    args = parse_args(argv)
    target = args.target.resolve()
    files = files_for_track(args.track, args.preset)
    plan = planning.build_plan(target, files)
    print(planning.render_plan(plan))
    if args.dry_run:
        print("dry-run: no files written")
        return 0
    if planning.has_conflicts(plan) and not args.force:
        print("Refusing CONFLICT items without --force; no files were written.")
        return 1
    selected = planning.writable_items(plan, force=args.force)
    try:
        result = transaction.apply_transaction(selected, target=target)
    except transaction.InitTransactionError as exc:
        print(f"FAIL init: {exc}")
        return 1
    _print_result(result)
    return 0


def _print_result(result: transaction.InitTransactionResult) -> None:
    """Print applied destinations and local recovery pointers."""

    for backup in result.backups:
        print("backed up", backup.original, "->", backup.backup)
    for path in result.written:
        print("wrote", path)
    if result.rollback_manifest is not None:
        print("rollback manifest:", result.rollback_manifest)


def files_for_track(track: str, preset: str = DEFAULT_PRESET) -> tuple[StarterFile, ...]:
    """Return starter files included in adoption track."""

    return tuple(starter for starter in starter_files_for_preset(preset) if track in starter.tracks)
