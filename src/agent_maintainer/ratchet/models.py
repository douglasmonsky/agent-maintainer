"""JSON-safe models for ratchet baselines and status reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

JsonValue = int | float | str | None


@dataclass(frozen=True)
class RatchetFinding:
    """One normalized ratchet violation."""

    check: str
    identity: str
    path: str
    line: int | None
    severity: str
    metric: str | None
    value: JsonValue
    threshold: JsonValue
    message: str
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON object."""

        return {
            "check": self.check,
            "identity": self.identity,
            "path": self.path,
            "line": self.line,
            "severity": self.severity,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RatchetFinding:
        """Build a finding from a JSON object."""

        return cls(
            check=str(payload["check"]),
            identity=str(payload["identity"]),
            path=str(payload["path"]),
            line=payload.get("line"),
            severity=str(payload["severity"]),
            metric=payload.get("metric"),
            value=payload.get("value"),
            threshold=payload.get("threshold"),
            message=str(payload["message"]),
            fingerprint=str(payload["fingerprint"]),
        )


@dataclass(frozen=True)
class BaselineProvenance:
    """Metadata explaining where a baseline came from."""

    version: int
    created_at: str
    created_by: str
    base_ref: str
    repo_commit: str
    dirty_state: bool
    mode: str
    checks: tuple[str, ...]
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON object."""

        return {
            "version": self.version,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "base_ref": self.base_ref,
            "repo_commit": self.repo_commit,
            "dirty_state": self.dirty_state,
            "mode": self.mode,
            "checks": list(self.checks),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BaselineProvenance:
        """Build provenance from a JSON object."""

        return cls(
            version=int(payload["version"]),
            created_at=str(payload["created_at"]),
            created_by=str(payload["created_by"]),
            base_ref=str(payload["base_ref"]),
            repo_commit=str(payload["repo_commit"]),
            dirty_state=bool(payload["dirty_state"]),
            mode=str(payload["mode"]),
            checks=tuple(str(check) for check in payload.get("checks", ())),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class RatchetBaseline:
    """Persisted ratchet baseline."""

    provenance: BaselineProvenance
    findings: tuple[RatchetFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON object."""

        return {
            "provenance": self.provenance.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RatchetBaseline:
        """Build a baseline from a JSON object."""

        findings = tuple(
            RatchetFinding.from_dict(raw_finding) for raw_finding in payload.get("findings", ())
        )
        return cls(
            provenance=BaselineProvenance.from_dict(payload["provenance"]),
            findings=findings,
        )


@dataclass(frozen=True)
class RatchetStatusEntry:
    """Comparison result for one finding."""

    status: str
    finding: RatchetFinding
    baseline: RatchetFinding | None

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON object."""

        return {
            "status": self.status,
            "finding": self.finding.to_dict(),
            "baseline": self.baseline.to_dict() if self.baseline else None,
        }


@dataclass(frozen=True)
class RatchetStatusReport:
    """Current status for one ratchet baseline."""

    entries: tuple[RatchetStatusEntry, ...]
    stale_reasons: tuple[str, ...]

    def counts(self) -> dict[str, int]:
        """Return status counts."""

        statuses = ("new", "worsened", "unchanged", "improved", "resolved")
        return {
            status: sum(entry.status == status for entry in self.entries) for status in statuses
        }

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON object."""

        return {
            "counts": self.counts(),
            "stale_reasons": list(self.stale_reasons),
            "entries": [entry.to_dict() for entry in self.entries],
        }
