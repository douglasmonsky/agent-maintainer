"""Tests for guardrail configuration and check catalog construction."""

from __future__ import annotations

import sys
from dataclasses import replace

from scripts.guardrail_catalogs import catalog as guardrail_catalog
from scripts.guardrail_core.config import GuardrailConfig
from scripts.guardrail_models import (
    MANUAL_PROFILES,
    PRECOMMIT_PROFILE,
)


def test_mutmut_check_is_disabled_by_default_and_manual_when_enabled() -> None:
    default_checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "mutmut")
    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None

    enabled_checks = guardrail_catalog.make_checks(
        replace(
            GuardrailConfig(),
            enable_mutmut=True,
            mutmut_args=("run", "scripts.guardrail_core.runtime*"),
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "mutmut")
    assert enabled.command == [
        sys.executable,
        "-m",
        "scripts.run_mutmut",
        "run",
        "scripts.guardrail_core.runtime*",
    ]
    assert enabled.profiles == MANUAL_PROFILES
    assert enabled.required_paths == ("scripts/run_mutmut.py",)
    assert enabled.required_executable == "mutmut"


def test_semgrep_check_is_disabled_by_default_and_profile_scoped() -> None:
    default_checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "semgrep")
    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None

    enabled_checks = guardrail_catalog.make_checks(
        replace(
            GuardrailConfig(),
            enable_semgrep=True,
            semgrep_args=("scan", "--config", "semgrep.yml", "--metrics=off", "."),
            semgrep_profiles=("manual", "security"),
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "semgrep")
    assert enabled.command == ["semgrep", "scan", "--config", "semgrep.yml", "--metrics=off", "."]
    assert enabled.profiles == frozenset(("manual", "security"))
    assert enabled.required_executable == "semgrep"


def test_secret_scan_checks_are_disabled_by_default() -> None:
    checks = guardrail_catalog.make_checks(GuardrailConfig(), "HEAD", "origin/main")
    secret_scan = next(check for check in checks if check.name == "secret-scan")

    assert secret_scan.optional_skip_reason is not None
    assert secret_scan.required_executable is None


def test_secret_scan_checks_use_gitleaks_backend_when_enabled() -> None:
    config = GuardrailConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=("full", "ci"),
        secret_scan_history_profiles=("security",),
    )
    checks = guardrail_catalog.make_checks(config, "origin/main", "origin/main")
    by_profile = {
        next(iter(check.profiles)): check for check in checks if check.name == "secret-scan"
    }
    history = next(check for check in checks if check.name == "secret-scan-history")

    assert by_profile["full"].required_executable == "gitleaks"
    assert "--mode" in by_profile["full"].command
    assert "current-tree" in by_profile["full"].command
    assert "range" in by_profile["ci"].command
    assert history.profiles == frozenset(("security",))
    assert "history" in history.command


def test_secret_scan_checks_use_staged_mode_for_staged_precommit() -> None:
    config = GuardrailConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=(PRECOMMIT_PROFILE,),
    )
    checks = guardrail_catalog.make_checks(config, "HEAD", "origin/main", staged=True)
    secret_scan = next(
        check
        for check in checks
        if check.name == "secret-scan" and PRECOMMIT_PROFILE in check.profiles
    )

    assert "staged" in secret_scan.command
