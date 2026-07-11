"""Data models for deterministic attention ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

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

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable payload."""
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "file_count": self.file_count,
            "inputs": self.inputs,
            "files": [
                {
                    "path": score.path,
                    "score": score.score,
                    "components": score.components,
                    "reasons": score.reasons,
                }
                for score in self.files
            ],
        }
