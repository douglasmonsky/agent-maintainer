"""Tests for advisory reviewability assessment."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agent_maintainer.assess import cli, reporting
from agent_maintainer.assess import reviewability as assessment_reviewability
from agent_maintainer.assess.models import ReviewabilityCount, ReviewabilityReport
from agent_maintainer.checks.change_budget import FileChange
from agent_maintainer.config.schema import MaintainerConfig

TOTAL_CHANGED_FILES = 5
CLASSIFIED_FILES = 4
UNCLASSIFIED_FILES = 1
SUPPRESSION_FINDINGS = 2


def test_reviewability_groups_provider_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Provider-aware assessment groups changed files without enforcing gates."""
    _patch_changed_files(monkeypatch)
    config = replace(MaintainerConfig(), enable_typescript=True, enable_go=True)

    report = assessment_reviewability.build_reviewability_report(
        tmp_path,
        config,
        base_ref="origin/main",
        staged=False,
    )

    _assert_report_counts(report)
    _assert_report_suppressions(report)
    assert "Advisory only" in report.advisory_note


def test_reviewability_cli_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI renders stable JSON advisory reviewability reports."""
    _write_config(tmp_path)
    _patch_changed_files(monkeypatch)

    status = cli.main(
        [
            "reviewability",
            "--target",
            str(tmp_path),
            "--base-ref",
            "HEAD",
            "--json",
        ],
    )

    payload = json.loads(capsys.readouterr().out)
    _assert_json_summary(payload, status)
    _assert_json_suppressions(payload)


def test_reviewability_text_lists_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Text renderer includes grouped counts and changed provider files."""
    _patch_changed_files(monkeypatch)
    config = replace(MaintainerConfig(), enable_typescript=True, enable_go=True)
    report = assessment_reviewability.build_reviewability_report(
        tmp_path,
        config,
        base_ref="origin/main",
        staged=False,
    )

    output = reporting.render_reviewability_text(report)

    _assert_text_output(output)


def test_reviewability_text_no_provider_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Text renderer reports empty groups without special casing callers."""
    monkeypatch.setattr(
        assessment_reviewability.change_budget,
        "run_git_numstat",
        _fake_unclassified_numstat,
    )
    monkeypatch.setattr(
        assessment_reviewability,
        "added_lines_by_path",
        _fake_no_added_lines,
    )
    report = assessment_reviewability.build_reviewability_report(
        tmp_path,
        MaintainerConfig(),
        base_ref="origin/main",
        staged=False,
    )
    output = reporting.render_reviewability_text(report)

    assert "- None" in output
    assert "Changed provider files:" not in output


def _patch_changed_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch git-backed change discovery for deterministic tests."""
    monkeypatch.setattr(
        assessment_reviewability.change_budget,
        "run_git_numstat",
        _fake_git_numstat,
    )
    monkeypatch.setattr(
        assessment_reviewability,
        "added_lines_by_path",
        _fake_added_lines,
    )


def _assert_report_counts(report: ReviewabilityReport) -> None:
    """Assert stable report grouping counts."""
    assert report.total_changed_files == TOTAL_CHANGED_FILES
    assert report.classified_files == CLASSIFIED_FILES
    assert report.unclassified_files == UNCLASSIFIED_FILES
    assert _count_map(report.by_ecosystem) == {
        "global": 1,
        "go": 1,
        "python": 1,
        "typescript": 1,
    }


def _assert_report_suppressions(report: ReviewabilityReport) -> None:
    """Assert stable advisory suppression summary."""
    assert len(report.suppressions) == SUPPRESSION_FINDINGS
    assert report.broad_suppressions == SUPPRESSION_FINDINGS


def _assert_json_summary(payload: dict[str, Any], status: int) -> None:
    """Assert stable JSON top-level summary."""
    assert status == 0
    assert payload["base_ref"] == "HEAD"
    assert payload["classified_files"] == CLASSIFIED_FILES
    assert payload["broad_suppressions"] == SUPPRESSION_FINDINGS


def _assert_json_suppressions(payload: dict[str, Any]) -> None:
    """Assert stable JSON suppression and role payload."""
    assert {item["kind"] for item in payload["suppressions"]} == {
        "eslint-disable",
        "nolint",
    }
    assert {item["key"] for item in payload["by_role"]} >= {"source", "test"}
    assert payload["changes"][0]["ecosystem"] == "python"


def _assert_text_output(output: str) -> None:
    """Assert stable text report lines."""
    assert "Reviewability Assessment" in output
    assert "- python: 1" in output
    assert "- Advisory suppressions: 2" in output
    assert "Advisory suppressions:" in output
    assert "src/example/app.py: python/source" in output


def _fake_git_numstat(base_ref: str, *, staged: bool) -> list[FileChange]:
    """Return mixed changed files for advisory classification tests."""
    assert base_ref in {"HEAD", "origin/main"}
    assert not staged
    return [
        FileChange("src/example/app.py", 3, 1),
        FileChange("src/web/app.ts", 5, 2),
        FileChange("internal/server/handler_test.go", 7, 0),
        FileChange("pyproject.toml", 1, 0),
        FileChange("notes/random.log", 1, 1),
    ]


def _fake_added_lines(base_ref: str, *, staged: bool) -> dict[str, tuple[str, ...]]:
    """Return added lines with advisory suppressions."""
    assert base_ref in {"HEAD", "origin/main"}
    assert not staged
    return {
        "src/web/app.ts": ("// eslint-disable", "export const value = 1;"),
        "internal/server/handler_test.go": ("//nolint", "func TestThing() {}"),
    }


def _fake_no_added_lines(
    base_ref: str,
    *,
    staged: bool,
) -> dict[str, tuple[str, ...]]:
    """Return no added lines for empty advisory suppression reports."""
    assert base_ref == "origin/main"
    assert not staged
    return {}


def _fake_unclassified_numstat(base_ref: str, *, staged: bool) -> list[FileChange]:
    """Return one unclassified changed file."""
    assert base_ref == "origin/main"
    assert not staged
    return [FileChange("notes/random.log", 1, 1)]


def _write_config(root: Path) -> None:
    """Write config enabling experimental providers."""
    root.joinpath("pyproject.toml").write_text(
        """
[tool.agent_maintainer]
enable_typescript = true
enable_go = true
""".strip(),
        encoding="utf-8",
    )


def _count_map(counts: tuple[ReviewabilityCount, ...]) -> dict[str, int]:
    """Return count mapping for assertions."""
    return {item.key: item.count for item in counts}
