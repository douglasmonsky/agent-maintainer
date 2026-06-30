"""Validate configured Mutmut target ratchet."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

GLOB_MARKERS = frozenset(("*", "?", "[", "]"))
SUPPORTED_MUTMUT_KEYS = frozenset(
    (
        "also_copy",
        "debug",
        "do_not_mutate",
        "do_not_mutate_patterns",
        "max_stack_depth",
        "mutate_only_covered_lines",
        "only_mutate",
        "pytest_add_cli_args",
        "pytest_add_cli_args_test_selection",
        "source_paths",
        "timeout_constant",
        "timeout_multiplier",
        "type_check_command",
        "use_setproctitle",
    )
)


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
    """Return nonzero when mutation targets regress."""

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
    mutmut_config = mutation_config(payload)
    targets = explicit_mutation_targets(payload)
    issues = list(count_issues(targets, min_targets))
    issues.extend(missing_path_issues(repo_root, targets))
    issues.extend(unsupported_key_issues(mutmut_config))
    issues.extend(
        missing_config_path_issues(
            repo_root,
            "also_copy",
            config_list_values(mutmut_config, "also_copy"),
        )
    )
    issues.extend(
        missing_config_path_issues(
            repo_root,
            "do_not_mutate",
            config_list_values(mutmut_config, "do_not_mutate"),
        )
    )
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

    configured_targets = config_list_values(mutation_config(payload), "only_mutate")
    seen: set[str] = set()
    targets: list[str] = []
    for target in configured_targets:
        if target not in seen:
            targets.append(target)
            seen.add(target)
    return tuple(targets)


def mutation_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Return Mutmut config table from parsed pyproject payload."""

    try:
        configured = payload["tool"]["mutmut"]
    except (KeyError, TypeError):
        return {}
    if not isinstance(configured, dict):
        return {}
    return configured


def config_list_values(config: dict[str, Any], key: str) -> tuple[str, ...]:
    """Return string values from a list-valued Mutmut config key."""

    values = config.get(key, [])
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, str))


def count_issues(targets: tuple[str, ...], min_targets: int) -> tuple[str, ...]:
    """Return target count issue when configured targets fall below ratchet."""

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


def missing_config_path_issues(
    repo_root: Path,
    key: str,
    values: tuple[str, ...],
) -> tuple[str, ...]:
    """Return missing concrete path issues for a Mutmut config key."""

    return tuple(
        f"mutmut {key} path does not exist: {value}"
        for value in values
        if is_concrete_config_path(value) and not (repo_root / value).exists()
    )


def unsupported_key_issues(config: dict[str, Any]) -> tuple[str, ...]:
    """Return issues for Mutmut keys unsupported by the pinned version."""

    return tuple(
        f"unsupported mutmut config key: {key}"
        for key in sorted(config)
        if key not in SUPPORTED_MUTMUT_KEYS
    )


def is_plain_path_target(target: str) -> bool:
    """Return whether target should be validated as a concrete path."""

    return (
        "/" in target
        and target.endswith(".py")
        and not any(marker in target for marker in GLOB_MARKERS)
    )


def is_concrete_config_path(value: str) -> bool:
    """Return whether a config value should be validated as a concrete path."""

    return "/" in value and not any(marker in value for marker in GLOB_MARKERS)


if __name__ == "__main__":
    sys.exit(main())
