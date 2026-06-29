"""Catalog pricing fixture for cohesive change-plan examples."""


def discounted_price(cents: int, percent: int) -> int:
    """Return discounted price in cents."""

    discount = cents * percent // 100
    return cents - discount
