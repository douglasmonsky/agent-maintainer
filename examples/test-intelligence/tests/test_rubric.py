"""Tests for test-intelligence scoring fixture."""

from __future__ import annotations

from scoring.rubric import clamp_score, mastery_band

MAX_SCORE = 10
TOO_HIGH_SCORE = 12


def test_clamp_score_rejects_values_above_maximum() -> None:
    """Scores above maximum should clamp down."""

    assert clamp_score(TOO_HIGH_SCORE, MAX_SCORE) == MAX_SCORE


def test_mastery_band_reports_advanced() -> None:
    """High scores report advanced band."""

    assert mastery_band(95) == "advanced"
