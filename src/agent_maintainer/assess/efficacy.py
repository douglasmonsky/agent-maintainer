"""Assess whether agent-facing primitives are improving local work loops."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_context.failures import DEFAULT_CONTEXT_BUDGET
from agent_maintainer.assess import efficacy_followthrough
from agent_maintainer.assess.efficacy_models import (
    UNKNOWN,
    EfficacyMetric,
    EfficacyReport,
)
from agent_maintainer.runtime_events.read import (
    RuntimeEventReadResult,
    read_runtime_events,
)

DEFAULT_EVENT_FILE_LIMIT = 40
FAILED_STATUSES = frozenset(("fail", "failed", "error", "timeout", "exception"))
PASS_STATUSES = frozenset(("pass", "passed", "success"))
TOKEN_CHARS = 4


@dataclass(frozen=True)
class EfficacyBuilder:
    """Build efficacy metrics from already-read local artifacts."""

    read_result: RuntimeEventReadResult
    log_dir: Path

    def build(self) -> EfficacyReport:
        """Return local efficacy report."""

        metrics = [
            *self._verifier_metrics(),
            *efficacy_followthrough.metrics(self.records),
            *self._manifest_metrics(),
        ]
        return EfficacyReport(
            files_read=self.read_result.files_read,
            total_events=len(self.records),
            malformed_lines=self.read_result.malformed_lines,
            metrics=tuple(metrics),
            sources=self._sources(),
            limitations=_limitations(metrics),
        )

    @property
    def records(self) -> list[dict[str, Any]]:
        """Return event records."""

        return self.read_result.records

    def _verifier_metrics(self) -> list[EfficacyMetric]:
        fresh_runs = _event_count(self.records, "verifier.fresh")
        reused_runs = _event_count(self.records, "verifier.reused")
        verifier_runs = fresh_runs + reused_runs
        failure_to_pass_ms = _first_failure_to_pass_ms(self.records)
        duration_value: int | str = UNKNOWN
        duration_kind = UNKNOWN
        if failure_to_pass_ms is None:
            duration_value = UNKNOWN
        else:
            duration_value = failure_to_pass_ms
            duration_kind = "measured"
        return [
            EfficacyMetric(
                name="verifier_fresh_runs",
                value=fresh_runs,
                unit="runs",
                kind="measured",
                detail="fresh verifier executions observed in runtime events",
            ),
            EfficacyMetric(
                name="duplicate_run_avoidance_rate",
                value=_percentage(reused_runs, verifier_runs),
                unit="percent",
                kind="measured" if verifier_runs else UNKNOWN,
                detail="verifier.reused divided by fresh plus reused verifier runs",
                numerator=reused_runs if verifier_runs else None,
                denominator=verifier_runs if verifier_runs else None,
            ),
            EfficacyMetric(
                name="first_failure_to_passing_profile_ms",
                value=duration_value,
                unit="milliseconds",
                kind=duration_kind,
                detail="elapsed time from first failure event to next passing profile",
            ),
        ]

    def _manifest_metrics(self) -> list[EfficacyMetric]:
        manifest = _read_latest_manifest(self.log_dir)
        if manifest is None:
            return [
                EfficacyMetric(
                    name="repair_capsule_token_savings_proxy",
                    value=UNKNOWN,
                    unit="tokens",
                    kind=UNKNOWN,
                    detail="no verifier manifest found for log-byte savings estimate",
                ),
            ]
        failed_checks = tuple(_failed_manifest_checks(manifest))
        savings = _manifest_token_savings(failed_checks)
        return [
            EfficacyMetric(
                name="latest_manifest_failed_checks",
                value=len(failed_checks),
                unit="checks",
                kind="measured",
                detail="failed checks in the latest verifier manifest",
            ),
            EfficacyMetric(
                name="repair_capsule_token_savings_proxy",
                value=savings,
                unit="tokens",
                kind="estimated",
                detail="log bytes avoided by bounded repair context, using chars/4",
            ),
        ]

    def _sources(self) -> tuple[str, ...]:
        sources = ["".join(("runtime events: ", str(self.read_result.files_read), " files"))]
        manifest_path = _latest_manifest_path(self.log_dir)
        if manifest_path is not None:
            sources.append("".join(("manifest: ", str(manifest_path))))
        return tuple(sources)


def build_efficacy_report(
    target: Path,
    *,
    events_dir: Path | None = None,
    log_dir: Path | None = None,
    event_file_limit: int = DEFAULT_EVENT_FILE_LIMIT,
) -> EfficacyReport:
    """Build efficacy report from local runtime events and verifier artifacts."""

    resolved_events_dir = events_dir or target / ".verify-logs" / "events"
    resolved_log_dir = log_dir or target / ".verify-logs"
    read_result = read_runtime_events(resolved_events_dir, file_limit=event_file_limit)
    return summarize_efficacy(read_result, log_dir=resolved_log_dir)


def summarize_efficacy(
    read_result: RuntimeEventReadResult,
    *,
    log_dir: Path,
) -> EfficacyReport:
    """Summarize already-read runtime events into efficacy metrics."""

    return EfficacyBuilder(read_result=read_result, log_dir=log_dir).build()


def _event_count(records: list[dict[str, Any]], event_name: str) -> int:
    return sum(1 for record in records if record.get("event_name") == event_name)


def _percentage(numerator: int, denominator: int) -> float | str:
    if denominator <= 0:
        return UNKNOWN
    return round((numerator / denominator) * 100, 1)


def _first_failure_to_pass_ms(records: list[dict[str, Any]]) -> int | None:
    failure_time: datetime | None = None
    for record in records:
        timestamp = _timestamp(record)
        if timestamp is None:
            continue
        if failure_time is None and _failed_event(record):
            failure_time = timestamp
            continue
        if failure_time is not None and _passing_profile(record):
            return int((timestamp - failure_time).total_seconds() * 1000)
    return None


def _read_latest_manifest(log_dir: Path) -> dict[str, Any] | None:
    manifest_path = _latest_manifest_path(log_dir)
    if manifest_path is None:
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _latest_manifest_path(log_dir: Path) -> Path | None:
    candidates = [log_dir / "manifest.json", *sorted((log_dir / "runs").glob("*/manifest.json"))]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _failed_manifest_checks(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    checks = manifest.get("checks")
    if not isinstance(checks, list):
        return ()
    return (
        check
        for check in checks
        if isinstance(check, dict) and str(check.get("status", "")).lower() in FAILED_STATUSES
    )


def _manifest_token_savings(checks: Iterable[dict[str, Any]]) -> int:
    raw_chars = sum(_positive_int(check.get("log_bytes")) for check in checks)
    bounded_chars = min(raw_chars, DEFAULT_CONTEXT_BUDGET)
    return max(raw_chars - bounded_chars, 0) // TOKEN_CHARS


def _positive_int(value: object) -> int:
    return value if isinstance(value, int) and value > 0 else 0


def _timestamp(record: dict[str, Any]) -> datetime | None:
    value = record.get("timestamp")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _failed_event(record: dict[str, Any]) -> bool:
    return (
        record.get("event_name") == "check.failed"
        or record.get("status") in FAILED_STATUSES
        or record.get("severity") == "error"
    )


def _passing_profile(record: dict[str, Any]) -> bool:
    return record.get("event_name") == "profile.finished" and record.get("status") in PASS_STATUSES


def _limitations(metrics: list[EfficacyMetric]) -> tuple[str, ...]:
    limitations = [
        "token savings are estimated from artifact bytes, not provider billing",
        "pointer follow-through uses local command events, not chat transcripts",
        "manual escalation counts explicit local runtime events only",
    ]
    if any(metric.kind == UNKNOWN for metric in metrics):
        limitations.append("unknown metrics need more runtime events or manifests")
    return tuple(limitations)
