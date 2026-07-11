"""Context compression request and result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompressionRequest:
    """Requested compression work for already sanitized context."""

    content: str
    content_kind: str
    target_chars: int
    preserve_terms: tuple[str, ...]
    forbidden_terms: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict[str, str])

    def __post_init__(self) -> None:
        """Reject invalid compression requests."""

        validate_non_negative(self.target_chars, name="target_chars")
        validate_non_empty_text(self.content_kind, name="content_kind")
        validate_terms(self.preserve_terms, name="preserve_terms")
        validate_terms(self.forbidden_terms, name="forbidden_terms")


@dataclass(frozen=True)
class CompressionResult:
    """Compressed context plus preservation metadata."""

    content: str
    backend: str
    original_chars: int
    compressed_chars: int
    exact_facts_preserved: bool
    warnings: tuple[str, ...] = ()


def validate_non_negative(value: int, *, name: str) -> None:
    """Reject negative integer values."""

    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def validate_non_empty_text(value: str, *, name: str) -> None:
    """Reject empty or whitespace-only text values."""

    if not value.strip():
        raise ValueError(f"{name} must be non-empty")


def validate_terms(terms: tuple[str, ...], *, name: str) -> None:
    """Reject empty exact-match term values."""

    if any(not term for term in terms):
        raise ValueError(f"{name} must not contain empty strings")
