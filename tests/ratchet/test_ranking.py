"""Tests ratchet target ranking."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_maintainer.ratchet import cli as ratchet_cli
from agent_maintainer.ratchet import ranking
from agent_maintainer.ratchet.baseline import write_baseline
from agent_maintainer.ratchet.models import (
    BaselineProvenance,
    RatchetBaseline,
    RatchetFinding,
    RatchetStatusEntry,
    RatchetStatusReport,
)
from agent_maintainer.ratchet.ranking import ranked_targets
from tests.support.callbacks import constant_callback


def test_ranked_targets_explain_why_and_first_command() -> None:
    """Ranking promotes changed new findings and emits first context command."""

    report = RatchetStatusReport(
        entries=(
            entry("unchanged", "src/legacy/old.py", value=800),
            entry("new", "src/legacy/big_service.py", value=1200),
        ),
        stale_reasons=(),
    )

    targets = ranked_targets(
        report,
        changed_path_set={"src/legacy/big_service.py"},
        limit=5,
    )

    assert targets[0].path == "src/legacy/big_service.py"
    assert targets[0].rank == 1
    assert targets[0].why == "new file-length violation in current diff"
    assert (
        targets[0].first_command
        == "python -m agent_maintainer context file src/legacy/big_service.py --outline"
    )


def test_ranked_targets_respect_limit() -> None:
    """Ranking respects configured or CLI limit."""

    report = RatchetStatusReport(
        entries=(
            entry("new", "src/one.py", value=1),
            entry("worsened", "src/two.py", value=2),
        ),
        stale_reasons=(),
    )

    assert len(ranked_targets(report, changed_path_set=set(), limit=1)) == 1


def test_changed_paths_rejects_git_option_injection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An option-like revision is refused before Git can write outside the repo."""

    outside = tmp_path / "outside.diff"
    outside.write_text("unchanged\n", encoding="utf-8")

    def forbidden_run(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"unsafe revision reached subprocess: {args!r} {kwargs!r}")

    monkeypatch.setattr(ranking.subprocess, "run", forbidden_run)

    assert ranking.changed_paths(f"--output={outside}") == set()
    assert outside.read_text(encoding="utf-8") == "unchanged\n"


def test_ratchet_next_outputs_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI next command renders target text."""

    baseline_path = tmp_path / "ratchet.json"
    write_baseline(baseline_path, baseline(), force=True)
    monkeypatch.setattr(
        ratchet_cli,
        "changed_paths",
        constant_callback({"src/current.py"}),
    )
    monkeypatch.setattr(ratchet_cli, "status_report", constant_callback(report()))

    assert ratchet_cli.main(["next", "--baseline", str(baseline_path), "--limit", "1"]) == 0

    output = capsys.readouterr().out
    assert "Top ratchet targets:" in output
    assert "Why target:" in output
    assert "First command:" in output


def test_ratchet_next_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI next command renders JSON."""

    baseline_path = tmp_path / "ratchet.json"
    write_baseline(baseline_path, baseline(), force=True)
    monkeypatch.setattr(
        ratchet_cli,
        "changed_paths",
        constant_callback({"src/current.py"}),
    )
    monkeypatch.setattr(ratchet_cli, "status_report", constant_callback(report()))

    assert (
        ratchet_cli.main(
            ["next", "--baseline", str(baseline_path), "--limit", "1", "--format", "json"],
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["targets"][0]["path"] == "src/current.py"


def test_ratchet_next_uses_configured_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI next uses configured target count when no limit passed."""

    baseline_path = tmp_path / "ratchet.json"
    write_baseline(baseline_path, baseline(), force=True)
    monkeypatch.setattr(
        ratchet_cli,
        "changed_paths",
        constant_callback(set[str]()),
    )
    monkeypatch.setattr(
        ratchet_cli,
        "status_report",
        constant_callback(two_target_report()),
    )
    monkeypatch.setattr(
        ratchet_cli,
        "load_config",
        constant_callback(SimpleNamespace(ratchet_target_limit=1)),
    )

    assert ratchet_cli.main(["next", "--baseline", str(baseline_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert len(payload["targets"]) == 1


def test_ratchet_next_missing_baseline_fails(tmp_path: Path) -> None:
    """CLI next returns nonzero for missing baseline."""

    assert ratchet_cli.main(["next", "--baseline", str(tmp_path / "missing.json")]) == 1


def baseline() -> RatchetBaseline:
    """Return baseline whose finding remains current in test repository."""

    finding = ratchet_finding("src/current.py", value=1200)
    return RatchetBaseline(
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
        findings=(finding,),
    )


def report() -> RatchetStatusReport:
    """Return deterministic status report for CLI rendering tests."""

    return RatchetStatusReport(
        entries=(entry("new", "src/current.py", value=1200),),
        stale_reasons=(),
    )


def two_target_report() -> RatchetStatusReport:
    """Return two deterministic targets for limit tests."""

    return RatchetStatusReport(
        entries=(
            entry("new", "src/current.py", value=1200),
            entry("new", "src/other.py", value=900),
        ),
        stale_reasons=(),
    )


def entry(status: str, path: str, *, value: int) -> RatchetStatusEntry:
    """Return one status entry."""

    finding = ratchet_finding(path, value=value)
    return RatchetStatusEntry(status=status, finding=finding, baseline=finding)


def ratchet_finding(path: str, *, value: int) -> RatchetFinding:
    """Return one file-length finding."""

    return RatchetFinding(
        check="file-length",
        identity=f"{path}:source-lines",
        path=path,
        line=None,
        severity="fail",
        metric="source-lines",
        value=value,
        threshold=600,
        message=f"{path} is oversized",
        fingerprint=path,
    )
