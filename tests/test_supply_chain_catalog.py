"""Tests for supply-chain guardrail catalog checks."""

from __future__ import annotations

from dataclasses import replace

from scripts.guardrail_catalogs import catalog as guardrail_catalog
from scripts.guardrail_core.config import GuardrailConfig
from scripts.guardrail_models import CI_PROFILE, MANUAL_PROFILES


def test_osv_scanner_check_is_disabled_by_default_and_manual_when_enabled() -> None:
    default_checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "osv-scanner")

    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None
    assert disabled.required_executable is None

    enabled_checks = guardrail_catalog.make_checks(
        replace(
            GuardrailConfig(),
            enable_osv_scanner=True,
            osv_scanner_args=("scan", "source", "-r", "."),
            diagnostic_artifacts_dir=".custom-logs",
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "osv-scanner")

    assert enabled.command == [
        "osv-scanner",
        "scan",
        "source",
        "-r",
        ".",
        "--format",
        "json",
        "--output-file",
        ".custom-logs/osv-scanner.json",
    ]
    assert enabled.profiles == MANUAL_PROFILES
    assert enabled.required_executable == "osv-scanner"


def test_trivy_check_is_disabled_by_default_and_manual_when_enabled() -> None:
    default_checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "trivy")

    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None
    assert disabled.required_executable is None

    enabled_checks = guardrail_catalog.make_checks(
        replace(
            GuardrailConfig(),
            enable_trivy=True,
            trivy_args=("fs", "--scanners", "vuln,misconfig", "."),
            diagnostic_artifacts_dir=".custom-logs",
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "trivy")

    assert enabled.command == [
        "trivy",
        "fs",
        "--scanners",
        "vuln,misconfig",
        ".",
        "--output",
        ".custom-logs/trivy.json",
    ]
    assert enabled.profiles == MANUAL_PROFILES
    assert enabled.required_executable == "trivy"


def test_sbom_check_is_disabled_by_default_and_writes_ci_artifact() -> None:
    default_checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "sbom")

    assert disabled.profiles == frozenset((CI_PROFILE,))
    assert disabled.optional_skip_reason is not None
    assert disabled.required_executable is None

    enabled_checks = guardrail_catalog.make_checks(
        replace(
            GuardrailConfig(),
            enable_sbom=True,
            sbom_args=("requirements", "config/dev-lock.txt", "--of", "JSON"),
            sbom_profiles=("ci",),
            diagnostic_artifacts_dir=".custom-logs",
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "sbom")

    assert enabled.command == [
        "cyclonedx-py",
        "requirements",
        "config/dev-lock.txt",
        "--of",
        "JSON",
        "--output-file",
        ".custom-logs/sbom.cdx.json",
    ]
    assert enabled.profiles == frozenset((CI_PROFILE,))
    assert enabled.required_executable == "cyclonedx-py"
    assert enabled.artifact_paths == (".custom-logs/sbom.cdx.json",)


def test_license_check_is_disabled_by_default_and_manual_when_enabled() -> None:
    default_checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "license-check")

    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None
    assert disabled.required_executable is None

    enabled_checks = guardrail_catalog.make_checks(
        replace(
            GuardrailConfig(),
            enable_license_check=True,
            license_check_args=("--from=mixed", "--format=json", "--allow-only=MIT"),
            license_check_profiles=("manual",),
            diagnostic_artifacts_dir=".custom-logs",
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "license-check")

    assert enabled.command == [
        "pip-licenses",
        "--from=mixed",
        "--format=json",
        "--allow-only=MIT",
        "--output-file",
        ".custom-logs/licenses.json",
    ]
    assert enabled.profiles == MANUAL_PROFILES
    assert enabled.required_executable == "pip-licenses"
    assert enabled.artifact_paths == (".custom-logs/licenses.json",)
