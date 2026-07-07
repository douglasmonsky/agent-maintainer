"""Demo implementation used by the DocSync first-run fixture."""


# docsync:evidence.start evidence.tax_total
def tax_total(subtotal: int) -> int:
    """Return subtotal with the configured tax rate applied."""
    return subtotal * 108 // 100


# docsync:evidence.end evidence.tax_total
