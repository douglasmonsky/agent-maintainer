"""Data models for deterministic attention ledgers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Final

SCHEMA_VERSION: Final = 1


@dataclass(frozen=True)
class AttentionFileScore:
    """One file-level attention score."""

    path: str
    score: float
    components: dict[str, float]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AttentionLedger:
    """Deterministic attention ledger for repository files."""

    schema_version: int
    target: str
    file_count: int
    inputs: dict[str, object]
    files: tuple[AttentionFileScore, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return JSON-serializable payload."""
        return asdict(self)
