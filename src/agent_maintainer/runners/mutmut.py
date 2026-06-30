"""Run Mutmut and clean generated mutation artifacts after successful runs."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from agent_maintainer.core.executor import command_env
from agent_maintainer.core.runtime import TRUE_ENV_VALUES
from agent_maintainer.runners import mutmut_lock, mutmut_stats

KEEP_MUTANTS_ENV = "AGENT_MAINTAINER_KEEP_MUTANTS"
MUTANTS_DIR = Path("mutants")
DEFAULT_RATCHET = mutmut_stats.MutmutRatchet()


def main(argv: list[str] | None = None) -> int:
    """Run Mutmut CLI arguments."""

    mutmut_args, ratchet = parse_runner_args(sys.argv[1:] if argv is None else argv)
    return run_mutmut(mutmut_args, ratchet=ratchet)


def parse_runner_args(argv: list[str]) -> tuple[list[str], mutmut_stats.MutmutRatchet]:
    """Parse Agent Maintainer runner flags and leave Mutmut args untouched."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--max-survivors", type=int)
    parser.add_argument("--max-suspicious", type=int)
    parser.add_argument("--max-timeouts", type=int)
    parser.add_argument("--min-score", type=int)
    args, mutmut_args = parser.parse_known_args(argv)
    ratchet = mutmut_stats.MutmutRatchet(
        enabled=any(
            value is not None
            for value in (
                args.max_survivors,
                args.max_suspicious,
                args.max_timeouts,
                args.min_score,
            )
        ),
        max_survivors=args.max_survivors or 0,
        max_suspicious=args.max_suspicious or 0,
        max_timeouts=args.max_timeouts or 0,
        min_score=args.min_score or 0,
    )
    return mutmut_args, ratchet


def run_mutmut(
    args: list[str],
    *,
    ratchet: mutmut_stats.MutmutRatchet = DEFAULT_RATCHET,
) -> int:
    """Run Mutmut and clean generated artifacts when the run succeeds."""

    with mutmut_lock.mutmut_run_lock():
        result = run_command([mutmut_executable(), *args])
        forward_output(result)
        if result.returncode != 0:
            return result.returncode
        if ratchet.enabled:
            ratchet_status = check_result_ratchet(ratchet)
            if ratchet_status != 0:
                return ratchet_status
        cleanup_mutants()
        return result.returncode


def check_result_ratchet(ratchet: mutmut_stats.MutmutRatchet) -> int:
    """Export Mutmut stats and return nonzero when result ratchets fail."""

    export_result = run_command([mutmut_executable(), "export-cicd-stats"])
    if export_result.returncode != 0:
        forward_output(export_result)
        return export_result.returncode
    try:
        stats = mutmut_stats.read_stats()
    except (OSError, ValueError) as exc:
        print(f"Mutmut result ratchet failed: {exc}")
        return 1
    issues = mutmut_stats.ratchet_issues(stats, ratchet)
    if not issues:
        print(f"Mutmut result ratchet passed: {mutmut_stats.render_summary(stats)}")
        return 0
    print("Mutmut result ratchet failed:")
    for issue in issues:
        print(f"- {issue}")
    print(mutmut_stats.render_summary(stats))
    return 1


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a Mutmut subprocess command."""

    return subprocess.run(  # nosec B603
        command,
        text=True,
        capture_output=True,
        env=command_env(),
        check=False,
    )


def forward_output(result: subprocess.CompletedProcess[str]) -> None:
    """Forward captured process output."""

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def mutmut_executable() -> str:
    """Return resolved Mutmut executable path."""

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
