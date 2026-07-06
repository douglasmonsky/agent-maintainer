"""Models for local agent efficacy assessment."""

from __future__ import annotations

import json
from dataclasses import dataclass

UNKNOWN = "unknown"


@dataclass(frozen=True)
class EfficacyMetric:
    """One measured or estimated local efficacy metric."""

    name: str
    value: int | float | str
    unit: str
    kind: str
    detail: str
    numerator: int | None = None
    denominator: int | None = None

    def to_payload(self) -> dict[str, object]:
        """Return stable JSON-compatible metric payload."""

        payload: dict[str, object] = {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "kind": self.kind,
            "detail": self.detail,
        }
        if self.numerator is not None:
            payload["numerator"] = self.numerator
        if self.denominator is not None:
            payload["denominator"] = self.denominator
        return payload


@dataclass(frozen=True)
class EfficacyReport:
    """Compact local agent efficacy report."""

    files_read: int
    total_events: int
    malformed_lines: int
    metrics: tuple[EfficacyMetric, ...]
    sources: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return stable JSON-compatible report payload."""

        return {
            "files_read": self.files_read,
            "total_events": self.total_events,
            "malformed_lines": self.malformed_lines,
            "metrics": [metric.to_payload() for metric in self.metrics],
            "sources": list(self.sources),
            "limitations": list(self.limitations),
        }

    def to_json(self) -> str:
        """Return deterministic JSON report."""

        return json.dumps(self.to_payload(), indent=2, sort_keys=True)
