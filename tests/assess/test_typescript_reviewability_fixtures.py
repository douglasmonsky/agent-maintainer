"""Fixture-style tests for TypeScript reviewability maturation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from agent_maintainer.assess import reviewability as assessment_reviewability
from agent_maintainer.assess.models import (
    ReviewabilityProviderSummary,
    ReviewabilityReport,
)
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.ecosystems.git_changes import FileChange

BASE_REF = "origin/main"
SOURCE_HEAVY = "source-heavy"
SOURCE_WITHOUT_TEST = "source-without-test"
BROAD_SUPPRESSION = "broad-suppression"
TYPESCRIPT = "typescript"

BUTTON_ADDED = 12
BUTTON_DELETED = 4
BUTTON_TEST_ADDED = 20
BUTTON_TEST_DELETED = 2
ROUTE_TEST_ADDED = 8
ROUTE_TEST_DELETED = 1
LOCK_ADDED = 4
LOCK_DELETED = 2
CONFIG_ADDED = 3
CONFIG_DELETED = 1
LOW_CHANGED_FILES = 4
LOW_SOURCE_FILES = 1
LOW_TEST_FILES = 2
LOW_SOURCE_LINES = 16
LOW_TEST_LINES = 31
NO_BROAD_SUPPRESSIONS = 0

INDEX_ADDED = 80
INDEX_DELETED = 10
SETTINGS_ADDED = 60
SETTINGS_DELETED = 20
CLIENT_ADDED = 50
CLIENT_DELETED = 15
SESSION_ADDED = 40
SESSION_DELETED = 0
PNPM_LOCK_ADDED = 12
PNPM_LOCK_DELETED = 9
HEAVY_CHANGED_FILES = 5
HEAVY_SOURCE_FILES = 4
NO_TEST_FILES = 0
HEAVY_SOURCE_LINES = 275
NO_TEST_LINES = 0
ONE_BROAD_SUPPRESSION = 1

GENERATED_ADDED = 100
IGNORED_ADDED = 100
COVERAGE_ADDED = 20
NO_LINES = 0


# docsync:evidence.start evidence.typescript.reviewability_fixture_tests
def test_ts_source_tests_low_noise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Representative TypeScript source/test changes avoid source-only findings."""
    report = _build_report(
        monkeypatch,
        tmp_path,
        changes=(
            FileChange("src/components/Button.tsx", BUTTON_ADDED, BUTTON_DELETED),
            FileChange(
                "src/components/Button.test.tsx",
                BUTTON_TEST_ADDED,
                BUTTON_TEST_DELETED,
            ),
            FileChange(
                "src/app/__tests__/route.spec.ts",
                ROUTE_TEST_ADDED,
                ROUTE_TEST_DELETED,
            ),
            FileChange("package-lock.json", LOCK_ADDED, LOCK_DELETED),
            FileChange("vite.config.ts", CONFIG_ADDED, CONFIG_DELETED),
        ),
        added_lines={
            "src/components/Button.tsx": (
                "// eslint-disable-next-line no-console",
                "export function Button() {}",
            ),
        },
    )
    summary = _summary(report.provider_summaries, TYPESCRIPT)

    assert summary == ReviewabilityProviderSummary(
        ecosystem=TYPESCRIPT,
        changed_files=LOW_CHANGED_FILES,
        source_files=LOW_SOURCE_FILES,
        test_files=LOW_TEST_FILES,
        source_lines=LOW_SOURCE_LINES,
        test_lines=LOW_TEST_LINES,
        broad_suppressions=NO_BROAD_SUPPRESSIONS,
    )
    assert (TYPESCRIPT, SOURCE_WITHOUT_TEST) not in _finding_keys(report)
    assert (TYPESCRIPT, SOURCE_HEAVY) not in _finding_keys(report)
    assert report.suppressions[0].broad is False


def test_ts_source_only_advisory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Source-only TypeScript fixture produces advisory findings, not failures."""
    report = _build_report(
        monkeypatch,
        tmp_path,
        changes=(
            FileChange("src/pages/index.tsx", INDEX_ADDED, INDEX_DELETED),
            FileChange("src/pages/settings.tsx", SETTINGS_ADDED, SETTINGS_DELETED),
            FileChange("src/lib/client.ts", CLIENT_ADDED, CLIENT_DELETED),
            FileChange("src/lib/session.ts", SESSION_ADDED, SESSION_DELETED),
            FileChange("pnpm-lock.yaml", PNPM_LOCK_ADDED, PNPM_LOCK_DELETED),
        ),
        added_lines={
            "src/pages/index.tsx": (
                "// eslint-disable",
                "export const page = true;",
            ),
        },
    )
    summary = _summary(report.provider_summaries, TYPESCRIPT)

    assert summary == ReviewabilityProviderSummary(
        ecosystem=TYPESCRIPT,
        changed_files=HEAVY_CHANGED_FILES,
        source_files=HEAVY_SOURCE_FILES,
        test_files=NO_TEST_FILES,
        source_lines=HEAVY_SOURCE_LINES,
        test_lines=NO_TEST_LINES,
        broad_suppressions=ONE_BROAD_SUPPRESSION,
    )
    assert {
        (TYPESCRIPT, BROAD_SUPPRESSION),
        (TYPESCRIPT, SOURCE_WITHOUT_TEST),
        (TYPESCRIPT, SOURCE_HEAVY),
    }.issubset(_finding_keys(report))
    assert "Advisory only" in report.advisory_note


def test_ts_generated_ignored_excluded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Generated and ignored TypeScript paths do not inflate source/test signals."""
    report = _build_report(
        monkeypatch,
        tmp_path,
        changes=(
            FileChange("src/__generated__/client.ts", GENERATED_ADDED, NO_LINES),
            FileChange("dist/index.js", IGNORED_ADDED, NO_LINES),
            FileChange("coverage/lcov.info", COVERAGE_ADDED, NO_LINES),
            FileChange("next.config.js", CONFIG_ADDED, CONFIG_DELETED),
        ),
        added_lines={
            "src/__generated__/client.ts": ("// eslint-disable",),
            "dist/index.js": ("// @ts-nocheck",),
        },
    )

    assert not report.provider_summaries
    assert not _finding_keys(report)
    assert not report.suppressions


def _build_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    changes: tuple[FileChange, ...],
    added_lines: dict[str, tuple[str, ...]],
) -> ReviewabilityReport:
    """Build reviewability report with patched TypeScript fixture changes."""
    monkeypatch.setattr(
        assessment_reviewability.git_changes,
        "run_git_numstat",
        _GitNumstatReader(changes),
    )
    monkeypatch.setattr(
        assessment_reviewability,
        "added_lines_by_path",
        _AddedLineReader(added_lines),
    )
    return assessment_reviewability.build_reviewability_report(
        tmp_path,
        replace(MaintainerConfig(), enable_typescript=True),
        base_ref=BASE_REF,
        staged=False,
    )


# docsync:evidence.end evidence.typescript.reviewability_fixture_tests


@dataclass(frozen=True)
class _GitNumstatReader:
    """Fake git numstat reader."""

    changes: tuple[FileChange, ...]

    def __call__(self, base_ref: str, *, staged: bool) -> list[FileChange]:
        """Return configured changed files."""
        assert base_ref == BASE_REF
        assert not staged
        return list(self.changes)


@dataclass(frozen=True)
class _AddedLineReader:
    """Fake added-line reader."""

    added_lines: dict[str, tuple[str, ...]]

    def __call__(self, base_ref: str, *, staged: bool) -> dict[str, tuple[str, ...]]:
        """Return configured added lines."""
        assert base_ref == BASE_REF
        assert not staged
        return self.added_lines


def _summary(
    summaries: tuple[ReviewabilityProviderSummary, ...],
    ecosystem: str,
) -> ReviewabilityProviderSummary:
    """Return summary for one ecosystem."""
    for summary in summaries:
        if summary.ecosystem == ecosystem:
            return summary
    msg = f"missing summary {ecosystem}"
    raise AssertionError(msg)


def _finding_keys(report: ReviewabilityReport) -> set[tuple[str, str]]:
    """Return advisory finding keys from report."""
    return {(item.ecosystem, item.kind) for item in report.advisory_findings}
