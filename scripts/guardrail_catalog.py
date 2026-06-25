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
from scripts import guardrail_models as models
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


def pytest_command(config: GuardrailConfig) -> list[str]:
    """Build the coverage-enforcing pytest command."""

    command = ["pytest", "-q", "--tb=short", "--disable-warnings", "-p", "no:tach"]
    command.extend(f"--cov={source}" for source in config.coverage_source)
    command.extend(
        [
            "--cov-report=term-missing:skip-covered",
            "--cov-report=xml",
            f"--cov-fail-under={config.coverage_fail_under}",
            *config.test_roots,
        ]
    )
    return command


def pytest_check(config: GuardrailConfig) -> models.Check:
    """Build the pytest coverage check or its require-tests skip."""

    if config.require_tests:
        return models.Check(
            "pytest-coverage",
            pytest_command(config),
            models.LOCAL_GATE_PROFILES,
            required_executable="pytest",
            artifact_paths=("coverage.xml",),
        )
    return models.Check(
        "pytest-coverage",
        ["pytest"],
        models.LOCAL_GATE_PROFILES,
        optional_skip_reason="tests are disabled by require_tests = false",
    )


def diff_cover_check(config: GuardrailConfig, compare_branch: str) -> models.Check:
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


def pip_audit_check(config: GuardrailConfig) -> models.Check:
    """Build the dependency vulnerability check or its explicit skip."""

    if not config.enable_pip_audit:
        return models.Check(
            "pip-audit",
            ["pip-audit"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with GUARDRAILS_ENABLE_PIP_AUDIT=1 or "
                "[tool.ai_guardrails].enable_pip_audit = true"
            ),
        )
    if not config.pip_audit_args:
        if config.mode == FRESH_STRICT_MODE:
            return models.Check(
                "pip-audit",
                [sys.executable, "-m", "scripts.check_pip_audit_config"],
                models.FULL_PROFILES,
                required_paths=("scripts/check_pip_audit_config.py",),
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


def pyright_check() -> models.Check:
    """Build the Pyright check through the generated-project wrapper."""

    return models.Check(
        "pyright",
        [sys.executable, "-m", "scripts.run_pyright"],
        models.LOCAL_GATE_PROFILES,
        required_paths=("scripts/run_pyright.py",),
        required_executable="pyright",
    )


def wemake_check(config: GuardrailConfig, package_paths: tuple[str, ...]) -> models.Check:
    """Build the wemake strict-style check or its explicit skip."""

    if not config.enable_wemake:
        return models.Check(
            "wemake",
            ["flake8"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with GUARDRAILS_ENABLE_WEMAKE=1 or "
                "[tool.ai_guardrails].enable_wemake = true"
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


def interrogate_check(config: GuardrailConfig, package_paths: tuple[str, ...]) -> models.Check:
    """Build the docstring coverage check or its explicit optional skip."""

    if not config.enable_interrogate:
        return models.Check(
            "interrogate",
            ["interrogate"],
            models.FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with GUARDRAILS_ENABLE_INTERROGATE=1 or "
                "[tool.ai_guardrails].enable_interrogate = true"
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
        models.Check(
            "ruff",
            [
                "ruff",
                "check",
                "--output-format=concise",
                "--config",
                f"lint.mccabe.max-complexity={config.ruff_max_complexity}",
                ".",
            ],
            models.ALL_PROFILES,
            required_executable="ruff",
        ),
        pyright_check(),
        pytest_check(config),
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
        models.Check(
            "bandit",
            ["bandit", "-q", "-r", *package_paths],
            models.FULL_PROFILES,
            required_executable="bandit",
        ),
        pip_audit_check(config),
        wemake_check(config, package_paths),
        interrogate_check(config, package_paths),
        diff_cover_check(config, compare_branch),
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
