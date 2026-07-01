"""Initialize package-first maintainer adoption files."""

from __future__ import annotations

import argparse
from pathlib import Path

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
    conflicts = [
        starter.path for starter in files if (target / starter.path).exists() and not args.force
    ]
    if conflicts:
        print("Refusing to overwrite existing files without --force:")
        for conflict in conflicts:
            print(f"  {conflict}")
        return 1
    for starter in files:
        destination = target / starter.path
        if args.dry_run:
            print(f"would write {destination}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(starter.content, encoding="utf-8")
        print(f"wrote {destination}")
    return 0


def files_for_track(track: str, preset: str = DEFAULT_PRESET) -> tuple[StarterFile, ...]:
    """Return starter files included in adoption track."""

    return tuple(starter for starter in starter_files_for_preset(preset) if track in starter.tracks)
