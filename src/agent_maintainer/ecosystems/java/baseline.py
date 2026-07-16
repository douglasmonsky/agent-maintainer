"""Deterministic Java finding debt baseline lifecycle and comparison."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agent_maintainer.ecosystems.java.findings import JavaFinding

BASELINE_VERSION = 1
CREATED_BY = "agent-maintainer"
MAX_BASELINE_BYTES = 2_000_000
MAX_BASELINE_ENTRIES = 20_000
COMMIT_PATTERN = re.compile(r"[0-9a-f]{7,64}")


@dataclass(frozen=True)
class JavaBaselineProvenance:
    """Stable baseline origin without nondeterministic timestamps."""

    source_commit: str
    created_by: str = CREATED_BY
    notes: str = ""

    def __post_init__(self) -> None:
        """Require an explicit immutable Git object identity."""
        if COMMIT_PATTERN.fullmatch(self.source_commit) is None:
            raise ValueError("Java baseline source_commit must be a hexadecimal commit id")
        if not self.created_by.strip():
            raise ValueError("Java baseline created_by must not be empty")


@dataclass(frozen=True)
class JavaBaselineEntry:
    """Allowed multiset count and numeric ceilings for one identity."""

    fingerprint: str
    tool: str
    rule: str
    path: str
    subject: str
    message: str
    severity: str
    allowed_count: int
    metric_ceilings: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Validate deterministic entry invariants."""
        expected_fingerprint = JavaFinding(
            self.tool,
            self.rule,
            self.path,
            self.subject,
            self.message,
            self.severity,
        ).fingerprint
        invalid_fingerprint = (
            re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
            or self.fingerprint != expected_fingerprint
        )
        if invalid_fingerprint:
            raise ValueError("Java baseline fingerprint must match normalized identity")
        invalid_count = self.allowed_count < 1 or (
            bool(self.metric_ceilings) and len(self.metric_ceilings) != self.allowed_count
        )
        if invalid_count:
            raise ValueError("Java baseline count and metric ceilings do not match")
        invalid_ceilings = tuple(sorted(self.metric_ceilings)) != self.metric_ceilings or any(
            value < 0 for value in self.metric_ceilings
        )
        if invalid_ceilings:
            raise ValueError("Java baseline metric ceilings must be sorted and non-negative")


@dataclass(frozen=True)
class JavaFindingsBaseline:
    """Versioned deterministic baseline document."""

    version: int
    provenance: JavaBaselineProvenance
    entries: tuple[JavaBaselineEntry, ...]

    def __post_init__(self) -> None:
        """Reject unsupported, duplicate, or noncanonical documents."""
        if self.version != BASELINE_VERSION:
            raise ValueError(f"unsupported Java baseline version: {self.version}")
        fingerprints = tuple(entry.fingerprint for entry in self.entries)
        if fingerprints != tuple(sorted(fingerprints)):
            raise ValueError("Java baseline entries must be fingerprint-sorted")
        if len(fingerprints) != len(set(fingerprints)):
            raise ValueError("Java baseline entries contain duplicate fingerprints")


@dataclass(frozen=True)
class MetricRegression:
    """One numeric finding exceeding its matched baseline ceiling."""

    fingerprint: str
    current: int
    ceiling: int


@dataclass(frozen=True)
class FindingDebtReport:
    """Duplicate-aware comparison result for current findings."""

    new_occurrences: int
    regressions: tuple[MetricRegression, ...]
    improved_occurrences: int
    resolved_occurrences: int

    @property
    def passed(self) -> bool:
        """Return whether current findings introduce no new or higher debt."""
        return self.new_occurrences == 0 and not self.regressions


@dataclass(frozen=True)
class JavaBaselineSummary:
    """Bounded inspect output for one Java findings baseline."""

    version: int
    source_commit: str
    entry_count: int
    occurrence_count: int
    numeric_ceiling_count: int


def create_baseline(
    findings: Iterable[JavaFinding],
    *,
    source_commit: str,
    notes: str = "",
) -> JavaFindingsBaseline:
    """Create a deterministic baseline from normalized findings."""
    entries = _entries_from_findings(findings)
    return JavaFindingsBaseline(
        BASELINE_VERSION,
        JavaBaselineProvenance(source_commit.lower(), notes=notes),
        entries,
    )


def compare_baseline(
    baseline: JavaFindingsBaseline,
    findings: Iterable[JavaFinding],
) -> FindingDebtReport:
    """Compare current findings using counts and descending numeric matching."""
    current = _group_findings(findings)
    allowed = {entry.fingerprint: entry for entry in baseline.entries}
    new_occurrences = 0
    regressions: list[MetricRegression] = []
    improved = 0
    resolved = 0
    for fingerprint in sorted(set(current) | set(allowed)):
        current_findings = current.get(fingerprint, ())
        entry = allowed.get(fingerprint)
        if entry is None:
            new_occurrences += len(current_findings)
            continue
        resolved += max(0, entry.allowed_count - len(current_findings))
        if len(current_findings) > entry.allowed_count:
            new_occurrences += len(current_findings) - entry.allowed_count
        metric_result = _compare_metrics(entry, current_findings)
        new_occurrences += metric_result[0]
        regressions.extend(metric_result[1])
        improved += metric_result[2]
    return FindingDebtReport(
        new_occurrences,
        tuple(regressions),
        improved,
        resolved,
    )


def prune_baseline(
    baseline: JavaFindingsBaseline,
    findings: Iterable[JavaFinding],
    *,
    source_commit: str,
) -> JavaFindingsBaseline:
    """Explicitly remove resolved debt and lower improved numeric ceilings."""
    return create_baseline(
        findings,
        source_commit=source_commit,
        notes=baseline.provenance.notes,
    )


def inspect_baseline(baseline: JavaFindingsBaseline) -> JavaBaselineSummary:
    """Return a concise baseline summary without exposing raw report data."""
    return JavaBaselineSummary(
        baseline.version,
        baseline.provenance.source_commit,
        len(baseline.entries),
        sum(entry.allowed_count for entry in baseline.entries),
        sum(len(entry.metric_ceilings) for entry in baseline.entries),
    )


def render_baseline(baseline: JavaFindingsBaseline) -> str:
    """Render canonical newline-terminated JSON."""
    return f"{json.dumps(_BASELINE_CODEC.payload(baseline), indent=2, sort_keys=True)}\n"


def parse_baseline(text: str) -> JavaFindingsBaseline:
    """Parse one bounded strict baseline document."""
    if len(text.encode("utf-8")) > MAX_BASELINE_BYTES:
        raise ValueError("Java baseline exceeds the size limit")
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Java baseline is malformed JSON") from exc
    root = _BASELINE_CODEC.object(
        payload,
        "Java baseline",
        {"entries", "provenance", "version"},
    )
    version = _BASELINE_CODEC.integer(root["version"], "version")
    provenance = _BASELINE_CODEC.provenance(root["provenance"])
    raw_entries = _BASELINE_CODEC.array(root["entries"], "entries")
    if len(raw_entries) > MAX_BASELINE_ENTRIES:
        raise ValueError("Java baseline contains too many entries")
    entries = tuple(_BASELINE_CODEC.entry(item) for item in raw_entries)
    return JavaFindingsBaseline(version, provenance, entries)


def write_baseline(
    path: Path,
    baseline: JavaFindingsBaseline,
    *,
    force: bool = False,
) -> None:
    """Write canonical JSON, refusing an unapproved overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if force else "x"
    try:
        with path.open(mode, encoding="utf-8", newline="\n") as handle:
            handle.write(render_baseline(baseline))
    except FileExistsError as exc:
        raise FileExistsError(f"baseline already exists: {path}") from exc


def read_baseline(path: Path) -> JavaFindingsBaseline:
    """Read one bounded baseline file."""
    if path.stat().st_size > MAX_BASELINE_BYTES:
        raise ValueError("Java baseline exceeds the size limit")
    return parse_baseline(path.read_text(encoding="utf-8"))


def _entries_from_findings(findings: Iterable[JavaFinding]) -> tuple[JavaBaselineEntry, ...]:
    grouped = _group_findings(findings)
    if len(grouped) > MAX_BASELINE_ENTRIES:
        raise ValueError("Java baseline contains too many entries")
    entries = tuple(_entry_from_group(grouped[fingerprint]) for fingerprint in sorted(grouped))
    return entries


def _group_findings(findings: Iterable[JavaFinding]) -> dict[str, tuple[JavaFinding, ...]]:
    grouped: defaultdict[str, list[JavaFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.fingerprint].append(finding)
    return {fingerprint: tuple(items) for fingerprint, items in grouped.items()}


def _entry_from_group(findings: tuple[JavaFinding, ...]) -> JavaBaselineEntry:
    first = findings[0]
    if any(finding.identity != first.identity for finding in findings):
        raise ValueError("Java finding fingerprint collision")
    metrics = tuple(finding.metric for finding in findings)
    if any(metric is None for metric in metrics) and any(metric is not None for metric in metrics):
        raise ValueError("Java finding identity mixes numeric and nonnumeric values")
    ceilings = tuple(sorted(metric for metric in metrics if metric is not None))
    return JavaBaselineEntry(
        first.fingerprint,
        first.tool,
        first.rule,
        first.path,
        first.subject,
        first.message,
        first.severity,
        len(findings),
        ceilings,
    )


def _compare_metrics(
    entry: JavaBaselineEntry,
    findings: tuple[JavaFinding, ...],
) -> tuple[int, tuple[MetricRegression, ...], int]:
    if not entry.metric_ceilings:
        return (sum(finding.metric is not None for finding in findings), (), 0)
    metrics = tuple(
        sorted(
            (finding.metric for finding in findings if finding.metric is not None),
            reverse=True,
        )
    )
    missing_metrics = sum(finding.metric is None for finding in findings)
    regressions: list[MetricRegression] = []
    improved = 0
    for current, ceiling in zip(metrics, reversed(entry.metric_ceilings), strict=False):
        if current > ceiling:
            regressions.append(MetricRegression(entry.fingerprint, current, ceiling))
        elif current < ceiling:
            improved += 1
    return (missing_metrics, tuple(regressions), improved)


@dataclass(frozen=True)
class _BaselineCodec:
    """Strict JSON conversion helpers kept behind one bounded interface."""

    def payload(self, baseline: JavaFindingsBaseline) -> dict[str, object]:
        """Return the canonical JSON-ready payload."""
        return {
            "version": baseline.version,
            "provenance": {
                "source_commit": baseline.provenance.source_commit,
                "created_by": baseline.provenance.created_by,
                "notes": baseline.provenance.notes,
            },
            "entries": [
                {
                    "fingerprint": entry.fingerprint,
                    "tool": entry.tool,
                    "rule": entry.rule,
                    "path": entry.path,
                    "subject": entry.subject,
                    "message": entry.message,
                    "severity": entry.severity,
                    "allowed_count": entry.allowed_count,
                    "metric_ceilings": list(entry.metric_ceilings),
                }
                for entry in baseline.entries
            ],
        }

    def provenance(self, value: object) -> JavaBaselineProvenance:
        """Parse strict provenance fields."""
        payload = self.object(
            value,
            "provenance",
            {"created_by", "notes", "source_commit"},
        )
        return JavaBaselineProvenance(
            self.string(payload["source_commit"], "source_commit"),
            self.string(payload["created_by"], "created_by"),
            self.string(payload["notes"], "notes", allow_empty=True),
        )

    def entry(self, value: object) -> JavaBaselineEntry:
        """Parse one strict baseline entry."""
        keys = {
            "allowed_count",
            "fingerprint",
            "message",
            "metric_ceilings",
            "path",
            "rule",
            "severity",
            "subject",
            "tool",
        }
        payload = self.object(value, "entry", keys)
        raw_ceilings = self.array(payload["metric_ceilings"], "metric_ceilings")
        ceilings = tuple(self.integer(item, "metric ceiling") for item in raw_ceilings)
        return JavaBaselineEntry(
            self.string(payload["fingerprint"], "fingerprint"),
            self.string(payload["tool"], "tool"),
            self.string(payload["rule"], "rule"),
            self.string(payload["path"], "path"),
            self.string(payload["subject"], "subject", allow_empty=True),
            self.string(payload["message"], "message"),
            self.string(payload["severity"], "severity"),
            self.integer(payload["allowed_count"], "allowed_count"),
            ceilings,
        )

    def object(
        self,
        value: object,
        label: str,
        expected: set[str],
    ) -> dict[str, object]:
        """Return a string-keyed object with an exact field set."""
        if not isinstance(value, dict):
            raise ValueError(f"{label} has unsupported or missing fields")
        untyped = cast(dict[object, object], value)
        invalid_keys = any(not isinstance(key, str) for key in untyped) or set(untyped) != expected
        if invalid_keys:
            raise ValueError(f"{label} has unsupported or missing fields")
        return cast(dict[str, object], untyped)

    def array(self, value: object, label: str) -> list[object]:
        """Return a JSON array."""
        if not isinstance(value, list):
            raise ValueError(f"{label} must be an array")
        return cast(list[object], value)

    def string(self, value: object, label: str, *, allow_empty: bool = False) -> str:
        """Return a JSON string with optional emptiness."""
        if not isinstance(value, str) or (not value and not allow_empty):
            raise ValueError(f"{label} must be a string")
        return value

    def integer(self, value: object, label: str) -> int:
        """Return a JSON integer while rejecting booleans."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{label} must be an integer")
        return value


_BASELINE_CODEC = _BaselineCodec()
