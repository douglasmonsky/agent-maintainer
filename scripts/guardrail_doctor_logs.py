"""Doctor checks for verifier diagnostic artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from guardrail_lib.verify.artifacts import LAST_FAILURE_NAME, MANIFEST_NAME
from scripts import guardrail_config
from scripts.guardrail_catalog import make_checks
from scripts.guardrail_doctor_models import (
    DISABLED,
    MISSING,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)

VERIFY_LOG_DIR = ".verify-logs"


def check_recent_logs(
    repo_root: Path, config: guardrail_config.GuardrailConfig | None = None
) -> DoctorResult:
    """Report whether recent verifier logs and artifacts are coherent."""

    if config and not config.diagnostic_artifacts_enabled:
        return DoctorResult(
            "verification-logs",
            OK,
            "diagnostic artifacts disabled.",
            state=DISABLED,
        )
    log_dir_name = config.diagnostic_artifacts_dir if config else VERIFY_LOG_DIR
    log_dir = repo_root / log_dir_name
    logs = recent_logs(log_dir)
    manifest = log_dir / MANIFEST_NAME
    preflight = preflight_result(log_dir, log_dir_name, logs, manifest)
    if preflight is not None:
        return preflight

    payload = read_manifest(manifest)
    if payload is None:
        return DoctorResult(
            "verification-logs",
            WARNING,
            f"{MANIFEST_NAME} is invalid JSON.",
            state=UNSAFE_CONFIG,
            hint="Remove stale verification logs or rerun verifier.",
        )
    issues = manifest_issues(repo_root, log_dir, logs[0], manifest, payload)
    if config is not None:
        issues.extend(catalog_drift_issues(config, payload))
    if issues:
        return DoctorResult(
            "verification-logs",
            WARNING,
            "; ".join(issues),
            state=issue_state(issues),
            hint="Rerun the relevant guardrail verify profile.",
        )
    return ok_result(logs[0], payload)


def recent_logs(log_dir: Path) -> list[Path]:
    """Return raw verifier logs newest first."""

    if not log_dir.exists():
        return []
    return sorted(log_dir.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)


def preflight_result(
    log_dir: Path,
    log_dir_name: str,
    logs: list[Path],
    manifest: Path,
) -> DoctorResult | None:
    """Return an early verifier-log diagnostic when required files are absent."""

    if not log_dir.exists():
        return DoctorResult(
            "verification-logs",
            WARNING,
            f"{log_dir_name}/ is absent.",
            state=MISSING,
        )
    if not logs:
        return DoctorResult(
            "verification-logs",
            WARNING,
            f"No logs found in {log_dir_name}/.",
            state=MISSING,
        )
    if not manifest.exists():
        return DoctorResult(
            "verification-logs",
            WARNING,
            f"{MANIFEST_NAME} is absent.",
            state=MISSING,
        )
    return None


def read_manifest(manifest: Path) -> dict[str, object] | None:
    """Read a verifier manifest, returning None when it is malformed."""

    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def manifest_issues(
    repo_root: Path,
    log_dir: Path,
    latest_log: Path,
    manifest: Path,
    payload: dict[str, object],
) -> list[str]:
    """Return stale or missing artifact problems for a manifest."""

    issues: list[str] = []
    if manifest.stat().st_mtime < latest_log.stat().st_mtime:
        issues.append(f"{MANIFEST_NAME} is older than {latest_log.name}")
    issues.extend(referenced_path_issues(repo_root, payload))
    issues.extend(failure_note_issues(log_dir, payload))
    return issues


def catalog_drift_issues(
    config: guardrail_config.GuardrailConfig, payload: dict[str, object]
) -> list[str]:
    """Return manifest checks absent from current check catalog."""

    current_names = {check.name for check in make_checks(config, "HEAD", "origin/main")}
    stale_names = sorted(
        {
            str(check.get("name", "unknown"))
            for check in manifest_checks(payload)
            if str(check.get("name", "unknown")) not in current_names
        }
    )
    if not stale_names:
        return []
    stale_list = ", ".join(stale_names)
    return [f"latest manifest references disabled or removed check(s): {stale_list}"]


def issue_state(issues: list[str]) -> str:
    """Return doctor state for verification-log issues."""

    if any("disabled or removed" in issue or "invalid JSON" in issue for issue in issues):
        return UNSAFE_CONFIG
    return MISSING


def referenced_path_issues(repo_root: Path, payload: dict[str, object]) -> list[str]:
    """Return missing log or artifact references from a manifest."""

    issues: list[str] = []
    for check in manifest_checks(payload):
        name = str(check.get("name", "unknown"))
        log_path = check.get("log_path")
        if missing_manifest_path(repo_root, log_path):
            issues.append(f"{name} log is missing")
        for artifact_path in manifest_artifact_paths(check):
            if missing_manifest_path(repo_root, artifact_path):
                issues.append(f"{name} artifact is missing: {artifact_path}")
    return issues


def missing_manifest_path(repo_root: Path, value: object) -> bool:
    """Return whether a manifest path value points at a missing file."""

    return isinstance(value, str) and bool(value) and not resolve_path(repo_root, value).exists()


def manifest_artifact_paths(check: dict[str, object]) -> list[object]:
    """Return raw artifact path entries from a manifest check."""

    raw_paths = check.get("artifacts", [])
    return raw_paths if isinstance(raw_paths, list) else []


def manifest_checks(payload: dict[str, object]) -> list[dict[str, object]]:
    """Return manifest check entries with a stable shape."""

    raw_checks = payload.get("checks", [])
    if not isinstance(raw_checks, list):
        return []
    return [item for item in raw_checks if isinstance(item, dict)]


def resolve_path(repo_root: Path, value: str) -> Path:
    """Resolve a manifest path relative to the repository root."""

    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def failure_note_issues(log_dir: Path, payload: dict[str, object]) -> list[str]:
    """Return LAST_FAILURE drift issues for the latest manifest."""

    failure_note = log_dir / LAST_FAILURE_NAME
    failed_checks = [check for check in manifest_checks(payload) if check.get("status") == "failed"]
    if failed_checks and not failure_note.exists():
        return [f"{LAST_FAILURE_NAME} is absent for failed latest run"]
    if not failed_checks and failure_note.exists():
        return [f"{LAST_FAILURE_NAME} is stale after a passing latest run"]
    return []


def ok_result(latest_log: Path, payload: dict[str, object]) -> DoctorResult:
    """Return the successful verifier-log doctor result."""

    generated_at = payload.get("generated_at", "unknown time")
    profile = payload.get("profile", "unknown profile")
    return DoctorResult(
        "verification-logs",
        OK,
        f"Latest run: {profile} at {generated_at}; latest log: {latest_log.name}",
    )
