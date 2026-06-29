"""Tests for context-safe ratchet example fixture."""

from __future__ import annotations

import pytest
from legacy.big import label_for_order, price_for_order


def test_price_for_order_rejects_negative_quantity() -> None:
    """Negative quantities are invalid input."""

    with pytest.raises(ValueError):
        price_for_order(-1, 100)


def test_label_for_order_reports_bulk() -> None:
    """Large orders get bulk label."""

    assert label_for_order(120) == "bulk"
