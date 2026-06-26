"""Run Mutmut and clean generated mutation artifacts after successful runs."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from scripts.guardrail_executor import command_env
from scripts.guardrail_runtime import TRUE_ENV_VALUES

KEEP_MUTANTS_ENV = "AI_GUARDRAILS_KEEP_MUTANTS"
MUTANTS_DIR = Path("mutants")


def main(argv: list[str] | None = None) -> int:
    """Run Mutmut with CLI arguments."""

    return run_mutmut(sys.argv[1:] if argv is None else argv)


def run_mutmut(args: list[str]) -> int:
    """Run Mutmut and clean generated artifacts when the run succeeds."""

    result = subprocess.run(  # nosec B603
        [mutmut_executable(), *args],
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0:
        cleanup_mutants()
    return result.returncode


def mutmut_executable() -> str:
    """Return the resolved Mutmut executable path."""

    return shutil.which("mutmut") or "mutmut"


def cleanup_mutants() -> None:
    """Remove Mutmut generated artifacts unless explicitly preserved."""

    if keep_mutants():
        return
    if MUTANTS_DIR.exists():
        shutil.rmtree(MUTANTS_DIR)


def keep_mutants() -> bool:
    """Return whether generated mutation artifacts should be preserved."""

    return os.environ.get(KEEP_MUTANTS_ENV, "").casefold() in TRUE_ENV_VALUES


if __name__ == "__main__":
    sys.exit(main())
