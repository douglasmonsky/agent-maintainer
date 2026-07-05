"""Architecture boundaries for experimental downstream packages."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+agent_task_broker\b", re.MULTILINE)
SCAN_PREFIXES = (
    "src/",
    "tests/",
    ".codex/hooks/",
    ".claude/hooks/",
)
IGNORED_PREFIXES = (
    "experiments/agent-task-broker/",
    "tests/architecture/test_experiment_boundaries.py",
)


def test_main_repo_does_not_import_agent_task_broker() -> None:
    """Keep downstream broker experiment out of Agent Maintainer core."""
    offenders = [
        path
        for path in tracked_python_files()
        if FORBIDDEN_IMPORT_RE.search((ROOT / path).read_text(encoding="utf-8"))
    ]

    assert offenders == []


def tracked_python_files() -> list[str]:
    """Return tracked Python files in main repo surfaces."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [
        path
        for path in result.stdout.splitlines()
        if path.startswith(SCAN_PREFIXES) and not path.startswith(IGNORED_PREFIXES)
    ]
