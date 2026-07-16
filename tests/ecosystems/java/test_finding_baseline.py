"""Tests deterministic Java finding debt baselines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.ecosystems.java.baseline import (
    BASELINE_VERSION,
    compare_baseline,
    create_baseline,
    inspect_baseline,
    parse_baseline,
    prune_baseline,
    read_baseline,
    render_baseline,
    write_baseline,
)
from agent_maintainer.ecosystems.java.findings import JavaFinding

SOURCE_COMMIT = "a" * 40
EXPECTED_BASELINE_OCCURRENCES = 4
EXPECTED_PRUNED_ENTRIES = 2
HIGH_COMPLEXITY = 10


def test_baseline_json_is_deterministic_and_versioned() -> None:
    """Equivalent inputs produce stable sorted JSON with provenance."""
    findings = (
        finding("checkstyle", "AvoidStarImport"),
        finding("checkstyle", "AvoidStarImport"),
        finding("pmd", "CyclomaticComplexity", subject="App.run", metric=HIGH_COMPLEXITY),
        finding("pmd", "CyclomaticComplexity", subject="App.run", metric=5),
    )

    baseline = create_baseline(reversed(findings), source_commit=SOURCE_COMMIT)
    rendered = render_baseline(baseline)

    assert rendered == render_baseline(create_baseline(findings, source_commit=SOURCE_COMMIT))
    assert parse_baseline(rendered) == baseline
    assert baseline.version == BASELINE_VERSION
    assert baseline.provenance.source_commit == SOURCE_COMMIT
    summary = inspect_baseline(baseline)
    assert summary.occurrence_count == EXPECTED_BASELINE_OCCURRENCES
    assert summary.numeric_ceiling_count == EXPECTED_PRUNED_ENTRIES


def test_duplicate_occurrences_compare_as_multiset() -> None:
    """Only occurrences beyond the allowed duplicate count are new debt."""
    duplicate = finding("checkstyle", "AvoidStarImport")
    baseline = create_baseline((duplicate, duplicate), source_commit=SOURCE_COMMIT)

    report = compare_baseline(baseline, (duplicate, duplicate, duplicate))

    assert report.new_occurrences == 1
    assert not report.passed


def test_numeric_ceilings_match_largest_remaining_slots() -> None:
    """A removed low-value duplicate does not make the remaining finding regress."""
    low = finding("pmd", "CyclomaticComplexity", subject="App.run", metric=5)
    high = finding("pmd", "CyclomaticComplexity", subject="App.run", metric=HIGH_COMPLEXITY)
    baseline = create_baseline((low, high), source_commit=SOURCE_COMMIT)

    improved = compare_baseline(
        baseline,
        (finding("pmd", "CyclomaticComplexity", subject="App.run", metric=9),),
    )
    regressed = compare_baseline(
        baseline,
        (finding("pmd", "CyclomaticComplexity", subject="App.run", metric=11),),
    )

    assert improved.passed
    assert improved.improved_occurrences == 1
    assert improved.resolved_occurrences == 1
    assert len(regressed.regressions) == 1
    assert regressed.regressions[0].ceiling == HIGH_COMPLEXITY


def test_prune_removes_resolved_debt_and_lowers_ceilings() -> None:
    """Explicit pruning keeps only current counts and improved measurements."""
    retained = finding("checkstyle", "AvoidStarImport")
    removed = finding("checkstyle", "UnusedImports", subject="App.other")
    complexity = finding(
        "pmd",
        "CyclomaticComplexity",
        subject="App.run",
        metric=HIGH_COMPLEXITY,
    )
    baseline = create_baseline(
        (retained, retained, removed, complexity),
        source_commit=SOURCE_COMMIT,
    )
    current = (
        retained,
        finding("pmd", "CyclomaticComplexity", subject="App.run", metric=7),
    )

    pruned = prune_baseline(baseline, current, source_commit="b" * 40)
    summary = inspect_baseline(pruned)

    assert summary.entry_count == EXPECTED_PRUNED_ENTRIES
    assert summary.occurrence_count == EXPECTED_PRUNED_ENTRIES
    assert summary.source_commit == "b" * 40
    assert [entry.metric_ceilings for entry in pruned.entries] == [(), (7,)]


def test_baseline_io_refuses_unreviewed_overwrite(tmp_path: Path) -> None:
    """Writes are deterministic and refuse replacement unless explicit."""
    baseline = create_baseline((finding("spotbugs", "NP_NULL"),), source_commit=SOURCE_COMMIT)
    path = tmp_path / "java-findings.json"

    write_baseline(path, baseline)

    assert read_baseline(path) == baseline
    with pytest.raises(FileExistsError, match="already exists"):
        write_baseline(path, baseline)


def test_baseline_rejects_schema_drift() -> None:
    """Unknown fields fail closed instead of becoming compatibility shims."""
    baseline = create_baseline((finding("spotbugs", "NP_NULL"),), source_commit=SOURCE_COMMIT)
    payload: dict[str, object] = json.loads(render_baseline(baseline))
    payload["legacy"] = True

    with pytest.raises(ValueError, match="unsupported or missing fields"):
        parse_baseline(json.dumps(payload))


def test_baseline_rejects_fingerprint_mismatch() -> None:
    """Stored identity fields cannot diverge from their fingerprint."""
    baseline = create_baseline((finding("spotbugs", "NP_NULL"),), source_commit=SOURCE_COMMIT)
    payload: dict[str, object] = json.loads(render_baseline(baseline))
    raw_entries = payload["entries"]
    assert isinstance(raw_entries, list)
    entries = cast(list[object], raw_entries)
    raw_entry = entries[0]
    assert isinstance(raw_entry, dict)
    entry = cast(dict[str, object], raw_entry)
    entry["rule"] = "NP_DIFFERENT"

    with pytest.raises(ValueError, match="fingerprint must match"):
        parse_baseline(json.dumps(payload))


def test_baseline_rejects_mixed_numeric_identity() -> None:
    """One fingerprint cannot mix measured and unmeasured debt."""
    measured = finding("pmd", "CyclomaticComplexity", metric=7)
    unmeasured = finding("pmd", "CyclomaticComplexity")

    with pytest.raises(ValueError, match="mixes numeric and nonnumeric"):
        create_baseline((measured, unmeasured), source_commit=SOURCE_COMMIT)


def finding(
    tool: str,
    rule: str,
    *,
    subject: str = "example.App",
    metric: int | None = None,
) -> JavaFinding:
    """Return one normalized test finding."""
    return JavaFinding(tool, rule, "src/main/java/example/App.java", subject, rule, metric=metric)
