"""Declarative catalog of guardrail checks."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.guardrail_config import (
    FRESH_STRICT_MODE,
    IMPORT_LINTER_TOOL,
    TACH_TOOL,
    GuardrailConfig,
    existing_paths,
)
from scripts.guardrail_models import (
    ALL_PROFILES,
    CI_ONLY_PROFILES,
    FULL_PROFILES,
    LOCAL_GATE_PROFILES,
    Check,
)


def existing_or_configured(paths: tuple[str, ...]) -> tuple[str, ...]:
    existing = tuple(existing_paths(paths))
    return existing if existing else paths


def pytest_command(config: GuardrailConfig) -> list[str]:
    command = ["pytest", "-q", "--tb=short", "--disable-warnings"]
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


def pytest_check(config: GuardrailConfig) -> Check:
    if config.require_tests:
        return Check(
            "pytest-coverage",
            pytest_command(config),
            LOCAL_GATE_PROFILES,
            required_executable="pytest",
        )
    return Check(
        "pytest-coverage",
        ["pytest"],
        LOCAL_GATE_PROFILES,
        optional_skip_reason="tests are disabled by require_tests = false",
    )


def diff_cover_check(config: GuardrailConfig, compare_branch: str) -> Check:
    if config.require_tests:
        return Check(
            "diff-cover",
            [
                "diff-cover",
                "coverage.xml",
                f"--compare-branch={compare_branch}",
                f"--fail-under={config.diff_cover_fail_under}",
            ],
            CI_ONLY_PROFILES,
            required_paths=("coverage.xml", ".git"),
            required_executable="diff-cover",
        )
    return Check(
        "diff-cover",
        ["diff-cover"],
        CI_ONLY_PROFILES,
        optional_skip_reason="changed-code coverage is disabled because require_tests = false",
    )


def pip_audit_check(config: GuardrailConfig) -> Check:
    if not config.enable_pip_audit:
        return Check(
            "pip-audit",
            ["pip-audit"],
            FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with GUARDRAILS_ENABLE_PIP_AUDIT=1 or "
                "[tool.ai_guardrails].enable_pip_audit = true"
            ),
        )
    return Check(
        "pip-audit",
        ["pip-audit", *config.pip_audit_args],
        FULL_PROFILES,
        required_executable="pip-audit",
    )


def wemake_check(config: GuardrailConfig, package_paths: tuple[str, ...]) -> Check:
    if not config.enable_wemake:
        return Check(
            "wemake",
            ["flake8"],
            FULL_PROFILES,
            optional_skip_reason=(
                "disabled by default; enable with GUARDRAILS_ENABLE_WEMAKE=1 or "
                "[tool.ai_guardrails].enable_wemake = true"
            ),
        )
    return Check(
        "wemake",
        [
            "flake8",
            "--require-plugins",
            "wemake-python-styleguide",
            *package_paths,
        ],
        FULL_PROFILES,
        required_executable="flake8",
    )


def architecture_checks(config: GuardrailConfig) -> list[Check]:
    if config.architecture_tool == TACH_TOOL:
        return tach_checks(config)
    return [
        Check(
            IMPORT_LINTER_TOOL,
            ["lint-imports"],
            FULL_PROFILES,
            required_executable="lint-imports",
            optional_skip_reason=(
                ".importlinter is absent; architecture contracts are not configured"
            ),
        )
    ]


def tach_checks(config: GuardrailConfig) -> list[Check]:
    strict = config.mode == FRESH_STRICT_MODE
    config_command = [sys.executable, "-m", "scripts.check_tach_config"]
    if strict:
        config_command.append("--strict-root-module")
    optional_skip_reason = None
    if not strict:
        optional_skip_reason = "tach.toml is absent; architecture contracts are not configured"
    return [
        Check(
            "tach-config",
            config_command,
            FULL_PROFILES,
            required_paths=("tach.toml",) if strict else (),
            optional_skip_reason=optional_skip_reason,
        ),
        Check(
            "tach",
            ["tach", "check", "--exact"],
            FULL_PROFILES,
            required_paths=("tach.toml",) if strict else (),
            required_executable="tach",
            optional_skip_reason=optional_skip_reason,
        ),
    ]


def vulture_paths(config: GuardrailConfig, package_paths: tuple[str, ...]) -> tuple[str, ...]:
    paths = tuple(path for path in config.vulture_paths if Path(path).exists())
    return paths or package_paths


def make_checks(
    config: GuardrailConfig, base_ref: str, compare_branch: str, *, staged: bool = False
) -> list[Check]:
    package_paths = existing_or_configured(config.package_paths)
    file_length_paths = existing_or_configured(config.file_length_paths)
    return [
        Check(
            "file-length",
            [sys.executable, "-m", "scripts.check_file_lengths", *file_length_paths],
            ALL_PROFILES,
            required_paths=("scripts/check_file_lengths.py",),
        ),
        Check(
            "change-budget",
            change_budget_command(config, base_ref, staged=staged),
            ALL_PROFILES,
            required_paths=("scripts/check_change_budget.py", ".git"),
        ),
        Check(
            "suppression-budget",
            suppression_budget_command(base_ref, staged=staged),
            ALL_PROFILES,
            required_paths=("scripts/check_suppression_budget.py", ".git"),
        ),
        Check(
            "ruff-format",
            ["ruff", "format", "--check", "."],
            LOCAL_GATE_PROFILES,
            required_executable="ruff",
        ),
        Check(
            "ruff",
            [
                "ruff",
                "check",
                "--output-format=concise",
                "--config",
                f"lint.mccabe.max-complexity={config.ruff_max_complexity}",
                ".",
            ],
            ALL_PROFILES,
            required_executable="ruff",
        ),
        Check(
            "pyright",
            ["pyright", "--outputjson"],
            LOCAL_GATE_PROFILES,
            required_executable="pyright",
        ),
        pytest_check(config),
        Check(
            "radon-cc-report",
            ["radon", "cc", *package_paths, "-a", "-s"],
            FULL_PROFILES,
            required_executable="radon",
        ),
        Check(
            "radon-mi-report",
            ["radon", "mi", *package_paths, "-s"],
            FULL_PROFILES,
            required_executable="radon",
        ),
        Check(
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
            LOCAL_GATE_PROFILES,
            required_executable="xenon",
        ),
        Check(
            "pylint",
            ["pylint", *package_paths, "--score=n"],
            FULL_PROFILES,
            required_executable="pylint",
        ),
        *architecture_checks(config),
        Check(
            "deptry",
            ["deptry", "."],
            FULL_PROFILES,
            required_executable="deptry",
        ),
        Check(
            "vulture",
            ["vulture", *vulture_paths(config, package_paths)],
            FULL_PROFILES,
            required_executable="vulture",
        ),
        Check(
            "bandit",
            ["bandit", "-q", "-r", *package_paths],
            FULL_PROFILES,
            required_executable="bandit",
        ),
        pip_audit_check(config),
        wemake_check(config, package_paths),
        diff_cover_check(config, compare_branch),
    ]


def change_budget_command(config: GuardrailConfig, base_ref: str, *, staged: bool) -> list[str]:
    command = [sys.executable, "-m", "scripts.check_change_budget", base_ref]
    if staged:
        command.append("--staged")
    for root in config.source_roots:
        command.extend(["--source-root", root])
    for root in config.test_roots:
        command.extend(["--test-root", root])
    return command


def suppression_budget_command(base_ref: str, *, staged: bool) -> list[str]:
    command = [sys.executable, "-m", "scripts.check_suppression_budget", base_ref]
    if staged:
        command.append("--staged")
    return command
