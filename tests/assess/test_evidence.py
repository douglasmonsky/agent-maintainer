"""Tests bounded repository evidence collection."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

from agent_maintainer.assess.evidence import collect_evidence

SCAN_LIMIT = 2
WRITTEN_FILES = 4
TRACKED_PYTHON_FILES = 1


def test_collect_evidence_caps_filesystem_walk(tmp_path: Path) -> None:
    """Filesystem fallback reports truncation instead of unbounded walking."""

    for index in range(WRITTEN_FILES):
        (tmp_path / f"module_{index}.py").write_text("value = 1\n", encoding="utf-8")

    evidence = collect_evidence(tmp_path, max_files=SCAN_LIMIT)

    assert evidence.scan_source == "filesystem-walk"
    assert evidence.scan_truncated is True
    assert evidence.scanned_files == SCAN_LIMIT
    assert evidence.python_files == SCAN_LIMIT


def test_collect_evidence_prefers_git(tmp_path: Path) -> None:
    """Git repos use tracked files instead of every file on disk."""

    git = shutil.which("git") or "git"
    subprocess.run([git, "init"], cwd=tmp_path, check=True, capture_output=True)  # nosec B603
    (tmp_path / "tracked.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("value = 2\n", encoding="utf-8")
    subprocess.run(  # nosec B603
        [git, "add", "tracked.py"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    evidence = collect_evidence(tmp_path)

    assert evidence.scan_source == "git-ls-files"
    assert evidence.python_files == TRACKED_PYTHON_FILES


def test_collect_evidence_reads_package_scripts(tmp_path: Path) -> None:
    """Root package.json script names are setup-advisor evidence."""
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "typecheck": "tsc --noEmit",
                    "test": "vitest run",
                    "lint": "eslint .",
                },
            },
        ),
        encoding="utf-8",
    )

    evidence = collect_evidence(tmp_path)

    assert evidence.has_package_json is True
    assert evidence.package_scripts == ("lint", "test", "typecheck")
