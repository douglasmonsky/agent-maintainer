"""Tests for the legacy-ratchet example package."""

from legacy_ratchet_example import normalize_label


def test_normalize_label_collapses_extra_space() -> None:
    """The example package has at least one covered behavior."""
    assert normalize_label("  Alpha   Beta  ") == "Alpha Beta"
