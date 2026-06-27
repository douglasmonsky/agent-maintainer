"""Python quality and security checks for the maintenance catalog."""

from __future__ import annotations

import sys
from pathlib import Path

from agent_maintainer import models
from agent_maintainer.config.schema import FRESH_STRICT_MODE, MaintainerConfig


def pytest_command(config: MaintainerConfig) -> list[str]:
    """Build the coverage-enforcing pytest command."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    coverage_json = artifacts_dir / "coverage.json"
    junit_xml = artifacts_dir / "pytest-junit.xml"
    command = ["pytest", "-q", "--tb=short", "--disable-warnings", "-p", "no:tach"]
    command.extend(f"--cov={source}" for source in config.coverage_source)
    command.extend(
        [
            "--cov-report=term-missing:skip-covered",
            "--cov-report=xml",
            f"--cov-report=json:{coverage_json}",
            f"--junitxml={junit_xml}",
            f"--cov-fail-under={config.coverage_fail_under}",
            *config.test_roots,
        ]
    )
    return command


def pytest_check(config: MaintainerConfig) -> models.Check:
    """Build the pytest coverage check or its require-tests skip."""

    if config.require_tests:
        artifacts_dir = Path(config.diagnostic_artifacts_dir)
        return models.Check(
            "pytest-coverage",
            pytest_command(config),
            models.LOCAL_GATE_PROFILES,
            required_executable="pytest",
            artifact_paths=(
                "coverage.xml",
                str(artifacts_dir / "coverage.json"),
                str(artifacts_dir / "pytest-junit.xml"),
            ),
        )
    return models.Check(
        "pytest-coverage",
        ["pytest"],
        models.LOCAL_GATE_PROFILES,
        optional_skip_reason="tests are disabled by require_tests = false",
    )


def diff_cover_check(config: MaintainerConfig, compare_branch: str) -> models.Check:
    """Build the changed-code coverage check for CI profiles."""

    if config.require_tests:
        return models.Check(
            "diff-cover",
            [
                "diff-cover",
                "coverage.xml",
                f"--compare-branch={compare_branch}",
                f"--fail-under={config.diff_cover_fail_under}",
            ],
            models.CI_ONLY_PROFILES,
            required_paths=("coverage.xml", ".git"),
            required_executable="diff-cover",
        )
    return models.Check(
        "diff-cover",
        ["diff-cover"],
        models.CI_ONLY_PROFILES,
        optional_skip_reason="changed-code coverage is disabled because require_tests = false",
    )


def pip_audit_check(config: MaintainerConfig) -> models.Check:
    """Build the dependency vulnerability check or its explicit skip."""

    if not config.enable_pip_audit:
        return models.Check(
            "pip-audit",
            ["pip-audit"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with AGENT_MAINTAINER_ENABLE_PIP_AUDIT=1 or "
                "[tool.agent_maintainer].enable_pip_audit = true"
            ),
        )
    if not config.pip_audit_args:
        if config.mode == FRESH_STRICT_MODE:
            return models.Check(
                "pip-audit",
                [sys.executable, "-m", "agent_maintainer.checks.pip_audit_config"],
                models.FULL_PROFILES,
            )
        return models.Check(
            "pip-audit",
            ["pip-audit"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "enabled without pinned input; skipped to avoid auditing the active environment"
            ),
        )
    return models.Check(
        "pip-audit",
        ["pip-audit", *config.pip_audit_args],
        models.FULL_PROFILES,
        required_executable="pip-audit",
    )


def mutmut_check(config: MaintainerConfig) -> models.Check:
    """Build mutation-testing check reserved for the manual profile."""

    command = [sys.executable, "-m", "agent_maintainer.runners.mutmut", *config.mutmut_args]
    if not config.enable_mutmut:
        return models.Check(
            "mutmut",
            command,
            models.MANUAL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with AGENT_MAINTAINER_ENABLE_MUTMUT=1 or "
                "[tool.agent_maintainer].enable_mutmut = true"
            ),
        )
    return models.Check(
        "mutmut",
        command,
        models.MANUAL_PROFILES,
        required_executable="mutmut",
    )


def pyright_check(config: MaintainerConfig) -> models.Check:
    """Build the Pyright check through the generated-project wrapper."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    return models.Check(
        "pyright",
        [sys.executable, "-m", "agent_maintainer.runners.pyright"],
        models.LOCAL_GATE_PROFILES,
        required_executable="pyright",
        artifact_paths=(
            str(artifacts_dir / "pyright.json"),
            str(artifacts_dir / "pyrightconfig.generated.json"),
        ),
    )


def ruff_check(config: MaintainerConfig) -> models.Check:
    """Build the Ruff check through the JSON-artifact wrapper."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    return models.Check(
        "ruff",
        [sys.executable, "-m", "agent_maintainer.runners.ruff"],
        models.ALL_PROFILES,
        required_executable="ruff",
        artifact_paths=(str(artifacts_dir / "ruff.json"),),
    )


def bandit_check(config: MaintainerConfig) -> models.Check:
    """Build the Bandit check through the JSON-artifact wrapper."""

    artifacts_dir = Path(config.diagnostic_artifacts_dir)
    return models.Check(
        "bandit",
        [sys.executable, "-m", "agent_maintainer.runners.bandit"],
        models.FULL_PROFILES,
        required_executable="bandit",
        artifact_paths=(str(artifacts_dir / "bandit.json"),),
    )


def wemake_check(config: MaintainerConfig, package_paths: tuple[str, ...]) -> models.Check:
    """Build the wemake strict-style check or its explicit skip."""

    if not config.enable_wemake:
        return models.Check(
            "wemake",
            ["flake8"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with AGENT_MAINTAINER_ENABLE_WEMAKE=1 or "
                "[tool.agent_maintainer].enable_wemake = true"
            ),
        )
    return models.Check(
        "wemake",
        [
            "flake8",
            "--require-plugins",
            "wemake-python-styleguide",
            *package_paths,
        ],
        models.FULL_PROFILES,
        required_executable="flake8",
    )


def interrogate_check(config: MaintainerConfig, package_paths: tuple[str, ...]) -> models.Check:
    """Build the docstring coverage check or its explicit optional skip."""

    if not config.enable_interrogate:
        return models.Check(
            "interrogate",
            ["interrogate"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with AGENT_MAINTAINER_ENABLE_INTERROGATE=1 or "
                "[tool.agent_maintainer].enable_interrogate = true"
            ),
        )
    return models.Check(
        "interrogate",
        [
            "interrogate",
            f"--fail-under={config.interrogate_fail_under}",
            "--ignore-init-method",
            "--ignore-init-module",
            "--ignore-private",
            "--ignore-semiprivate",
            "--ignore-magic",
            *package_paths,
        ],
        models.FULL_PROFILES,
        required_executable="interrogate",
    )
