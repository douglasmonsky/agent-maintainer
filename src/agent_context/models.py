"""Context contract value objects for bounded agent-facing output."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    """Limits for bounded context output."""

    max_chars: int
    max_items: int
    max_lines: int | None = None

    def __post_init__(self) -> None:
        """Reject negative limits before context producers use them."""

        if self.max_chars < 0:
            raise ValueError("max_chars must be non-negative")
        if self.max_items < 0:
            raise ValueError("max_items must be non-negative")
        if self.max_lines is not None and self.max_lines < 0:
            raise ValueError("max_lines must be non-negative when set")


@dataclass(frozen=True)
class BoundedText:
    """Text plus deterministic truncation metadata."""

    text: str
    original_chars: int
    original_lines: int
    truncated: bool
    omitted_chars: int
    omitted_lines: int


@dataclass(frozen=True)
class ExactRepairFact:
    """Exact fact a repair loop must preserve without summarizing."""

    check: str
    path: str | None
    line: int | None
    column: int | None
    symbol: str | None
    message: str
    severity: str


@dataclass(frozen=True)
class SupportingContext:
    """Untrusted supporting context from repository or tool output."""

    title: str
    content: str
    source: str
    untrusted: bool = True
