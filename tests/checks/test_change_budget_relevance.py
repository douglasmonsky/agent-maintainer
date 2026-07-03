"""Tests source/test relevance change-budget helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.checks import change_budget as check_change_budget
from agent_maintainer.checks import test_relevance
from agent_maintainer.core.config import MaintainerConfig


def test_change_budget_allows_docsync_evidence_marker_only_source_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """DocSync trace marker-only source edits do not require fake source tests."""

    args = check_change_budget.parse_args([])
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True)
    completed = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout=(
            "diff --git a/src/pkg/tool.py b/src/pkg/tool.py\n"
            "@@ -1,0 +1,3 @@\n"
            "+# docsync:evidence.start evidence.docs.trace\n"
            "+\n"
            "+# docsync:evidence.end evidence.docs.trace\n"
        ),
        stderr="",
    )
    monkeypatch.setattr(test_relevance.subprocess, "run", lambda *args, **_kwargs: completed)

    warnings = test_relevance.warnings_for_changes(
        args,
        config,
        [check_change_budget.FileChange("src/pkg/tool.py", 2, 0)],
        [check_change_budget.FileChange("tests/docsync/test_readme_trace.py", 1, 0)],
        tmp_path,
    )

    assert warnings == []


def test_change_budget_keeps_warning_for_real_source_edits_near_docsync_markers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """DocSync marker skip does not hide behavior edits in the same source file."""

    args = check_change_budget.parse_args([])
    config = MaintainerConfig(source_roots=("src",), test_roots=("tests",), require_tests=True)
    completed = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout=(
            "diff --git a/src/pkg/tool.py b/src/pkg/tool.py\n"
            "@@ -1,0 +1,2 @@\n"
            "+# docsync:evidence.start evidence.docs.trace\n"
            "+VALUE = 1\n"
        ),
        stderr="",
    )
    monkeypatch.setattr(test_relevance.subprocess, "run", lambda *args, **_kwargs: completed)

    warnings = test_relevance.warnings_for_changes(
        args,
        config,
        [check_change_budget.FileChange("src/pkg/tool.py", 2, 0)],
        [check_change_budget.FileChange("tests/docsync/test_readme_trace.py", 1, 0)],
        tmp_path,
    )

    assert len(warnings) == 1
    assert warnings[0].startswith(
        "A test file changed, but no likely relevant test changed for modified source."
    )
