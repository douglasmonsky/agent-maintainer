"""Security scanner check catalog helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from guardrail_lib.config.schema import GITLEAKS_SCANNER, GuardrailConfig
from scripts import guardrail_models as models
from scripts.run_secret_scan import (
    CURRENT_TREE_MODE,
    HISTORY_MODE,
    RANGE_MODE,
    STAGED_MODE,
)

SECRET_SCAN_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_SECRET_SCANNING=1 or "
    "[tool.ai_guardrails].enable_secret_scanning = true"
)  # nosec B105 - this is a user-facing scanner enablement hint, not a credential.


SEMGREP_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_SEMGREP=1 or "
    "[tool.ai_guardrails].enable_semgrep = true"
)
OSV_SCANNER_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_OSV_SCANNER=1 or "
    "[tool.ai_guardrails].enable_osv_scanner = true"
)
TRIVY_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_TRIVY=1 or "
    "[tool.ai_guardrails].enable_trivy = true"
)
SBOM_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_SBOM=1 or "
    "[tool.ai_guardrails].enable_sbom = true"
)
LICENSE_CHECK_SKIP_REASON = (
    "disabled by default; enable with GUARDRAILS_ENABLE_LICENSE_CHECK=1 or "
    "[tool.ai_guardrails].enable_license_check = true"
)


def osv_scanner_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build optional OSV Scanner checks for mixed-ecosystem repositories."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    report_path = artifacts_dir / "osv-scanner.json"
    report_path_text = str(report_path)
    artifact_paths = (report_path_text,)
    command = [
        "osv-scanner",
        *config.osv_scanner_args,
        "--format",
        "json",
        "--output-file",
        report_path_text,
    ]
    profiles = frozenset(config.osv_scanner_profiles)
    if not config.enable_osv_scanner:
        return [
            models.Check(
                "osv-scanner",
                command,
                profiles,
                optional_skip_reason=OSV_SCANNER_SKIP_REASON,
                artifact_paths=artifact_paths,
            )
        ]
    return [
        models.Check(
            "osv-scanner",
            command,
            profiles,
            required_executable="osv-scanner",
            artifact_paths=artifact_paths,
        )
    ]


def trivy_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build optional Trivy filesystem checks for container or IaC repositories."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    report_path = artifacts_dir / "trivy.json"
    report_path_text = str(report_path)
    artifact_paths = (report_path_text,)
    command = ["trivy", *config.trivy_args, "--output", report_path_text]
    profiles = frozenset(config.trivy_profiles)
    if not config.enable_trivy:
        return [
            models.Check(
                "trivy",
                command,
                profiles,
                optional_skip_reason=TRIVY_SKIP_REASON,
                artifact_paths=artifact_paths,
            )
        ]
    return [
        models.Check(
            "trivy",
            command,
            profiles,
            required_executable="trivy",
            artifact_paths=artifact_paths,
        )
    ]


def sbom_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build optional Python SBOM generation checks."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    report_path = artifacts_dir / "sbom.cdx.json"
    report_path_text = str(report_path)
    artifact_paths = (report_path_text,)
    command = ["cyclonedx-py", *config.sbom_args, "--output-file", report_path_text]
    profiles = frozenset(config.sbom_profiles)
    if not config.enable_sbom:
        return [
            models.Check(
                "sbom",
                command,
                profiles,
                optional_skip_reason=SBOM_SKIP_REASON,
                artifact_paths=artifact_paths,
            )
        ]
    return [
        models.Check(
            "sbom",
            command,
            profiles,
            required_executable="cyclonedx-py",
            artifact_paths=artifact_paths,
        )
    ]


def license_check_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build optional Python license reporting or policy checks."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    report_path = artifacts_dir / "licenses.json"
    report_path_text = str(report_path)
    artifact_paths = (report_path_text,)
    command = ["pip-licenses", *config.license_check_args, "--output-file", report_path_text]
    profiles = frozenset(config.license_check_profiles)
    if not config.enable_license_check:
        return [
            models.Check(
                "license-check",
                command,
                profiles,
                optional_skip_reason=LICENSE_CHECK_SKIP_REASON,
                artifact_paths=artifact_paths,
            )
        ]
    return [
        models.Check(
            "license-check",
            command,
            profiles,
            required_executable="pip-licenses",
            artifact_paths=artifact_paths,
        )
    ]


def semgrep_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build optional Semgrep checks for configured profiles."""

    profiles = frozenset(config.semgrep_profiles)
    if not config.enable_semgrep:
        return [
            models.Check(
                "semgrep",
                ["semgrep", *config.semgrep_args],
                profiles,
                optional_skip_reason=SEMGREP_SKIP_REASON,
            )
        ]
    return [
        models.Check(
            "semgrep",
            ["semgrep", *config.semgrep_args],
            profiles,
            required_executable="semgrep",
        )
    ]


def secret_scan_checks(
    config: GuardrailConfig, base_ref: str, *, staged: bool
) -> list[models.Check]:
    """Build configured secret scanner checks."""
    normal_profiles = frozenset(config.secret_scan_profiles)
    history_profiles = frozenset(config.secret_scan_history_profiles)
    if not config.enable_secret_scanning:
        return [
            models.Check(
                "secret-scan",
                ["secret-scan"],
                normal_profiles,
                optional_skip_reason=SECRET_SCAN_SKIP_REASON,
            ),
            models.Check(
                "secret-scan-history",
                ["secret-scan-history"],
                history_profiles,
                optional_skip_reason=SECRET_SCAN_SKIP_REASON,
            ),
        ]
    return [
        *normal_secret_scan_checks(config, base_ref, normal_profiles, staged=staged),
        *history_secret_scan_checks(config, history_profiles),
    ]


def normal_secret_scan_checks(
    config: GuardrailConfig,
    base_ref: str,
    profiles: frozenset[str],
    *,
    staged: bool,
) -> list[models.Check]:
    """Build non-history secret scan checks for configured profiles."""
    checks: list[models.Check] = []
    for profile in sorted(profiles):
        mode = secret_scan_mode(profile, staged=staged)
        checks.append(secret_scan_check(config, "secret-scan", profile, mode, base_ref))
    return checks


def history_secret_scan_checks(
    config: GuardrailConfig, profiles: frozenset[str]
) -> list[models.Check]:
    """Build full-history secret scan checks for manual security profiles."""
    return [
        secret_scan_check(config, "secret-scan-history", profile, HISTORY_MODE, "HEAD")
        for profile in sorted(profiles)
    ]


def secret_scan_mode(profile: str, *, staged: bool) -> str:
    """Return secret scanning mode for a verifier profile."""
    if profile == models.CI_PROFILE:
        return RANGE_MODE
    if staged:
        return STAGED_MODE
    return CURRENT_TREE_MODE


def secret_scan_check(
    config: GuardrailConfig,
    name: str,
    profile: str,
    mode: str,
    base_ref: str,
) -> models.Check:
    """Build one secret scan check."""
    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    report_name = f"{name}-{profile}.json"
    command = [
        sys.executable,
        "-m",
        "scripts.run_secret_scan",
        "--backend",
        config.secret_scanner,
        "--mode",
        mode,
        "--base-ref",
        base_ref,
        "--report-path",
        str(artifacts_dir / report_name),
    ]
    required_executable = GITLEAKS_SCANNER if config.secret_scanner == GITLEAKS_SCANNER else None
    return models.Check(
        name,
        command,
        frozenset((profile,)),
        required_paths=("scripts/run_secret_scan.py",),
        required_executable=required_executable,
        artifact_paths=(str(artifacts_dir / report_name),),
    )
