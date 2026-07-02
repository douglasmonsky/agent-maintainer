"""Detect broad or excessive suppressions added in a diff.

The goal is not to ban suppressions. The goal is to prevent AI-assisted changes
from hiding lint/type/coverage failures with broad comments.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass

from agent_maintainer.core.config import load_config
from agent_maintainer.ecosystems.python.classification import is_python_path

NAME_STATUS_COPY_FIELD_COUNT = 3

SUPPRESSION_PATTERNS = (
    "# noqa",
    "# type: ignore",
    "# pylint: disable",
    "# pragma: no cover",
    "# pyright:",
)

BROAD_NOQA_RE = re.compile(r"#\s*noqa\s*(?:$|[#])")
BROAD_TYPE_IGNORE_RE = re.compile(r"#\s*type:\s*ignore\s*(?:$|[#])")
PYLINT_DISABLE_ALL_RE = re.compile(r"#\s*pylint:\s*disable\s*=\s*all\b")
PYRIGHT_FILE_DISABLE_RE = re.compile(r"#\s*pyright:\s*report\w+\s*=\s*(?:false|none)", re.I)


@dataclass(frozen=True)
class Suppression:
    """Classified suppression comment added by the current diff."""

    path: str
    line: str
    reason: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse suppression-budget command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_ref", nargs="?", default="HEAD")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Inspect staged changes with git diff --cached.",
    )
    parser.add_argument("--max-new-suppressions", type=int)
    return parser.parse_args(argv)


def git_diff_command(base_ref: str, *, staged: bool) -> list[str]:
    """Build copy-aware patch diff command."""

    git = shutil.which("git") or "git"
    command = [git, "diff", "--patch", "-C", "--find-copies-harder"]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    return command


def git_name_status_command(base_ref: str, *, staged: bool) -> list[str]:
    """Build copy-aware name-status command."""

    git = shutil.which("git") or "git"
    command = [git, "diff", "--name-status", "-C", "--find-copies-harder"]
    command.extend(["--cached"] if staged else [base_ref])
    command.append("--")
    return command


def diff_target_label(base_ref: str, *, staged: bool) -> str:
    """Return human-readable target label for error messages."""

    return "staged changes" if staged else repr(base_ref)


def copied_destination_paths(base_ref: str, *, staged: bool) -> frozenset[str]:
    """Return destination files copied from existing source files."""

    try:
        result = subprocess.run(  # nosec B603
            git_name_status_command(base_ref, staged=staged),
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        target = diff_target_label(base_ref, staged=staged)
        raise RuntimeError(f"Could not calculate copied paths for {target}: {stderr}") from exc

    destinations: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split("	")
        if len(parts) == NAME_STATUS_COPY_FIELD_COUNT and parts[0].startswith("C"):
            destinations.add(parts[2])
    return frozenset(destinations)


def added_python_lines(base_ref: str, *, staged: bool) -> list[tuple[str, str]]:
    """Return added Python lines from staged or ref-based git diff output."""

    try:
        result = subprocess.run(  # nosec B603
            git_diff_command(base_ref, staged=staged),
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        target = diff_target_label(base_ref, staged=staged)
        raise RuntimeError(f"Could not calculate diff suppressions for {target}: {stderr}") from exc

    copied_destinations = copied_destination_paths(base_ref, staged=staged)
    added: list[tuple[str, str]] = []
    current_path = ""
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_path = line.removeprefix("+++ b/")
            continue
        if not is_python_path(current_path) or current_path in copied_destinations:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append((current_path, line[1:]))
    return added


def classify(path: str, line: str) -> list[Suppression]:
    """Classify broad suppression patterns in a single added source line."""

    lower = line.lower()
    if not any(pattern in lower for pattern in SUPPRESSION_PATTERNS):
        return []

    issues: list[Suppression] = []
    if BROAD_NOQA_RE.search(line):
        issues.append(Suppression(path, line, "broad noqa without specific rule code"))
    if BROAD_TYPE_IGNORE_RE.search(line):
        issues.append(Suppression(path, line, "broad type ignore without specific error code"))
    if PYLINT_DISABLE_ALL_RE.search(line):
        issues.append(Suppression(path, line, "pylint disable=all"))
    if PYRIGHT_FILE_DISABLE_RE.search(line):
        issues.append(Suppression(path, line, "file-level pyright diagnostic disable"))
    return issues


def contains_suppression(line: str) -> bool:
    """Return whether a line contains any tracked suppression marker."""

    lower = line.lower()
    return any(pattern in lower for pattern in SUPPRESSION_PATTERNS)


def suppression_failures(added: list[tuple[str, str]], max_new_suppressions: int) -> list[str]:
    """Return failures for broad or excessive suppression comments."""

    suppressions = [(path, line) for path, line in added if contains_suppression(line)]
    issues = [issue for path, line in added for issue in classify(path, line)]

    failures = [format_suppression_failure(issue) for issue in issues]
    if len(suppressions) > max_new_suppressions:
        failures.append(
            f"Too many new suppression comments: {len(suppressions)} "
            f"(limit: {max_new_suppressions})."
        )
    return failures


def format_suppression_failure(issue: Suppression) -> str:
    """Format one classified suppression issue for terminal output."""

    stripped_line = issue.line.strip()
    return f"{issue.path}: {issue.reason}: {stripped_line}"


def print_failures(failures: list[str]) -> None:
    """Print suppression-budget failures with repair guidance."""

    print("Suppression budget failed:\n")
    for failure in failures:
        print(f"  {failure}")
    print("\nUse narrow suppressions only, and prefer fixing the underlying issue.")


def main(argv: list[str]) -> int:
    """Run the suppression-budget check and return a process exit code."""

    args = parse_args(argv)
    config = load_config()

    try:
        added = added_python_lines(args.base_ref, staged=args.staged)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    max_new_suppressions = (
        config.suppression_max_new
        if args.max_new_suppressions is None
        else args.max_new_suppressions
    )
    failures = suppression_failures(added, max_new_suppressions)

    if failures:
        print_failures(failures)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
