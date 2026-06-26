"""Declarative catalog of guardrail checks."""

from __future__ import annotations

import sys
from pathlib import Path

from guardrail_lib.config.schema import (
    FRESH_STRICT_MODE,
    IMPORT_LINTER_TOOL,
    TACH_TOOL,
    GuardrailConfig,
)
from scripts import guardrail_catalog_python as python_checks
from scripts import guardrail_models as models
from scripts.guardrail_catalog_docs import docs_config_checks
from scripts.guardrail_catalog_security import (
    license_check_checks,
    sbom_checks,
    secret_scan_checks,
    semgrep_checks,
)
from scripts.guardrail_config import existing_paths

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


def architecture_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build the selected architecture contract checks."""

    if config.architecture_tool == TACH_TOOL:
        return tach_checks(config)
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


def tach_checks(config: GuardrailConfig) -> list[models.Check]:
    """Build Tach config and architecture checks for the selected strictness mode."""

    strict = config.mode == FRESH_STRICT_MODE
    config_command = [sys.executable, "-m", "scripts.check_tach_config"]
    if strict:
        config_command.append("--strict-root-module")
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
            "tach",
            ["tach", "check", "--exact"],
            models.FULL_PROFILES,
            required_paths=("tach.toml",) if strict else (),
            required_executable="tach",
            optional_skip_reason=optional_skip_reason,
        ),
    ]


def vulture_paths(config: GuardrailConfig, package_paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return existing vulture scan paths, falling back to package paths."""

    paths = tuple(path for path in config.vulture_paths if Path(path).exists())
    return paths or package_paths


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
    config: GuardrailConfig, base_ref: str, compare_branch: str, *, staged: bool = False
) -> list[models.Check]:
    """Build the complete check catalog for all verifier profiles."""

    package_paths = existing_or_configured(config.package_paths)
    file_length_paths = existing_or_configured(config.file_length_paths)
    return [
        models.Check(
            "file-length",
            file_length_command(config, file_length_paths),
            models.ALL_PROFILES,
            required_paths=("scripts/check_file_lengths.py",),
        ),
        models.Check(
            "structure-cohesion",
            structure_command(config),
            models.ALL_PROFILES,
            required_paths=("scripts/check_structure.py",),
            report_success_output=True,
        ),
        *change_budget_checks(config, base_ref, staged=staged),
        models.Check(
            "suppression-budget",
            suppression_budget_command(base_ref, staged=staged),
            models.ALL_PROFILES,
            required_paths=("scripts/check_suppression_budget.py", ".git"),
        ),
        models.Check(
            "ruff-format",
            ["ruff", "format", "--check", "."],
            models.LOCAL_GATE_PROFILES,
            required_executable="ruff",
        ),
        python_checks.ruff_check(config),
        python_checks.pyright_check(config),
        python_checks.pytest_check(config),
        models.Check(
            "radon-cc-report",
            ["radon", "cc", *package_paths, "-a", "-s"],
            models.FULL_PROFILES,
            required_executable="radon",
        ),
        models.Check(
            "radon-mi-report",
            ["radon", "mi", *package_paths, "-s"],
            models.FULL_PROFILES,
            required_executable="radon",
        ),
        models.Check(
            "xenon-complexity-gate",
            [
                "xenon",
                "--max-absolute",
                config.xenon_max_absolute,
                "--max-modules",
                config.xenon_max_modules,
                "--max-average",
                config.xenon_max_average,
                *package_paths,
            ],
            models.LOCAL_GATE_PROFILES,
            required_executable="xenon",
        ),
        models.Check(
            "pylint",
            ["pylint", *package_paths, "--score=n"],
            models.FULL_PROFILES,
            required_executable="pylint",
        ),
        *architecture_checks(config),
        models.Check(
            "deptry",
            ["deptry", "."],
            models.FULL_PROFILES,
            required_executable="deptry",
        ),
        models.Check(
            "vulture",
            ["vulture", *vulture_paths(config, package_paths)],
            models.FULL_PROFILES,
            required_executable="vulture",
        ),
        python_checks.bandit_check(config),
        python_checks.pip_audit_check(config),
        python_checks.mutmut_check(config),
        *semgrep_checks(config),
        *sbom_checks(config),
        *license_check_checks(config),
        *secret_scan_checks(config, base_ref, staged=staged),
        *workflow_checks(),
        python_checks.wemake_check(config, package_paths),
        python_checks.interrogate_check(config, package_paths),
        *docs_config_checks(config),
        python_checks.diff_cover_check(config, compare_branch),
    ]


def change_budget_checks(
    config: GuardrailConfig, base_ref: str, *, staged: bool
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
            required_paths=("scripts/check_change_budget.py", ".git"),
            report_success_output=True,
        )
        for profile in CHANGE_BUDGET_PROFILES
    ]


def file_length_command(config: GuardrailConfig, file_length_paths: tuple[str, ...]) -> list[str]:
    """Build the file-length command with optional legacy-ratchet baseline."""

    command = [sys.executable, "-m", "scripts.check_file_lengths", *file_length_paths]
    if config.file_length_baseline:
        command.extend(["--baseline", config.file_length_baseline])
    return command


def structure_command(config: GuardrailConfig) -> list[str]:
    """Build structure cohesion command."""

    paths = config.structure_paths or config.source_roots
    command = [
        sys.executable,
        "-m",
        "scripts.check_structure",
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
    config: GuardrailConfig,
    base_ref: str,
    *,
    staged: bool,
    missing_test_change_as_error: bool = False,
) -> list[str]:
    """Build the change-budget command with configured source and test roots."""

    command = [sys.executable, "-m", "scripts.check_change_budget", base_ref]
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

    command = [sys.executable, "-m", "scripts.check_suppression_budget", base_ref]
    if staged:
        command.append("--staged")
    return command
