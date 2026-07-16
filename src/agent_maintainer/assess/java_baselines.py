"""Explicit Java findings baseline lifecycle from bounded runner evidence."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed local Git inspection commands only
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

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


class JavaBaselineLifecycleError(ValueError):
    """One invalid or unsafe Java baseline lifecycle request."""


@dataclass(frozen=True)
class JavaBaselineEvidence:
    """Complete findings tied to the exact repository commit that produced them."""

    source_commit: str
    findings: tuple[JavaFinding, ...]


def create_from_artifact(
    target: Path,
    configured_path: str,
    artifact_path: Path,
) -> tuple[Path, baseline.JavaFindingsBaseline]:
    """Build a new baseline candidate from successful, current evidence."""
    root = _repository_root(target)
    _require_clean_worktree(root)
    evidence = _read_evidence(root, artifact_path)
    destination = _confined_path(root, Path(configured_path), "baseline")
    candidate = baseline.create_baseline(
        evidence.findings,
        source_commit=evidence.source_commit,
    )
    return destination, candidate


def prune_from_artifact(
    target: Path,
    configured_path: str,
    artifact_path: Path,
) -> tuple[Path, baseline.JavaFindingsBaseline]:
    """Build a candidate that only removes or lowers recorded debt."""
    root = _repository_root(target)
    _require_clean_worktree(root)
    evidence = _read_evidence(root, artifact_path)
    destination = _confined_path(root, Path(configured_path), "baseline")
    try:
        stored = baseline.read_baseline(destination)
    except (OSError, ValueError) as exc:
        raise JavaBaselineLifecycleError(f"invalid Java findings baseline: {exc}") from exc
    comparison = baseline.compare_baseline(stored, evidence.findings)
    if not comparison.passed:
        raise JavaBaselineLifecycleError("prune evidence contains new or regressed Java findings")
    candidate = baseline.prune_baseline(
        stored,
        evidence.findings,
        source_commit=evidence.source_commit,
    )
    return destination, candidate


def inspect_configured(
    target: Path,
    configured_path: str,
) -> baseline.JavaBaselineSummary:
    """Read and summarize the configured baseline without changing repository state."""
    root = _repository_root(target)
    destination = _confined_path(root, Path(configured_path), "baseline")
    try:
        return baseline.inspect_baseline(baseline.read_baseline(destination))
    except (OSError, ValueError) as exc:
        raise JavaBaselineLifecycleError(f"invalid Java findings baseline: {exc}") from exc


def render_summary(summary: baseline.JavaBaselineSummary, *, json_output: bool) -> str:
    """Render a deterministic machine or human baseline summary."""
    values = asdict(summary)
    if json_output:
        return f"{json.dumps(values, indent=2, sort_keys=True)}\n"
    return "\n".join(f"{key}: {value}" for key, value in values.items()) + "\n"


def render_candidate(candidate: baseline.JavaFindingsBaseline) -> str:
    """Render one lifecycle candidate through the canonical baseline codec."""
    return baseline.render_baseline(candidate)


def write_candidate(
    path: Path,
    candidate: baseline.JavaFindingsBaseline,
    *,
    overwrite: bool,
) -> None:
    """Persist one reviewed lifecycle candidate at its confined destination."""
    baseline.write_baseline(path, candidate, force=overwrite)


def _read_evidence(target: Path, artifact_path: Path) -> JavaBaselineEvidence:
    path = _confined_path(target, artifact_path, "artifact")
    try:
        if not path.is_file():
            raise JavaBaselineLifecycleError(f"Java evidence artifact is not a file: {path}")
        with path.open("rb") as handle:
            raw = handle.read(artifacts.MAX_ARTIFACT_BYTES + 1)
    except OSError as exc:
        raise JavaBaselineLifecycleError(f"could not read Java evidence artifact: {exc}") from exc
    if len(raw) > artifacts.MAX_ARTIFACT_BYTES:
        raise JavaBaselineLifecycleError("Java evidence artifact exceeds the size limit")
    try:
        payload: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JavaBaselineLifecycleError("Java evidence artifact is malformed JSON") from exc
    return _parse_evidence(payload, _repository_head(target))


def _parse_evidence(payload: Any, current_head: str) -> JavaBaselineEvidence:
    root = _object(payload, "Java evidence artifact")
    _validate_artifact_header(root)
    _validate_observation(root)
    reports = _object(root.get("reports"), "Java evidence reports")
    return _parse_reports(reports, current_head)


def _validate_artifact_header(root: dict[str, Any]) -> None:
    if root.get("schema_version") != 1 or root.get("provider") != "java-gradle":
        raise JavaBaselineLifecycleError("Java evidence artifact has an unsupported schema")
    if root.get("reports_parsed") is not True:
        raise JavaBaselineLifecycleError("Java evidence artifact has no parsed reports")
    if root.get("evidence_status") not in VALID_EVIDENCE_STATUSES:
        raise JavaBaselineLifecycleError("Java evidence artifact was not successfully validated")


def _validate_observation(root: dict[str, Any]) -> None:
    observation = _object(root.get("observation"), "Java evidence observation")
    if _integer(observation.get("exit_code"), "observation.exit_code") != 0:
        raise JavaBaselineLifecycleError("Java evidence artifact records a failed Gradle run")


def _parse_reports(reports: dict[str, Any], current_head: str) -> JavaBaselineEvidence:
    if reports.get("findings_truncated") is not False:
        raise JavaBaselineLifecycleError("Java evidence findings are incomplete or truncated")
    source_commit = _validated_source_commit(reports.get("source_commit"), current_head)
    raw_findings = reports.get("findings")
    if not isinstance(raw_findings, list):
        raise JavaBaselineLifecycleError("Java evidence findings must be an array")
    finding_items = cast(list[Any], raw_findings)
    if len(finding_items) > report_evidence.MAX_ARTIFACT_FINDINGS:
        raise JavaBaselineLifecycleError("Java evidence contains too many finding facts")
    finding_count = _integer(reports.get("finding_count"), "reports.finding_count")
    if finding_count != len(finding_items):
        raise JavaBaselineLifecycleError("Java evidence finding count does not match its facts")
    findings = tuple(_parse_finding(item) for item in finding_items)
    return JavaBaselineEvidence(source_commit.lower(), findings)


def _validated_source_commit(payload: Any, current_head: str) -> str:
    if not isinstance(payload, str) or baseline.COMMIT_PATTERN.fullmatch(payload) is None:
        raise JavaBaselineLifecycleError("Java evidence source_commit is invalid")
    if payload.lower() != current_head:
        raise JavaBaselineLifecycleError("Java evidence is stale for the current repository HEAD")
    return payload


def _parse_finding(payload: Any) -> JavaFinding:
    raw = _object(payload, "Java evidence finding")
    if frozenset(raw) != EXPECTED_FINDING_FIELDS:
        raise JavaBaselineLifecycleError("Java evidence finding has unexpected fields")
    strings = ("tool", "rule", "path", "subject", "message", "severity", "fingerprint")
    if any(not isinstance(raw[field], str) for field in strings):
        raise JavaBaselineLifecycleError("Java evidence finding text fields must be strings")
    line = _optional_integer(raw["line"], "finding.line")
    metric = _optional_integer(raw["metric"], "finding.metric")
    try:
        finding = JavaFinding(
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
        raise JavaBaselineLifecycleError(f"invalid Java evidence finding: {exc}") from exc
    if raw["fingerprint"] != finding.fingerprint:
        raise JavaBaselineLifecycleError(
            "Java evidence finding fingerprint does not match identity"
        )
    return finding


def _repository_root(target: Path) -> Path:
    try:
        root = target.resolve(strict=True)
    except OSError as exc:
        raise JavaBaselineLifecycleError(f"invalid target repository: {exc}") from exc
    if not root.is_dir():
        raise JavaBaselineLifecycleError(f"target repository is not a directory: {root}")
    _repository_head(root)
    return root


def _repository_head(target: Path) -> str:
    completed = _run_git(target, "rev-parse", "HEAD")
    head = completed.stdout.strip().lower()
    if completed.returncode != 0 or baseline.COMMIT_PATTERN.fullmatch(head) is None:
        raise JavaBaselineLifecycleError("target must be a Git repository with a valid HEAD")
    return head


def _require_clean_worktree(target: Path) -> None:
    completed = _run_git(target, "status", "--porcelain", "--untracked-files=all")
    if completed.returncode != 0:
        raise JavaBaselineLifecycleError("could not inspect target Git worktree")
    if completed.stdout:
        raise JavaBaselineLifecycleError("Java baseline changes require a clean Git worktree")


def _run_git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # nosec B603
            ("git", "-C", str(target), *args),
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
    except OSError as exc:
        raise JavaBaselineLifecycleError(f"could not run Git: {exc}") from exc


def _confined_path(target: Path, configured: Path, label: str) -> Path:
    candidate = configured if configured.is_absolute() else target / configured
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(target)
    except ValueError as exc:
        raise JavaBaselineLifecycleError(
            f"Java {label} path escapes the target repository"
        ) from exc
    return resolved


def _object(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise JavaBaselineLifecycleError(f"{label} must be an object")
    raw = cast(dict[object, Any], payload)
    if any(not isinstance(key, str) for key in raw):
        raise JavaBaselineLifecycleError(f"{label} must use string keys")
    return cast(dict[str, Any], raw)


def _integer(payload: Any, label: str) -> int:
    if not isinstance(payload, int) or isinstance(payload, bool):
        raise JavaBaselineLifecycleError(f"{label} must be an integer")
    return payload


def _optional_integer(payload: Any, label: str) -> int | None:
    if payload is None:
        return None
    return _integer(payload, label)
