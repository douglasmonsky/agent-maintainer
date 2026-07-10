"""DocSync trace loading and editing errors."""

from __future__ import annotations


class TraceEditError(ValueError):
    """Raised when a trace edit cannot be applied safely."""
