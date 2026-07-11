"""Assess structured repair-fact coverage for recent verifier failures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agent_context.failures import FailureRecord, record_from_payload
from agent_maintainer.assess.repair_fact_coverage_models import (
    RepairFactCheckCoverage,
    RepairFactCoverageReport,
    RepairFactParserTarget,
)
from agent_maintainer.context.pack import exact_facts
from agent_maintainer.core.structured_values import json_array, json_object

MANIFEST_NAME = "manifest.json"
RUNS_DIR_NAME = "runs"
DEFAULT_RUN_LIMIT = 10
PERFECT_COVERAGE = 100.0


@dataclass(frozen=True)
class _ManifestFailure:
    """Failed check plus its manifest path."""

    manifest_path: Path
    record: FailureRecord


def build_repair_fact_coverage_report(
    target: Path,
    *,
    log_dir: Path | None = None,
    run_limit: int = DEFAULT_RUN_LIMIT,
) -> RepairFactCoverageReport:
    """Return repair-fact coverage for the latest verifier manifest."""

    resolved_target = target.resolve()
    resolved_log_dir = resolved_log_dir_for(resolved_target, log_dir)
    manifests = recent_manifest_paths(resolved_log_dir, run_limit=run_limit)
    if manifests:
        return report_from_manifest(resolved_target, resolved_log_dir, manifests)
    return no_manifest_report(resolved_target, resolved_log_dir)


def report_from_manifest(
    target: Path,
    log_dir: Path,
    manifests: tuple[Path, ...],
) -> RepairFactCoverageReport:
    """Return coverage report from recent manifests."""

    latest_manifest_path = manifests[0]
    latest_manifest = read_manifest(latest_manifest_path)
    if latest_manifest is None:
        return no_manifest_report(target, log_dir)
    latest_failures = failures_for_manifest(latest_manifest_path, latest_manifest)
    checks = tuple(
        check_coverage(latest_manifest_path.parent, failure.record) for failure in latest_failures
    )
    structured_checks = sum(1 for check in checks if check.structured_facts)
    fallback_checks = sum(1 for check in checks if check.fallback_facts)
    recent_failures = tuple(
        failure
        for manifest_path in manifests
        if (manifest := read_manifest(manifest_path)) is not None
        for failure in failures_for_manifest(manifest_path, manifest)
    )
    return RepairFactCoverageReport(
        target=str(target),
        log_dir=str(log_dir),
        manifest_path=str(latest_manifest_path),
        run_id=optional_text(latest_manifest.get("run_id")),
        profile=optional_text(latest_manifest.get("profile")),
        status=status_for(len(checks), fallback_checks),
        failed_checks=len(checks),
        structured_checks=structured_checks,
        fallback_checks=fallback_checks,
        coverage_percent=coverage(structured_checks, len(checks)),
        checks=checks,
        parser_targets=rank_parser_targets(recent_failures),
        next_commands=next_commands(latest_manifest_path, fallback_checks),
    )


def recent_manifest_paths(log_dir: Path, *, run_limit: int) -> tuple[Path, ...]:
    """Return recent run-scoped manifest paths, newest first."""

    run_manifests = tuple(
        reversed(sorted((log_dir / RUNS_DIR_NAME).glob(f"*/{MANIFEST_NAME}"))),
    )
    if run_manifests:
        return run_manifests[: max(run_limit, 1)]
    latest = log_dir / MANIFEST_NAME
    return (latest,) if latest.exists() else ()


def read_manifest(path: Path) -> dict[str, object] | None:
    """Return manifest payload if readable."""

    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return json_object(payload)


def failures_for_manifest(
    manifest_path: Path,
    manifest: dict[str, object],
) -> tuple[_ManifestFailure, ...]:
    """Return failed checks for one manifest in stable priority order."""

    checks = json_array(manifest.get("checks"))
    if checks is None:
        return ()
    return tuple(
        _ManifestFailure(manifest_path, record)
        for record in sorted(failed_records(checks), key=failure_sort_key)
    )


def failed_records(checks: list[object]) -> tuple[FailureRecord, ...]:
    """Return failed records from manifest checks payloads."""

    return tuple(
        record for item in checks if (record := failed_record_from_payload(item)) is not None
    )


def failed_record_from_payload(payload: object) -> FailureRecord | None:
    """Return failure record only when payload is failed check."""

    record = record_from_payload(payload)
    if record is None or record.status != "failed":
        return None
    return record


def failure_sort_key(record: FailureRecord) -> tuple[int, str]:
    """Return stable failure sort key."""

    return (record.priority, record.name)


def check_coverage(log_dir: Path, record: FailureRecord) -> RepairFactCheckCoverage:
    """Return structured versus fallback fact coverage for one failed check."""

    facts = exact_facts.structured_facts(log_dir, record)
    actionable_facts = tuple(fact for fact in facts if is_actionable_fact(fact))
    fallback_facts = 0 if actionable_facts else 1
    return RepairFactCheckCoverage(
        check=record.name,
        structured_facts=len(actionable_facts),
        fallback_facts=fallback_facts,
        log_bytes=record.log_bytes,
        artifact_paths=record.artifact_paths,
        expansion_commands=record.expansion_commands,
    )


def rank_parser_targets(
    failures: tuple[_ManifestFailure, ...],
) -> tuple[RepairFactParserTarget, ...]:
    """Return deterministic parser targets for checks still using fallbacks."""

    by_check: dict[str, list[FailureRecord]] = {}
    for failure in failures:
        coverage_record = check_coverage(failure.manifest_path.parent, failure.record)
        if coverage_record.fallback_facts:
            by_check.setdefault(failure.record.name, []).append(failure.record)
    targets = tuple(target_for(check, records) for check, records in by_check.items())
    return tuple(
        sorted(
            targets,
            key=lambda item: (
                -item.fallback_failures,
                -item.total_log_bytes,
                item.priority,
                item.check,
            ),
        )
    )


def target_for(check: str, records: list[FailureRecord]) -> RepairFactParserTarget:
    """Return one parser target aggregate."""

    artifact_paths = tuple(
        sorted({artifact for record in records for artifact in record.artifact_paths})
    )
    priority = min(record.priority for record in records)
    return RepairFactParserTarget(
        check=check,
        fallback_failures=len(records),
        total_log_bytes=sum(record.log_bytes for record in records),
        priority=priority,
        artifact_paths=artifact_paths,
        recommendation=recommendation_for(check, artifact_paths),
    )


def recommendation_for(check: str, artifact_paths: tuple[str, ...]) -> str:
    """Return compact parser improvement recommendation."""

    if artifact_paths:
        names = ", ".join(Path(path).name for path in artifact_paths[:3])
        return f"Add structured parser for {check} artifacts: {names}."
    return f"Add log parser for {check} or configure a structured artifact."


def is_actionable_fact(fact: dict[str, object]) -> bool:
    """Return whether a fact has enough structure to avoid raw-log expansion."""

    check = str(fact.get("check") or "").strip()
    message = str(fact.get("message") or "").strip()
    locator_keys = ("path", "line", "symbol", "rule")
    locator = any(fact.get(key) not in (None, "") for key in locator_keys)
    return bool(check and message and locator)


def coverage(structured_checks: int, failed_checks: int) -> float:
    """Return coverage percent; no failures mean no parser gap observed."""

    if failed_checks == 0:
        return PERFECT_COVERAGE
    return round((structured_checks / failed_checks) * PERFECT_COVERAGE, 2)


def status_for(failed_checks: int, fallback_checks: int) -> str:
    """Return stable report status."""

    if failed_checks == 0:
        return "no-failures"
    if fallback_checks == 0:
        return "structured"
    if fallback_checks == failed_checks:
        return "fallback-only"
    return "mixed"


def next_commands(manifest_path: Path, fallback_checks: int) -> tuple[str, ...]:
    """Return just-in-time follow-up commands."""

    if fallback_checks:
        return (
            "python -m agent_maintainer assess repair-fact-coverage --json",
            f"python -m agent_maintainer context failures --log-dir {manifest_path.parent}",
        )
    return ("python -m agent_maintainer context failures",)


def no_manifest_report(target: Path, log_dir: Path) -> RepairFactCoverageReport:
    """Return report when no verifier manifest exists."""

    return RepairFactCoverageReport(
        target=str(target),
        log_dir=str(log_dir),
        manifest_path=None,
        run_id=None,
        profile=None,
        status="no-manifest",
        failed_checks=0,
        structured_checks=0,
        fallback_checks=0,
        coverage_percent=PERFECT_COVERAGE,
        checks=(),
        parser_targets=(),
        next_commands=("python -m agent_maintainer verify --profile precommit",),
    )


def resolved_log_dir_for(target: Path, log_dir: Path | None) -> Path:
    """Return absolute diagnostic log directory."""

    candidate = log_dir or Path(".verify-logs")
    return candidate if candidate.is_absolute() else target / candidate


def optional_text(value: object) -> str | None:
    """Return non-empty text value."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None
