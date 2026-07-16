"""Bounded Java findings evidence parsing for explicit baseline lifecycles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agent_maintainer.assess import baseline_repository
from agent_maintainer.ecosystems.java import artifacts, baseline, report_evidence
from agent_maintainer.ecosystems.java.findings import JavaFinding

EXPECTED_FINDING_FIELDS = frozenset(
    (
        "fingerprint",
        "line",
        "message",
        "metric",
        "path",
        "rule",
        "severity",
        "subject",
        "tool",
    )
)
VALID_EVIDENCE_STATUSES = frozenset(("regression", "validated"))


class JavaEvidenceError(ValueError):
    """Invalid or unsafe Java evidence for a baseline lifecycle operation."""


@dataclass(frozen=True)
class JavaBaselineEvidence:
    """Complete findings tied to the exact repository commit that produced them."""

    source_commit: str
    findings: tuple[JavaFinding, ...]


def read_evidence(target: Path, artifact_path: Path) -> JavaBaselineEvidence:
    """Read one confined, bounded artifact tied to the current repository HEAD."""
    path = baseline_repository.confined_path(target, artifact_path, label="Java artifact")
    payload = _decode(_read_bounded(path))
    return _parse(payload, baseline_repository.repository_head(target))


def _read_bounded(path: Path) -> bytes:
    if not path.is_file():
        raise JavaEvidenceError(f"Java evidence artifact is not a file: {path}")
    try:
        raw = _read_bytes(path)
    except OSError as exc:
        raise JavaEvidenceError(f"could not read Java evidence artifact: {exc}") from exc
    if len(raw) > artifacts.MAX_ARTIFACT_BYTES:
        raise JavaEvidenceError("Java evidence artifact exceeds the size limit")
    return raw


def _read_bytes(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(artifacts.MAX_ARTIFACT_BYTES + 1)


def _decode(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JavaEvidenceError("Java evidence artifact is malformed JSON") from exc


def _parse(payload: Any, current_head: str) -> JavaBaselineEvidence:
    root = _object(payload, "Java evidence artifact")
    _validate_artifact_header(root)
    _validate_observation(root)
    reports = _object(root.get("reports"), "Java evidence reports")
    return _parse_reports(reports, current_head)


def _validate_artifact_header(root: dict[str, Any]) -> None:
    if root.get("schema_version") != 1 or root.get("provider") != "java-gradle":
        raise JavaEvidenceError("Java evidence artifact has an unsupported schema")
    if root.get("reports_parsed") is not True:
        raise JavaEvidenceError("Java evidence artifact has no parsed reports")
    if root.get("evidence_status") not in VALID_EVIDENCE_STATUSES:
        raise JavaEvidenceError("Java evidence artifact was not successfully validated")


def _validate_observation(root: dict[str, Any]) -> None:
    observation = _object(root.get("observation"), "Java evidence observation")
    if _integer(observation.get("exit_code"), "observation.exit_code") != 0:
        raise JavaEvidenceError("Java evidence artifact records a failed Gradle run")


def _parse_reports(reports: dict[str, Any], current_head: str) -> JavaBaselineEvidence:
    source_commit = _validated_source_commit(reports.get("source_commit"), current_head)
    finding_items = _finding_items(reports)
    finding_count = _integer(reports.get("finding_count"), "reports.finding_count")
    if finding_count != len(finding_items):
        raise JavaEvidenceError("Java evidence finding count does not match its facts")
    findings = tuple(_parse_finding(item) for item in finding_items)
    return JavaBaselineEvidence(source_commit.lower(), findings)


def _finding_items(reports: dict[str, Any]) -> list[Any]:
    if reports.get("findings_truncated") is not False:
        raise JavaEvidenceError("Java evidence findings are incomplete or truncated")
    raw_findings = reports.get("findings")
    if not isinstance(raw_findings, list):
        raise JavaEvidenceError("Java evidence findings must be an array")
    finding_items = cast(list[Any], raw_findings)
    if len(finding_items) > report_evidence.MAX_ARTIFACT_FINDINGS:
        raise JavaEvidenceError("Java evidence contains too many finding facts")
    return finding_items


def _validated_source_commit(payload: Any, current_head: str) -> str:
    if not isinstance(payload, str) or baseline.COMMIT_PATTERN.fullmatch(payload) is None:
        raise JavaEvidenceError("Java evidence source_commit is invalid")
    if payload.lower() != current_head:
        raise JavaEvidenceError("Java evidence is stale for the current repository HEAD")
    return payload


def _parse_finding(payload: Any) -> JavaFinding:
    raw = _validated_finding(payload)
    finding = _build_finding(raw)
    if raw["fingerprint"] != finding.fingerprint:
        raise JavaEvidenceError("Java evidence finding fingerprint does not match identity")
    return finding


def _validated_finding(payload: Any) -> dict[str, Any]:
    raw = _object(payload, "Java evidence finding")
    if frozenset(raw) != EXPECTED_FINDING_FIELDS:
        raise JavaEvidenceError("Java evidence finding has unexpected fields")
    strings = ("tool", "rule", "path", "subject", "message", "severity", "fingerprint")
    if any(not isinstance(raw[field], str) for field in strings):
        raise JavaEvidenceError("Java evidence finding text fields must be strings")
    return raw


def _build_finding(raw: dict[str, Any]) -> JavaFinding:
    line = _optional_integer(raw["line"], "finding.line")
    metric = _optional_integer(raw["metric"], "finding.metric")
    try:
        return JavaFinding(
            cast(str, raw["tool"]),
            cast(str, raw["rule"]),
            cast(str, raw["path"]),
            cast(str, raw["subject"]),
            cast(str, raw["message"]),
            cast(str, raw["severity"]),
            line,
            metric,
        )
    except (TypeError, ValueError) as exc:
        raise JavaEvidenceError(f"invalid Java evidence finding: {exc}") from exc


def _object(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise JavaEvidenceError(f"{label} must be an object")
    raw = cast(dict[object, Any], payload)
    if any(not isinstance(key, str) for key in raw):
        raise JavaEvidenceError(f"{label} must use string keys")
    return cast(dict[str, Any], raw)


def _integer(payload: Any, label: str) -> int:
    if not isinstance(payload, int) or isinstance(payload, bool):
        raise JavaEvidenceError(f"{label} must be an integer")
    return payload


def _optional_integer(payload: Any, label: str) -> int | None:
    if payload is None:
        return None
    return _integer(payload, label)
