"""Tests advisory provider reviewability summaries."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agent_maintainer.assess import reporting
from agent_maintainer.assess import reviewability as assessment_reviewability
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.git_changes import FileChange

BASE_REF = "origin/main"
TYPESCRIPT = "typescript"
SOURCE_WITHOUT_TEST = "source-without-test"
BROAD_SUPPRESSION = "broad-suppression"
TYPESCRIPT_SOURCE_LINES = 7


# docsync:evidence.start evidence.multi_ecosystem_reviewability.advisory_suppression_tests
def test_provider_summaries_and_findings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """TypeScript gets source/test findings without unsupported ecosystem noise."""
    report = _build_report(monkeypatch, tmp_path)

    assert _summary_map(report.provider_summaries) == {
        TYPESCRIPT: (2, 1, 0, TYPESCRIPT_SOURCE_LINES, 0, 1),
    }
    assert {(item.ecosystem, item.kind) for item in report.advisory_findings} == {
        (TYPESCRIPT, BROAD_SUPPRESSION),
        (TYPESCRIPT, SOURCE_WITHOUT_TEST),
    }


def test_json_and_text_render_advisories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Advisory summaries render in JSON and text output."""
    report = _build_report(monkeypatch, tmp_path)
    payload = json.loads(reporting.render_json(report))
    text = reporting.render_reviewability_text(report)

    assert payload["provider_summaries"][0]["ecosystem"] == TYPESCRIPT
    assert payload["advisory_findings"][0]["kind"] == BROAD_SUPPRESSION
    assert "Provider summaries:" in text
    assert "Advisory findings:" in text


# docsync:evidence.end evidence.multi_ecosystem_reviewability.advisory_suppression_tests


def _build_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Any:
    """Build advisory report against deterministic mixed fixture changes."""
    monkeypatch.setattr(
        assessment_reviewability.git_changes,
        "run_git_numstat",
        _fake_git_numstat,
    )
    monkeypatch.setattr(
        assessment_reviewability,
        "added_lines_by_path",
        _fake_added_lines,
    )
    config = replace(MaintainerConfig(), enable_typescript=True)
    return assessment_reviewability.build_reviewability_report(
        tmp_path,
        config,
        base_ref=BASE_REF,
        staged=False,
    )


def _summary_map(summaries: tuple[Any, ...]) -> dict[str, tuple[int, ...]]:
    """Return compact summary tuple map."""
    return {
        item.ecosystem: (
            item.changed_files,
            item.source_files,
            item.test_files,
            item.source_lines,
            item.test_lines,
            item.broad_suppressions,
        )
        for item in summaries
    }


def _fake_git_numstat(base_ref: str, *, staged: bool) -> list[FileChange]:
    """Return TypeScript and unsupported ecosystem fixture changes."""
    assert base_ref == BASE_REF
    assert not staged
    return [
        FileChange("src/web/app.ts", 5, 2),
        FileChange("package-lock.json", 5, 1),
        FileChange("native/app/main.rs", 8, 1),
        FileChange("Cargo.lock", 2, 1),
    ]


def _fake_added_lines(
    base_ref: str,
    *,
    staged: bool,
) -> dict[str, tuple[str, ...]]:
    """Return broad TypeScript and unsupported suppression lines."""
    assert base_ref == BASE_REF
    assert not staged
    return {
        "src/web/app.ts": ("// eslint-disable", "export const value = 1;"),
        "native/app/main.rs": ("#[allow(dead_code)]", "fn main() {}"),
    }
