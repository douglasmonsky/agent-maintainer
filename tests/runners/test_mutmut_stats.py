"""Tests for Mutmut result statistics and ratchets."""

from __future__ import annotations

import json
from pathlib import Path

from agent_maintainer.runners import mutmut_stats

KILLED_COUNT = 7
SURVIVED_COUNT = 2
TOTAL_COUNT = 10
NO_TESTS_COUNT = 1
SUSPICIOUS_COUNT = 1
TIMEOUT_COUNT = 1
MAX_SURVIVORS = 1
MIN_SCORE = 75
EXPECTED_SCORE = 70.0


def test_read_stats_parses_exported_cicd_stats(tmp_path: Path) -> None:
    """Exported Mutmut CI stats become typed mutation statistics."""

    stats_path = tmp_path / "mutmut-cicd-stats.json"
    stats_path.write_text(
        json.dumps(
            {
                "killed": KILLED_COUNT,
                "survived": SURVIVED_COUNT,
                "total": TOTAL_COUNT,
                "no_tests": NO_TESTS_COUNT,
                "skipped": 0,
                "suspicious": 0,
                "timeout": 0,
                "check_was_interrupted_by_user": 0,
                "segfault": 0,
            }
        ),
        encoding="utf-8",
    )

    stats = mutmut_stats.read_stats(stats_path)

    assert stats.killed == KILLED_COUNT
    assert stats.survived == SURVIVED_COUNT
    assert stats.total == TOTAL_COUNT
    assert stats.score == EXPECTED_SCORE


def test_ratchet_issues_reports_budget_failures() -> None:
    """Configured result budgets fail on survivor, timeout, and score regressions."""

    stats = mutmut_stats.MutmutStats(
        killed=KILLED_COUNT,
        survived=SURVIVED_COUNT,
        total=TOTAL_COUNT,
        no_tests=0,
        skipped=0,
        suspicious=SUSPICIOUS_COUNT,
        timeout=TIMEOUT_COUNT,
        check_was_interrupted_by_user=0,
        segfault=0,
    )
    ratchet = mutmut_stats.MutmutRatchet(
        enabled=True,
        max_survivors=MAX_SURVIVORS,
        max_suspicious=0,
        max_timeouts=0,
        min_score=MIN_SCORE,
    )

    assert mutmut_stats.ratchet_issues(stats, ratchet) == (
        "mutmut survived mutants 2 above allowed 1",
        "mutmut suspicious mutants 1 above allowed 0",
        "mutmut timeout mutants 1 above allowed 0",
        "mutmut score 70.00% below required 75%",
    )


def test_ratchet_disabled_has_no_issues() -> None:
    """Disabled result ratchets do not constrain Mutmut output."""

    stats = mutmut_stats.MutmutStats(
        killed=0,
        survived=99,
        total=99,
        no_tests=0,
        skipped=0,
        suspicious=0,
        timeout=0,
        check_was_interrupted_by_user=0,
        segfault=0,
    )

    assert mutmut_stats.ratchet_issues(stats, mutmut_stats.MutmutRatchet()) == ()
