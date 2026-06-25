#!/usr/bin/env python3
"""Canonical command-line entrypoint for repository guardrails."""

from __future__ import annotations

import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from verify_quiet import main as verify_main

USAGE = """Usage:
  python scripts/guardrail.py install
  python scripts/guardrail.py verify [verify options]

Examples:
  python scripts/guardrail.py install
  python scripts/guardrail.py verify --profile fast
  python scripts/guardrail.py verify --profile precommit
  python scripts/guardrail.py verify --profile full
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE.rstrip())
        return 0

    command, *command_args = argv
    if command == "install":
        return install()
    if command == "verify":
        return verify_main(command_args)

    print(f"Unknown guardrail command: {command}", file=sys.stderr)
    print(USAGE.rstrip(), file=sys.stderr)
    return 2


def install() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    pre_commit_status = install_pre_commit(repo_root)
    report_codex_hooks(repo_root)
    return pre_commit_status


def install_pre_commit(repo_root: Path) -> int:
    config_path = repo_root / ".pre-commit-config.yaml"
    if not config_path.exists():
        print("SKIP pre-commit: .pre-commit-config.yaml is not present.")
        return 0

    pre_commit = find_pre_commit(repo_root)
    if pre_commit is None:
        print("FAIL pre-commit: command not found. Install config/dev-dependencies.txt first.")
        return 1

    result = subprocess.run(  # nosec B603
        [pre_commit, "install"],
        cwd=repo_root,
        text=True,
        check=False,
    )
    return result.returncode


def find_pre_commit(repo_root: Path) -> str | None:
    for relative in (".venv/bin/pre-commit", "venv/bin/pre-commit"):
        candidate = repo_root / relative
        if candidate.exists():
            return str(candidate)
    return shutil.which("pre-commit")


def report_codex_hooks(repo_root: Path) -> None:
    config_path = repo_root / ".codex" / "config.toml"
    if config_path.exists():
        print("Codex hooks are configured in .codex/config.toml.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
