"""Small shared guard for explicit contract validation failures."""

from __future__ import annotations


def require(condition: bool, message: str, error_type: type[Exception]) -> None:
    """Raise the nominated validation error when a condition is false."""

    if not condition:
        raise error_type(message)
