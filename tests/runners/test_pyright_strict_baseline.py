"""Tests for the versioned strict-Pyright debt baseline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_maintainer.runners import pyright_strict_baseline as strict_baseline

PYRIGHT_VERSION = "1.1.410"
SCOPE_SHA256 = "a" * 64
OTHER_SCOPE_SHA256 = "b" * 64
BASELINE_SCHEMA_VERSION = 2
SAMPLE_TOTAL = 3
PAIR_BASELINE = 2


def test_v2_baseline_round_trips_review_summaries(tmp_path: Path) -> None:
    """The committed shape is strict, reviewable, and internally consistent."""

    current = stats(
        {
            "src/a.py": {"reportUnknownMemberType": 2},
            "tests/test_a.py": {"reportPrivateUsage": 1},
        },
    )
    path = tmp_path / "baseline.json"
    path.write_text(
        strict_baseline.baseline_json(current, note="Reviewed CS-07 debt."),
        encoding="utf-8",
    )

    loaded = strict_baseline.load_baseline(path)

    assert loaded == baseline(current.pairs)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == BASELINE_SCHEMA_VERSION
    assert payload["total_errors"] == SAMPLE_TOTAL
    assert payload["by_rule"] == {
        "reportPrivateUsage": 1,
        "reportUnknownMemberType": 2,
    }
    assert payload["note"] == "Reviewed CS-07 debt."


@pytest.mark.parametrize(
    "payload",
    (
        {
            "version": 1,
            "total_errors": 1,
            "by_rule": {"reportUnknownMemberType": 1},
        },
        {
            "schema_version": 2,
            "tool": {
                "name": "pyright",
                "version": PYRIGHT_VERSION,
                "type_checking_mode": "strict",
                "scope_sha256": SCOPE_SHA256,
            },
            "total_errors": 0,
            "by_rule": {},
            "pairs": {"src/a.py": {"reportUnknownMemberType": 0}},
        },
        {
            "schema_version": 2,
            "tool": {
                "name": "pyright",
                "version": PYRIGHT_VERSION,
                "type_checking_mode": "strict",
                "scope_sha256": SCOPE_SHA256,
            },
            "total_errors": 2,
            "by_rule": {"reportUnknownMemberType": 1},
            "pairs": {"src/a.py": {"reportUnknownMemberType": 1}},
        },
        {
            "schema_version": 2,
            "tool": {
                "name": "pyright",
                "version": PYRIGHT_VERSION,
                "type_checking_mode": "strict",
                "scope_sha256": SCOPE_SHA256,
            },
            "total_errors": 1,
            "by_rule": {"reportUnknownMemberType": 1},
            "pairs": {"../outside.py": {"reportUnknownMemberType": 1}},
        },
    ),
)
def test_load_baseline_rejects_v1_and_inconsistent_v2(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    """Migration and hand-edited baseline mistakes fail closed."""

    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert strict_baseline.load_baseline(path) is None


def test_compare_fails_new_pair_even_when_total_drops() -> None:
    """Moving debt to a new rule or file cannot substitute for resolved debt."""

    result = strict_baseline.compare_stats(
        stats(
            {
                "src/a.py": {"reportUnknownMemberType": 1},
                "src/b.py": {"reportUnknownArgumentType": 1},
            },
        ),
        baseline({"src/a.py": {"reportUnknownMemberType": 3}}),
    )

    assert result.passed is False
    assert result.regressions == (
        strict_baseline.StrictRegression(
            file="src/b.py",
            rule="reportUnknownArgumentType",
            current_count=1,
            baseline_count=0,
        ),
    )


def test_compare_fails_increased_pair_despite_lower_total() -> None:
    """A file/rule allowance is independently monotonic."""

    result = strict_baseline.compare_stats(
        stats({"src/a.py": {"reportUnknownMemberType": 3}}),
        baseline(
            {
                "src/a.py": {"reportUnknownMemberType": 2},
                "src/b.py": {"reportUnknownArgumentType": 4},
            },
        ),
    )

    assert result.passed is False
    assert result.current.total_errors < result.baseline.total_errors
    assert result.regressions[0].baseline_count == PAIR_BASELINE


def test_compare_allows_resolved_pairs_to_disappear() -> None:
    """Removing diagnostics lowers debt without requiring empty placeholders."""

    result = strict_baseline.compare_stats(
        stats({"src/a.py": {"reportUnknownMemberType": 1}}),
        baseline(
            {
                "src/a.py": {"reportUnknownMemberType": 2},
                "src/b.py": {"reportUnknownArgumentType": 1},
            },
        ),
    )

    assert result.passed is True
    assert result.regressions == ()
    assert result.compatibility_errors == ()


@pytest.mark.parametrize(
    ("pyright_version", "scope_sha256", "expected"),
    (
        ("1.1.411", SCOPE_SHA256, "Pyright version changed"),
        (PYRIGHT_VERSION, OTHER_SCOPE_SHA256, "strict analysis scope changed"),
    ),
)
def test_compare_rejects_tool_or_scope_mismatch(
    pyright_version: str,
    scope_sha256: str,
    expected: str,
) -> None:
    """Tool and scope changes require an intentional baseline migration."""

    result = strict_baseline.compare_stats(
        stats({}, pyright_version=pyright_version, scope_sha256=scope_sha256),
        baseline({}),
    )

    assert result.passed is False
    assert any(expected in error for error in result.compatibility_errors)


def test_format_result_names_pair_regression() -> None:
    """Failure output points to the exact allowance that regressed."""

    result = strict_baseline.compare_stats(
        stats({"src/a.py": {"reportUnknownMemberType": 2}}),
        baseline({"src/a.py": {"reportUnknownMemberType": 1}}),
    )

    summary = strict_baseline.format_result(result)

    assert "pyright strict ratchet failed: 2 errors" in summary
    assert "src/a.py :: reportUnknownMemberType: 2 (baseline 1, +1)" in summary
    assert "Repair:" in summary


def stats(
    pairs: strict_baseline.PairCounts,
    *,
    pyright_version: str = PYRIGHT_VERSION,
    scope_sha256: str = SCOPE_SHA256,
) -> strict_baseline.StrictPyrightStats:
    """Return current strict stats for one test."""

    return strict_baseline.StrictPyrightStats(
        files_analyzed=2,
        pyright_version=pyright_version,
        scope_sha256=scope_sha256,
        pairs=pairs,
    )


def baseline(pairs: strict_baseline.PairCounts) -> strict_baseline.StrictBaseline:
    """Return compatible baseline for one test."""

    return strict_baseline.StrictBaseline(
        pyright_version=PYRIGHT_VERSION,
        scope_sha256=SCOPE_SHA256,
        pairs=pairs,
    )
