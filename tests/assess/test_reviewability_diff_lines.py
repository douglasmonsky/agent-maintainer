"""Tests for advisory reviewability diff-line extraction."""

from __future__ import annotations

import subprocess

import pytest

from agent_maintainer.assess import reviewability as assessment_reviewability

BASE_REF = "origin/main"


def test_added_lines_by_path_parses_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Added line extraction skips copied paths and patch headers."""
    monkeypatch.setattr(
        assessment_reviewability.subprocess,
        "run",
        _fake_diff_run,
    )
    monkeypatch.setattr(
        assessment_reviewability.suppression_budget,
        "copied_destination_paths",
        _fake_copied_destinations,
    )

    added_lines = assessment_reviewability.added_lines_by_path(
        BASE_REF,
        staged=False,
    )

    assert added_lines == {"src/web/app.ts": ("// eslint-disable",)}


def test_added_lines_by_path_reports_git_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Added line extraction reports git diff failures with context."""
    monkeypatch.setattr(
        assessment_reviewability.subprocess,
        "run",
        _fake_failed_diff_run,
    )

    with pytest.raises(RuntimeError, match="fatal diff"):
        assessment_reviewability.added_lines_by_path(BASE_REF, staged=False)


def _fake_diff_run(
    command: list[str],
    *,
    text: bool,
    capture_output: bool,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Return git diff output with one copied destination."""
    assert text
    assert capture_output
    assert check
    return subprocess.CompletedProcess(
        command,
        0,
        stdout=(
            "diff --git a/src/web/app.ts b/src/web/app.ts\n"
            "+++ b/src/web/app.ts\n"
            "+// eslint-disable\n"
            "diff --git a/src/web/copied.ts b/src/web/copied.ts\n"
            "+++ b/src/web/copied.ts\n"
            "+// eslint-disable\n"
        ),
        stderr="",
    )


def _fake_failed_diff_run(
    command: list[str],
    *,
    text: bool,
    capture_output: bool,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Raise git diff failure for added-line extraction."""
    assert text
    assert capture_output
    assert check
    raise subprocess.CalledProcessError(1, command, stderr="fatal diff")


def _fake_copied_destinations(base_ref: str, *, staged: bool) -> frozenset[str]:
    """Return copied path excluded from advisory line parsing."""
    assert base_ref == BASE_REF
    assert not staged
    return frozenset(("src/web/copied.ts",))
