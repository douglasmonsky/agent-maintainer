"""Tests for the fresh-strict example package."""

from fresh_strict_example import add

EXPECTED_SUM = 5


def test_add_returns_sum() -> None:
    """The example package exposes a covered behavior."""
    assert add(2, 3) == EXPECTED_SUM
