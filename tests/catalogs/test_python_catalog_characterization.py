"""Characterization tests for the current Python-heavy check catalog."""

from __future__ import annotations

import sys
from dataclasses import replace

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.catalogs import python as python_catalog
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.ecosystems.python.provider import PythonProvider
from agent_maintainer.models import (
    CI_PROFILE,
    FAST_PROFILE,
    FULL_PROFILE,
    MANUAL_PROFILE,
    PRECOMMIT_PROFILE,
    SECURITY_PROFILE,
    Check,
)

ENABLED_SECRET_SCAN_CHECK_COUNT = 2


def _default_checks() -> list[Check]:
    return maintainer_catalog.make_checks(
        MaintainerConfig(),
        "HEAD",
        "origin/main",
    )


def _checks_by_name(checks: list[Check]) -> dict[str, Check]:
    return {check.name: check for check in checks}


def _profile_names(checks: list[Check], profile: str) -> list[str]:
    return [check.name for check in checks if profile in check.profiles]


def _module_command(check: Check) -> list[str]:
    return check.command[:3]


def test_python_provider_exposes_current_python_owned_checks() -> None:
    """Pin the private Python provider seam introduced before refactoring."""
    provider = PythonProvider()
    checks = provider.checks(
        EcosystemCheckContext(
            config=MaintainerConfig(),
            compare_branch="origin/main",
            package_paths=("src",),
        )
    )

    assert [check.name for check in checks] == [
        "ruff-format",
        "ruff",
        "pyright",
        "pyright-strict-ratchet",
        "pytest-coverage",
        "mutmut-target-ratchet",
        "radon-cc-report",
        "radon-mi-report",
        "xenon-complexity-gate",
        "pylint",
        "deptry",
        "vulture",
        "bandit",
        "pip-audit",
        "mutmut",
        "wemake",
        "interrogate",
        "diff-cover",
    ]
    assert (
        provider.checks_by_name(
            EcosystemCheckContext(
                config=MaintainerConfig(),
                compare_branch="origin/main",
                package_paths=("src",),
            )
        )["pyright"].name
        == "pyright"
    )


def test_default_catalog_profile_membership_is_characterized() -> None:
    """Protect the current Python check set before provider extraction."""
    checks = _default_checks()

    assert _profile_names(checks, FAST_PROFILE) == [
        "file-length",
        "structure-cohesion",
        "change-budget",
        "suppression-budget",
        "verification-plan-policy",
        "contract-compatibility",
        "ruff",
    ]
    assert _profile_names(checks, PRECOMMIT_PROFILE) == [
        "file-length",
        "structure-cohesion",
        "change-budget",
        "suppression-budget",
        "verification-plan-policy",
        "contract-compatibility",
        "ruff-format",
        "ruff",
        "pyright",
        "pytest-coverage",
        "xenon-complexity-gate",
        "docsync",
    ]
    assert _profile_names(checks, FULL_PROFILE) == [
        "file-length",
        "structure-cohesion",
        "change-budget",
        "suppression-budget",
        "verification-plan-policy",
        "contract-compatibility",
        "ruff-format",
        "ruff",
        "pyright",
        "pytest-coverage",
        "mutmut-target-ratchet",
        "radon-cc-report",
        "radon-mi-report",
        "xenon-complexity-gate",
        "pylint",
        "import-linter",
        "deptry",
        "vulture",
        "bandit",
        "pip-audit",
        "secret-scan",
        "actionlint",
        "zizmor",
        "wemake",
        "interrogate",
        "markdownlint",
        "yamllint",
        "taplo",
        "check-jsonschema",
        "docsync",
    ]
    assert _profile_names(checks, CI_PROFILE) == [
        "file-length",
        "structure-cohesion",
        "change-budget",
        "suppression-budget",
        "verification-plan-policy",
        "contract-compatibility",
        "ruff-format",
        "ruff",
        "pyright",
        "pytest-coverage",
        "mutmut-target-ratchet",
        "radon-cc-report",
        "radon-mi-report",
        "xenon-complexity-gate",
        "pylint",
        "import-linter",
        "deptry",
        "vulture",
        "bandit",
        "pip-audit",
        "sbom",
        "secret-scan",
        "actionlint",
        "zizmor",
        "wemake",
        "interrogate",
        "markdownlint",
        "yamllint",
        "taplo",
        "check-jsonschema",
        "docsync",
        "diff-cover",
    ]
    assert _profile_names(checks, SECURITY_PROFILE) == ["secret-scan-history"]
    assert _profile_names(checks, MANUAL_PROFILE) == [
        "pyright-strict-ratchet",
        "mutmut",
        "semgrep",
        "osv-scanner",
        "trivy",
        "license-check",
    ]


def test_python_tool_commands_and_artifacts_are_characterized() -> None:
    """Pin key Python commands and structured artifacts."""
    checks = _checks_by_name(_default_checks())

    assert _module_command(checks["ruff"]) == [
        sys.executable,
        "-m",
        "agent_maintainer.runners.ruff",
    ]
    assert checks["ruff"].artifact_paths == (".verify-logs/ruff.json",)
    assert checks["ruff"].required_executable == "ruff"

    assert _module_command(checks["pyright"]) == [
        sys.executable,
        "-m",
        "agent_maintainer.runners.pyright",
    ]
    assert checks["pyright"].artifact_paths == (
        ".verify-logs/pyright.json",
        ".verify-logs/pyrightconfig.generated.json",
    )
    assert checks["pyright"].required_executable == "pyright"
    assert checks["docsync"].command == [
        sys.executable,
        "-m",
        "docsync",
        "check",
        "--base",
        "HEAD",
        "--write-reports",
    ]
    assert checks["docsync"].artifact_paths == (".docsync/out/report.json",)

    pytest_check = checks["pytest-coverage"]
    assert pytest_check.command[:6] == [
        "pytest",
        "-q",
        "--tb=short",
        "--disable-warnings",
        "-p",
        "no:tach",
    ]
    assert "--cov=src" in pytest_check.command
    assert "--cov-report=json:.verify-logs/coverage.json" in pytest_check.command
    assert "--junitxml=.verify-logs/pytest-junit.xml" in pytest_check.command
    assert "--cov-fail-under=80" in pytest_check.command
    assert pytest_check.artifact_paths == (
        "coverage.xml",
        ".verify-logs/coverage.json",
        ".verify-logs/pytest-junit.xml",
    )

    assert _module_command(checks["bandit"]) == [
        sys.executable,
        "-m",
        "agent_maintainer.runners.bandit",
    ]
    assert checks["bandit"].artifact_paths == (".verify-logs/bandit.json",)
    assert checks["bandit"].required_executable == "bandit"

    assert checks["diff-cover"].command == [
        "diff-cover",
        "coverage.xml",
        "--compare-branch=origin/main",
        "--fail-under=90",
    ]


def test_optional_scanner_skip_contract_is_characterized() -> None:
    """Pin disabled-by-default optional entries and structured outputs."""
    checks = _checks_by_name(_default_checks())

    for name in (
        "pip-audit",
        "mutmut",
        "semgrep",
        "osv-scanner",
        "trivy",
        "sbom",
        "license-check",
        "secret-scan",
        "secret-scan-history",
    ):
        assert checks[name].optional_skip_reason is not None

    pip_audit_skip = checks["pip-audit"].optional_skip_reason
    assert pip_audit_skip is not None
    assert "enable_pip_audit" in pip_audit_skip
    assert checks["semgrep"].artifact_paths == (".verify-logs/semgrep.json",)
    assert checks["osv-scanner"].artifact_paths == (".verify-logs/osv-scanner.json",)
    assert checks["trivy"].artifact_paths == (".verify-logs/trivy.json",)
    assert checks["sbom"].artifact_paths == (".verify-logs/sbom.cdx.json",)
    assert checks["license-check"].artifact_paths == (".verify-logs/licenses.json",)


def test_enabled_pip_audit_has_bounded_runtime() -> None:
    """Enabled pip-audit does not inherit the broad generic timeout."""

    config = replace(
        MaintainerConfig(),
        enable_pip_audit=True,
        pip_audit_args=("-r", "requirements.txt"),
    )
    checks = _checks_by_name(maintainer_catalog.make_checks(config, "HEAD", "origin/main"))

    assert checks["pip-audit"].timeout_seconds == python_catalog.PIP_AUDIT_TIMEOUT_SECONDS


def test_enabled_pip_audit_preserves_pinned_lock_fast_args() -> None:
    """Pinned-lock pip-audit args are preserved before report arguments."""

    args = (
        "-r",
        "config/dev-lock.txt",
        "--no-deps",
        "--disable-pip",
        "--progress-spinner",
        "off",
        "--timeout",
        "20",
    )
    config = replace(MaintainerConfig(), enable_pip_audit=True, pip_audit_args=args)
    checks = _checks_by_name(maintainer_catalog.make_checks(config, "HEAD", "origin/main"))

    assert checks["pip-audit"].command[: 1 + len(args)] == ["pip-audit", *args]
    assert checks["pip-audit"].command[-4:] == [
        "--format",
        "json",
        "--output",
        ".verify-logs/pip-audit.json",
    ]


def test_enabled_secret_scan_uses_runner_and_redacted_artifacts() -> None:
    """Characterize enabled secret scanning without requiring Gitleaks."""
    config = replace(
        MaintainerConfig(),
        diagnostic_artifacts_dir=".custom-logs",
        enable_secret_scanning=True,
    )
    checks = maintainer_catalog.make_checks(
        config,
        "HEAD",
        "origin/main",
        staged=True,
    )
    secret_checks = [check for check in checks if check.name == "secret-scan"]

    assert len(secret_checks) == ENABLED_SECRET_SCAN_CHECK_COUNT
    ci_check = next(check for check in secret_checks if check.profiles == frozenset((CI_PROFILE,)))
    full_check = next(
        check for check in secret_checks if check.profiles == frozenset((FULL_PROFILE,))
    )

    assert _module_command(ci_check) == [
        sys.executable,
        "-m",
        "agent_maintainer.runners.secret_scan",
    ]
    assert "--mode" in ci_check.command
    assert "range" in ci_check.command
    assert ci_check.artifact_paths == (".custom-logs/secret-scan-ci.json",)
    assert ci_check.artifact_sensitivity == "redacted-secrets"
    assert ci_check.required_executable == "gitleaks"

    assert "staged" in full_check.command
    assert full_check.artifact_paths == (".custom-logs/secret-scan-full.json",)
