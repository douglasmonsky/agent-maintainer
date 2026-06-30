"""Validate configured Mutmut target ratchet."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

GLOB_MARKERS = frozenset("*?[]")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse mutmut target ratchet arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-targets",
        type=int,
        required=True,
        help="Minimum number of explicit [tool.mutmut].only_mutate targets.",
    )
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Return nonzero when configured mutation targets regress."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    issues = mutmut_target_issues(Path.cwd(), args.pyproject, args.min_targets)
    if not issues:
        print(f"mutmut target ratchet passed: {args.min_targets} target floor")
        return 0
    print("Mutmut target ratchet failed:")
    for issue in issues:
        print(f"- {issue}")
    return 1


def mutmut_target_issues(
    repo_root: Path,
    pyproject_path: str,
    min_targets: int,
) -> tuple[str, ...]:
    """Return configured Mutmut target ratchet issues."""

    if min_targets <= 0:
        return ()
    payload = read_pyproject(repo_root / pyproject_path)
    targets = explicit_mutation_targets(payload)
    issues = list(count_issues(targets, min_targets))
    issues.extend(missing_path_issues(repo_root, targets))
    return tuple(issues)


def read_pyproject(path: Path) -> dict[str, Any]:
    """Read TOML project configuration."""

    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return payload


def explicit_mutation_targets(payload: dict[str, Any]) -> tuple[str, ...]:
    """Return unique explicit Mutmut only_mutate targets."""

    tool = payload.get("tool")
    if not isinstance(tool, dict):
        return ()
    mutmut = tool.get("mutmut")
    if not isinstance(mutmut, dict):
        return ()
    only_mutate = mutmut.get("only_mutate")
    if not isinstance(only_mutate, list):
        return ()
    targets = tuple(str(item).strip() for item in only_mutate if str(item).strip())
    return tuple(dict.fromkeys(targets))


def count_issues(targets: tuple[str, ...], min_targets: int) -> tuple[str, ...]:
    """Return target-count floor issue when below ratchet."""

    if len(targets) >= min_targets:
        return ()
    return (
        f"configured mutmut only_mutate targets {len(targets)} below required floor {min_targets}",
    )


def missing_path_issues(repo_root: Path, targets: tuple[str, ...]) -> tuple[str, ...]:
    """Return missing filesystem path issues for path-like targets."""

    return tuple(
        f"mutmut target path does not exist: {target}"
        for target in targets
        if is_plain_path_target(target) and not (repo_root / target).exists()
    )


def is_plain_path_target(target: str) -> bool:
    """Return whether target should be validated as a concrete path."""

    return (
        "/" in target
        and target.endswith(".py")
        and not any(marker in target for marker in GLOB_MARKERS)
    )


if __name__ == "__main__":
    sys.exit(main())
