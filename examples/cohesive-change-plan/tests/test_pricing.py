"""Tests for cohesive change-plan pricing fixture."""

from __future__ import annotations

from catalog.pricing import discounted_price

DISCOUNTED_PRICE_CENTS = 850


def test_discounted_price_uses_integer_cents() -> None:
    """Discount calculation keeps integer cents."""

    assert discounted_price(1000, 15) == DISCOUNTED_PRICE_CENTS
