"""Tests advisory reviewability assessment."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from agent_maintainer.assess import cli, reporting
from agent_maintainer.assess import reviewability as assessment_reviewability
from agent_maintainer.assess.models import ReviewabilityCount
from agent_maintainer.checks.change_budget import FileChange
from agent_maintainer.config.schema import MaintainerConfig

TOTAL_CHANGED_FILES = 5
CLASSIFIED_FILES = 4


def test_reviewability_groups_provider_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Provider-aware assessment groups changed files without enforcing gates."""
    monkeypatch.setattr(
        assessment_reviewability,
        "run_git_numstat",
        _fake_git_numstat,
    )
    config = replace(MaintainerConfig(), enable_typescript=True, enable_go=True)

    report = assessment_reviewability.build_reviewability_report(
        tmp_path,
        config,
        base_ref="origin/main",
        staged=False,
    )

    assert report.total_changed_files == TOTAL_CHANGED_FILES
    assert report.classified_files == CLASSIFIED_FILES
    assert report.unclassified_files == 1
    assert _count_map(report.by_ecosystem) == {
        "global": 1,
        "go": 1,
        "python": 1,
        "typescript": 1,
    }
    assert "Advisory only" in report.advisory_note


def test_reviewability_cli_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI renders stable JSON for advisory reviewability reports."""
    _write_config(tmp_path)
    monkeypatch.setattr(
        assessment_reviewability,
        "run_git_numstat",
        _fake_git_numstat,
    )

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
    assert status == 0
    assert payload["base_ref"] == "HEAD"
    assert payload["classified_files"] == CLASSIFIED_FILES
    assert {item["key"] for item in payload["by_role"]} >= {"source", "test"}
    assert payload["changes"][0]["ecosystem"] == "python"


def test_reviewability_text_lists_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Text renderer includes grouped counts and changed provider files."""
    monkeypatch.setattr(
        assessment_reviewability,
        "run_git_numstat",
        _fake_git_numstat,
    )
    config = replace(MaintainerConfig(), enable_typescript=True, enable_go=True)
    report = assessment_reviewability.build_reviewability_report(
        tmp_path,
        config,
        base_ref="origin/main",
        staged=False,
    )

    output = reporting.render_reviewability_text(report)

    assert "Reviewability Assessment" in output
    assert "- python: 1" in output
    assert "Changed provider files:" in output
    assert "src/example/app.py: python/source" in output


def test_reviewability_text_no_provider_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Text renderer reports empty groups without special casing callers."""
    monkeypatch.setattr(
        assessment_reviewability,
        "run_git_numstat",
        _fake_unclassified_numstat,
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
