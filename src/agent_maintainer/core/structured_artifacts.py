"""Structured diagnostic artifact dispatch for verifier repair output."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from agent_maintainer.core.structured_pytest import summarize_pytest_artifacts
from agent_maintainer.core.structured_security import (
    summarize_gitleaks_payload,
    summarize_osv_payload,
    summarize_pip_audit_payload,
    summarize_semgrep_payload,
)
from agent_maintainer.core.structured_values import json_array, json_object, plain_int

JsonFormatter = Callable[[object], str | None]
JsonMatcher = Callable[[Path], bool]
ArtifactSummarizer = Callable[[tuple[str, ...]], str | None]


def structured_artifact_summary(
    check_name: str,
    artifact_paths: tuple[str, ...],
) -> str | None:
    """Return compact summary from high-value structured artifacts."""

    summarizers: dict[str, ArtifactSummarizer] = {
        "pytest-coverage": summarize_pytest_artifacts,
        "semgrep": lambda paths: summarize_json_artifact(
            paths,
            "semgrep.json",
            summarize_semgrep_payload,
        ),
        "osv-scanner": lambda paths: summarize_json_artifact(
            paths,
            "osv-scanner.json",
            summarize_osv_payload,
        ),
        "secret-scan": summarize_secret_scan_artifact,
        "secret-scan-history": summarize_secret_scan_artifact,
        "pip-audit": lambda paths: summarize_json_artifact(
            paths,
            "pip-audit.json",
            summarize_pip_audit_payload,
        ),
        "java-gradle-static": summarize_java_artifact,
        "java-gradle-tests": summarize_java_artifact,
    }
    summarizer = summarizers.get(check_name)
    return summarizer(artifact_paths) if summarizer else None


def summarize_secret_scan_artifact(artifact_paths: tuple[str, ...]) -> str | None:
    """Summarize redacted secret-scan artifact."""

    return summarize_json_artifact_by_name(
        artifact_paths,
        lambda path: path.name.startswith("secret-scan") and path.suffix == ".json",
        summarize_gitleaks_payload,
    )


def summarize_java_artifact(artifact_paths: tuple[str, ...]) -> str | None:
    """Summarize one sanitized Java Gradle artifact."""
    return summarize_json_artifact_by_name(
        artifact_paths,
        lambda path: path.name.startswith("java-gradle-") and path.suffix == ".json",
        summarize_java_payload,
    )


def summarize_java_payload(value: object) -> str | None:
    """Return concise findings and test totals from a Java artifact payload."""
    payload = json_object(value)
    if payload is None or payload.get("provider") != "java-gradle":
        return None
    reports = json_object(payload.get("reports"))
    if reports is None:
        return None
    lines = _java_summary_lines(reports)
    return "\n".join(lines) if lines else None


def _java_summary_lines(reports: dict[str, object]) -> list[str]:
    lines: list[str] = []
    baseline = json_object(reports.get("baseline"))
    finding_count = plain_int(reports.get("finding_count"))
    if finding_count or baseline is not None:
        baseline = baseline or {}
        regressions = json_array(baseline.get("metric_regressions")) or []
        lines.append(
            f"java findings: {finding_count} reported, "
            f"{plain_int(baseline.get('new_occurrences'))} new, "
            f"{len(regressions)} metric regressions"
        )
    tests = json_object(reports.get("tests"))
    if tests is not None:
        lines.append(
            f"java tests: {plain_int(tests.get('tests'))} run, "
            f"{plain_int(tests.get('failures'))} failures, "
            f"{plain_int(tests.get('errors'))} errors, "
            f"{plain_int(tests.get('skipped'))} skipped"
        )
    return lines


def summarize_json_artifact(
    artifact_paths: tuple[str, ...],
    suffix: str,
    formatter: JsonFormatter,
) -> str | None:
    """Load matching JSON artifact and return formatter output when possible."""

    return summarize_json_artifact_by_name(
        artifact_paths,
        lambda path: path.as_posix().endswith(suffix),
        formatter,
    )


def summarize_json_artifact_by_name(
    artifact_paths: tuple[str, ...],
    matcher: JsonMatcher,
    formatter: JsonFormatter,
) -> str | None:
    """Load first JSON artifact matching predicate."""

    path = next((Path(item) for item in artifact_paths if matcher(Path(item))), None)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return formatter(payload)
