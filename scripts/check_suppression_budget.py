#!/usr/bin/env python3
"""Detect broad or excessive suppressions added in a diff.

The goal is not to ban suppressions. The goal is to prevent AI-assisted changes
from hiding lint/type/coverage failures with broad comments.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

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
    path: str
    line: str
    reason: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_ref", nargs="?", default="HEAD")
    parser.add_argument("--max-new-suppressions", type=int, default=3)
    return parser.parse_args(argv)


def added_python_lines(base_ref: str) -> list[tuple[str, str]]:
    try:
        result = subprocess.run(
            ["git", "diff", "--unified=0", base_ref, "--", "*.py"],
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown git diff failure"
        raise RuntimeError(f"Could not inspect suppression diff against {base_ref!r}: {stderr}") from exc

    path = "<unknown>"
    added: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            path = line.removeprefix("+++ b/")
            continue
        if line.startswith("+") and not line.startswith("+++"):  # added source line
            added.append((path, line[1:]))
    return added


def classify(path: str, line: str) -> list[Suppression]:
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


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        added = added_python_lines(args.base_ref)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    suppressions = [(path, line) for path, line in added if any(p in line.lower() for p in SUPPRESSION_PATTERNS)]
    issues = [issue for path, line in added for issue in classify(path, line)]

    failures: list[str] = []
    for issue in issues:
        failures.append(f"{issue.path}: {issue.reason}: {issue.line.strip()}")

    if len(suppressions) > args.max_new_suppressions:
        failures.append(
            f"Too many new suppression comments: {len(suppressions)} "
            f"(limit: {args.max_new_suppressions})."
        )

    if failures:
        print("Suppression budget failed:\n")
        for failure in failures:
            print(f"  {failure}")
        print("\nUse narrow suppressions only, and prefer fixing the underlying issue.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
