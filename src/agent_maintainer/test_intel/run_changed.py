"""Execute the smallest known-safe set of tests for changed Python files."""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from pathlib import Path

from agent_maintainer.checks.change_budget import changed_python_files, run_git_numstat
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.test_intel.mapping import likely_tests_for_changes


def selected_test_paths(
    config: MaintainerConfig,
    *,
    base_ref: str,
    staged: bool,
    repo_root: Path,
) -> tuple[str, ...]:
    """Return existing mapped and directly changed Python test paths."""

    changes = run_git_numstat(base_ref, staged=staged)
    source_changes, test_changes = changed_python_files(changes, config)
    source_paths = tuple(sorted(change.path for change in source_changes))
    mapped = likely_tests_for_changes(source_paths, config, repo_root)
    candidates = {
        *(match.test_path for match in mapped),
        *(change.path for change in test_changes),
    }
    return tuple(sorted(path for path in candidates if (repo_root / path).is_file()))


def run_selected_tests(paths: tuple[str, ...], *, repo_root: Path) -> int:
    """Run selected tests without commit-time coverage collection."""

    if not paths:
        print("PASS: no affected Python tests")
        return 0
    command = [
        project_python(repo_root),
        "-m",
        "pytest",
        "-q",
        "--tb=short",
        "--disable-warnings",
        "-p",
        "no:tach",
        *paths,
    ]
    result = subprocess.run(  # nosec B603
        command,
        cwd=repo_root,
        check=False,
    )
    return result.returncode


def project_python(repo_root: Path) -> str:
    """Return the repository Python when present, else the current interpreter."""

    for relative_path in (".venv/bin/python", "venv/bin/python"):
        if (repo_root / relative_path).is_file():
            return relative_path
    return sys.executable
