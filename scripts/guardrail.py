#!/usr/bin/env python3
"""Canonical command-line entrypoint for repository guardrails."""

from __future__ import annotations

import sys

from verify_quiet import main as verify_main

USAGE = """Usage:
  python scripts/guardrail.py verify [verify options]

Examples:
  python scripts/guardrail.py verify --profile fast
  python scripts/guardrail.py verify --profile precommit
  python scripts/guardrail.py verify --profile full
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE.rstrip())
        return 0

    command, *command_args = argv
    if command == "verify":
        return verify_main(command_args)

    print(f"Unknown guardrail command: {command}", file=sys.stderr)
    print(USAGE.rstrip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
