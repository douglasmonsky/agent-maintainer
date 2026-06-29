"""Tests ratchet status comparison."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.ratchet import status as ratchet_status
from agent_maintainer.ratchet.models import (
    BaselineProvenance,
    RatchetBaseline,
    RatchetFinding,
)
from agent_maintainer.ratchet.status import compare_findings, stale_reasons


def test_status_categories_include_new_worsened_improved_resolved() -> None:
    """Finding comparison returns all ratchet status categories."""

    baseline = (
        finding("unchanged", 3),
        finding("worsened", 3),
        finding("improved", 3),
        finding("resolved", 3),
    )
    current = (
        finding("unchanged", 3),
        finding("worsened", 4),
        finding("improved", 2),
        finding("new", 1),
    )

    statuses = {
        entry.finding.identity: entry.status for entry in compare_findings(baseline, current)
    }

    assert statuses == {
        "unchanged": "unchanged",
        "worsened": "worsened",
        "improved": "improved",
        "new": "new",
        "resolved": "resolved",
    }


def test_stale_reasons_include_deleted_dirty_mismatch_and_resolved(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Stale detection reports basic baseline drift."""

    monkeypatch.chdir(tmp_path)
    baseline = RatchetBaseline(
        provenance=BaselineProvenance(
            version=1,
            created_at="2026-06-29T00:00:00+00:00",
            created_by="agent-maintainer",
            base_ref="origin/main",
            repo_commit="abc123",
            dirty_state=True,
            mode="legacy-ratchet",
            checks=("file-length",),
            notes="",
        ),
        findings=(finding("src/deleted.py", 10),),
    )

    reasons = stale_reasons(baseline, (), base_ref="HEAD")

    assert "baseline was created from a dirty worktree" in reasons
    assert "baseline base ref 'origin/main' differs from 'HEAD'" in reasons
    assert "baseline path no longer exists: src/deleted.py" in reasons
    assert "baseline finding is no longer current: src/deleted.py" in reasons


def test_status_report_uses_current_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status report compares baseline with collected current findings."""

    baseline = RatchetBaseline(
        provenance=BaselineProvenance(
            version=1,
            created_at="2026-06-29T00:00:00+00:00",
            created_by="agent-maintainer",
            base_ref="HEAD",
            repo_commit="abc123",
            dirty_state=False,
            mode="legacy-ratchet",
            checks=("file-length",),
            notes="",
        ),
        findings=(finding("tracked.py", 2),),
    )
    monkeypatch.setattr(
        ratchet_status,
        "current_findings",
        lambda checks: (finding("tracked.py", 3),),
    )

    report = ratchet_status.status_report(baseline, base_ref="HEAD")

    assert report.counts()["worsened"] == 1


def test_model_json_round_trip() -> None:
    """Baseline and report models serialize to stable dictionaries."""

    baseline = RatchetBaseline(
        provenance=provenance(),
        findings=(finding("tracked.py", 2),),
    )

    restored = RatchetBaseline.from_dict(baseline.to_dict())
    report = ratchet_status.RatchetStatusReport(
        entries=(
            ratchet_status.RatchetStatusEntry(
                status="new",
                finding=finding("new.py", 3),
                baseline=None,
            ),
        ),
        stale_reasons=("stale",),
    )

    assert restored == baseline
    assert report.to_dict()["counts"]["new"] == 1
    assert report.to_dict()["entries"][0]["baseline"] is None


def test_non_numeric_values_are_unchanged() -> None:
    """Non-numeric ratchet values compare as unchanged."""

    baseline = (finding("text", "old"),)
    current = (finding("text", "new"),)

    entries = compare_findings(baseline, current)

    assert entries[0].status == "unchanged"


def provenance() -> BaselineProvenance:
    """Return test baseline provenance."""

    return BaselineProvenance(
        version=1,
        created_at="2026-06-29T00:00:00+00:00",
        created_by="agent-maintainer",
        base_ref="HEAD",
        repo_commit="abc123",
        dirty_state=False,
        mode="legacy-ratchet",
        checks=("file-length",),
        notes="",
    )


def finding(identity: str, value: int | str) -> RatchetFinding:
    """Return a test finding."""

    return RatchetFinding(
        check="file-length",
        identity=identity,
        path=identity,
        line=None,
        severity="fail",
        metric="source-lines",
        value=value,
        threshold=2,
        message=f"{identity} is oversized",
        fingerprint=identity,
    )
