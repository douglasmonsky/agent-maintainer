"""Run configured secret scanner backends with compact guardrail output."""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

from guardrail_lib.config.schema import GITLEAKS_SCANNER, SUPPORTED_SECRET_SCANNERS

CURRENT_TREE_MODE = "current-tree"
STAGED_MODE = "staged"
RANGE_MODE = "range"
HISTORY_MODE = "history"
SECRET_SCAN_MODES = frozenset((CURRENT_TREE_MODE, STAGED_MODE, RANGE_MODE, HISTORY_MODE))


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse secret scan wrapper arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--mode", choices=sorted(SECRET_SCAN_MODES), required=True)
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--report-path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    """Run configured secret scanner and return its exit code."""
    args = parse_args(argv)
    if args.backend not in SUPPORTED_SECRET_SCANNERS:
        supported = ", ".join(sorted(SUPPORTED_SECRET_SCANNERS))
        print(f"Unsupported secret scanner backend: {args.backend}. Supported: {supported}.")
        return 1
    if args.backend == GITLEAKS_SCANNER:
        return run_gitleaks(args)
    print(f"Unsupported secret scanner backend: {args.backend}.")
    return 1


def run_gitleaks(args: argparse.Namespace) -> int:
    """Run Gitleaks using the configured scan mode."""
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    command = gitleaks_command(args.mode, args.base_ref, report_path)
    if args.mode == STAGED_MODE:
        return run_gitleaks_staged(command)
    result = subprocess.run(command, text=True, capture_output=True, check=False)  # nosec B603
    print_combined_output(result)
    return result.returncode


def gitleaks_command(mode: str, base_ref: str, report_path: Path) -> list[str]:
    """Build the Gitleaks command for one scan mode."""
    common = [
        "--no-banner",
        "--no-color",
        "--redact",
        "--report-format",
        "json",
        "--report-path",
        str(report_path),
    ]
    if mode == CURRENT_TREE_MODE:
        return ["gitleaks", "dir", *common, "."]
    if mode == RANGE_MODE:
        return ["gitleaks", "git", *common, f"--log-opts=--all {base_ref}..HEAD", "."]
    if mode == HISTORY_MODE:
        return ["gitleaks", "git", *common, "--log-opts=--all", "."]
    return ["gitleaks", "stdin", *common]


def run_gitleaks_staged(command: list[str]) -> int:
    """Scan staged diff content with Gitleaks stdin mode."""
    git = shutil.which("git")
    if git is None:
        print("git executable not found.")
        return 1
    diff_result = subprocess.run(  # nosec B603
        [git, "diff", "--cached", "--patch"],
        text=True,
        capture_output=True,
        check=False,
    )
    if diff_result.returncode != 0:
        print_combined_output(diff_result)
        return diff_result.returncode
    if not diff_result.stdout.strip():
        print("No staged diff to scan.")
        return 0
    result = subprocess.run(  # nosec B603
        command,
        input=diff_result.stdout,
        text=True,
        capture_output=True,
        check=False,
    )
    print_combined_output(result)
    return result.returncode


def print_combined_output(result: subprocess.CompletedProcess[str]) -> None:
    """Print subprocess output preserving stderr after stdout."""
    for output in (result.stdout, result.stderr):
        if output:
            print(output.rstrip())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
