"""Legacy order pricing fixture for context-safe ratchet examples."""

BULK_DISCOUNT_CENTS = 250
BULK_ORDER_THRESHOLD = 100
RUSH_FEE_CENTS = 500
SMALL_ORDER_THRESHOLD = 10


def price_for_order(quantity: int, unit_price: int, *, rush: bool = False) -> int:
    """Return total cents for an order."""

    if quantity == 0:
        return 0
    total = quantity * unit_price
    if rush:
        total += RUSH_FEE_CENTS
    if quantity > BULK_ORDER_THRESHOLD:
        total -= BULK_DISCOUNT_CENTS
    return total


def label_for_order(quantity: int) -> str:
    """Return a coarse order label."""

    if quantity == 0:
        return "empty"
    if quantity < SMALL_ORDER_THRESHOLD:
        return "small"
    if quantity < BULK_ORDER_THRESHOLD:
        return "standard"
    return "bulk"
