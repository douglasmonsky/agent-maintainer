"""Validate Tach configuration before running the architecture gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_maintainer.tach import tach_config_issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse Tach config validation options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-root-module",
        action="store_true",
        help='Require root_module = "forbid".',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate tach.toml and print all discovered configuration issues."""

    args = parse_args(argv)
    issues = tach_config_issues(Path.cwd(), require_strict_root=args.strict_root_module)
    if not issues:
        print("tach.toml is configured for architecture checks.")
        return 0
    for issue in issues:
        print(issue)
    return 1


if __name__ == "__main__":
    sys.exit(main())
