"""Declarative catalog of maintainer checks."""

from __future__ import annotations

import sys

from agent_maintainer import models
from agent_maintainer.catalogs.docs import docs_config_checks
from agent_maintainer.catalogs.security import (
    license_check_checks,
    osv_scanner_checks,
    sbom_checks,
    secret_scan_checks,
    semgrep_checks,
    trivy_checks,
)
from agent_maintainer.config.schema import (
    FRESH_STRICT_MODE,
    IMPORT_LINTER_TOOL,
    TACH_TOOL,
    MaintainerConfig,
)
from agent_maintainer.core.config import existing_paths
from agent_maintainer.ecosystems.models import EcosystemCheckContext
from agent_maintainer.ecosystems.python.provider import PythonProvider

CHANGE_BUDGET_PROFILES = (
    models.FAST_PROFILE,
    models.PRECOMMIT_PROFILE,
    models.FULL_PROFILE,
    models.CI_PROFILE,
)


def existing_or_configured(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Prefer existing paths while preserving configured values for diagnostics."""

    existing = tuple(existing_paths(paths))
    return existing if existing else paths


def architecture_checks(
    config: MaintainerConfig,
    base_ref: str,
    *,
    staged: bool,
) -> list[models.Check]:
    """Build the selected architecture contract checks."""

    if config.architecture_tool == TACH_TOOL:
        return tach_checks(config, base_ref, staged=staged)
    return [
        models.Check(
            IMPORT_LINTER_TOOL,
            ["lint-imports"],
            models.FULL_PROFILES,
            required_executable="lint-imports",
            optional_skip_reason=(
                ".importlinter is absent; architecture contracts are not configured"
            ),
        )
    ]


def tach_checks(
    config: MaintainerConfig,
    base_ref: str,
    *,
    staged: bool,
) -> list[models.Check]:
    """Build Tach config and architecture checks for the selected strictness mode."""

    strict = config.mode == FRESH_STRICT_MODE
    config_command = [sys.executable, "-m", "archguard", "tach-config"]
    if strict:
        config_command.append("--strict-root-module")
    decision_command = [
        sys.executable,
        "-m",
        "archguard",
        "decision-check",
        "--base-ref",
        base_ref,
    ]
    if staged:
        decision_command.append("--staged")
    optional_skip_reason = None
    if not strict:
        optional_skip_reason = "tach.toml is absent; architecture contracts are not configured"
    return [
        models.Check(
            "tach-config",
            config_command,
            models.FULL_PROFILES,
            required_paths=("tach.toml",) if strict else (),
            optional_skip_reason=optional_skip_reason,
        ),
        models.Check(
            "architecture-decision",
            decision_command,
            models.LOCAL_GATE_PROFILES,
            required_paths=(".git",),
            optional_skip_reason=optional_skip_reason,
        ),
        models.Check(
            "tach",
            ["tach", "check", "--exact"],
            models.FULL_PROFILES,
            required_paths=("tach.toml",) if strict else (),
            required_executable="tach",
            optional_skip_reason=optional_skip_reason,
        ),
    ]


def workflow_checks() -> list[models.Check]:
    """Build GitHub Actions workflow quality and security checks."""

    skip_reason = ".github/workflows is absent; GitHub Actions checks are not applicable"
    return [
        models.Check(
            "actionlint",
            ["actionlint", "-no-color", "-oneline"],
            models.FULL_PROFILES,
            required_executable="actionlint",
            optional_skip_reason=skip_reason,
        ),
        models.Check(
            "zizmor",
            ["zizmor", "--offline", "--no-progress", ".github/workflows", ".github/dependabot.yml"],
            models.FULL_PROFILES,
            required_executable="zizmor",
            optional_skip_reason=skip_reason,
        ),
    ]


def make_checks(
    config: MaintainerConfig, base_ref: str, compare_branch: str, *, staged: bool = False
) -> list[models.Check]:
    """Build the complete check catalog for all verifier profiles."""

    package_paths = existing_or_configured(config.package_paths)
    file_length_paths = existing_or_configured(config.file_length_paths)
    python_provider_checks = PythonProvider().checks_by_name(
        EcosystemCheckContext(
            config=config,
            compare_branch=compare_branch,
            package_paths=package_paths,
        )
    )
    return [
        models.Check(
            "file-length",
            file_length_command(config, file_length_paths),
            models.ALL_PROFILES,
        ),
        models.Check(
            "structure-cohesion",
            structure_command(config),
            models.ALL_PROFILES,
            report_success_output=True,
        ),
        *change_budget_checks(config, base_ref, staged=staged),
        models.Check(
            "suppression-budget",
            suppression_budget_command(base_ref, staged=staged),
            models.ALL_PROFILES,
            required_paths=(".git",),
        ),
        python_provider_checks["ruff-format"],
        python_provider_checks["ruff"],
        python_provider_checks["pyright"],
        python_provider_checks["pyright-strict-ratchet"],
        python_provider_checks["pytest-coverage"],
        python_provider_checks["mutmut-target-ratchet"],
        python_provider_checks["radon-cc-report"],
        python_provider_checks["radon-mi-report"],
        python_provider_checks["xenon-complexity-gate"],
        python_provider_checks["pylint"],
        *architecture_checks(config, base_ref, staged=staged),
        python_provider_checks["deptry"],
        python_provider_checks["vulture"],
        python_provider_checks["bandit"],
        python_provider_checks["pip-audit"],
        python_provider_checks["mutmut"],
        *semgrep_checks(config),
        *osv_scanner_checks(config),
        *trivy_checks(config),
        *sbom_checks(config),
        *license_check_checks(config),
        *secret_scan_checks(config, base_ref, staged=staged),
        *workflow_checks(),
        python_provider_checks["wemake"],
        python_provider_checks["interrogate"],
        *docs_config_checks(config),
        python_provider_checks["diff-cover"],
    ]


def change_budget_checks(
    config: MaintainerConfig, base_ref: str, *, staged: bool
) -> list[models.Check]:
    """Build profile-specific change-budget checks."""

    return [
        models.Check(
            "change-budget",
            change_budget_command(
                config,
                base_ref,
                staged=staged,
                missing_test_change_as_error=(
                    profile in config.source_without_test_change_error_profiles
                ),
            ),
            frozenset((profile,)),
            required_paths=(".git",),
            report_success_output=True,
        )
        for profile in CHANGE_BUDGET_PROFILES
    ]


def file_length_command(config: MaintainerConfig, file_length_paths: tuple[str, ...]) -> list[str]:
    """Build the file-length command with optional legacy-ratchet baseline."""

    command = [sys.executable, "-m", "agent_maintainer.checks.file_lengths", *file_length_paths]
    if config.file_length_baseline:
        command.extend(["--baseline", config.file_length_baseline])
    return command


def structure_command(config: MaintainerConfig) -> list[str]:
    """Build structure cohesion command."""

    paths = config.structure_paths or config.source_roots
    command = [
        sys.executable,
        "-m",
        "agent_maintainer.checks.structure",
        "--warn-threshold",
        str(config.folder_file_warn),
        "--block-threshold",
        str(config.folder_file_block if config.mode == FRESH_STRICT_MODE else 0),
        "--cluster-min",
        str(config.structure_cluster_min),
    ]
    for ignored_path in config.structure_ignore_paths:
        command.extend(("--ignore", ignored_path))
    for pattern in config.structure_hint_patterns:
        command.extend(("--hint-pattern", pattern))
    return [*command, *paths]


def change_budget_command(
    config: MaintainerConfig,
    base_ref: str,
    *,
    staged: bool,
    missing_test_change_as_error: bool = False,
) -> list[str]:
    """Build the change-budget command with configured source and test roots."""

    command = [sys.executable, "-m", "agent_maintainer.checks.change_budget", base_ref]
    if staged:
        command.append("--staged")
    if missing_test_change_as_error:
        command.append("--missing-test-change-as-error")
    if config.allow_source_without_test_change:
        command.append("--allow-source-without-test-change")
    for root in config.source_roots:
        command.extend(["--source-root", root])
    for root in config.test_roots:
        command.extend(["--test-root", root])
    return command


def suppression_budget_command(base_ref: str, *, staged: bool) -> list[str]:
    """Build the suppression-budget command for staged or ref-based diffs."""

    command = [sys.executable, "-m", "agent_maintainer.checks.suppression_budget", base_ref]
    if staged:
        command.append("--staged")
    return command
