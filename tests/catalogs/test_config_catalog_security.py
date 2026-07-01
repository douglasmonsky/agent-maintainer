"""Tests for Agent Maintainer configuration and check catalog construction."""

from __future__ import annotations

import sys
from dataclasses import replace

from agent_maintainer.catalogs import catalog as maintainer_catalog
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.models import (
    MANUAL_PROFILES,
    PRECOMMIT_PROFILE,
)


def test_mutmut_check_is_disabled_by_default_and_manual_when_enabled() -> None:
    default_checks = maintainer_catalog.make_checks(MaintainerConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "mutmut")
    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None

    enabled_checks = maintainer_catalog.make_checks(
        replace(
            MaintainerConfig(),
            enable_mutmut=True,
            mutmut_args=("run", "agent_maintainer.core.runtime*"),
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "mutmut")
    assert enabled.command == [
        sys.executable,
        "-m",
        "agent_maintainer.runners.mutmut",
        "run",
        "agent_maintainer.core.runtime*",
    ]
    assert enabled.profiles == MANUAL_PROFILES
    assert enabled.required_paths == ()
    assert enabled.required_executable == "mutmut"


def test_semgrep_check_is_disabled_by_default_and_profile_scoped() -> None:
    default_checks = maintainer_catalog.make_checks(MaintainerConfig(), "HEAD", "origin/main")
    disabled = next(check for check in default_checks if check.name == "semgrep")
    assert disabled.profiles == MANUAL_PROFILES
    assert disabled.optional_skip_reason is not None

    enabled_checks = maintainer_catalog.make_checks(
        replace(
            MaintainerConfig(),
            enable_semgrep=True,
            semgrep_args=("scan", "--config", "semgrep.yml", "--metrics=off", "."),
            semgrep_profiles=("manual", "security"),
        ),
        "HEAD",
        "origin/main",
    )
    enabled = next(check for check in enabled_checks if check.name == "semgrep")
    assert enabled.command == [
        "semgrep",
        "scan",
        "--config",
        "semgrep.yml",
        "--metrics=off",
        ".",
        "--json-output",
        ".verify-logs/semgrep.json",
    ]
    assert enabled.artifact_paths == (".verify-logs/semgrep.json",)
    assert enabled.profiles == frozenset(("manual", "security"))
    assert enabled.required_executable == "semgrep"


def test_secret_scan_checks_are_disabled_by_default() -> None:
    checks = maintainer_catalog.make_checks(MaintainerConfig(), "HEAD", "origin/main")
    secret_scan = next(check for check in checks if check.name == "secret-scan")

    assert secret_scan.optional_skip_reason is not None
    assert secret_scan.required_executable is None


def test_secret_scan_checks_use_gitleaks_backend_when_enabled() -> None:
    config = MaintainerConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=("full", "ci"),
        secret_scan_history_profiles=("security",),
    )
    checks = maintainer_catalog.make_checks(config, "origin/main", "origin/main")
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


def test_secret_scan_ci_uses_base_ref() -> None:
    config = MaintainerConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=("ci",),
    )

    checks = maintainer_catalog.make_checks(config, "origin/main", "origin/main")
    secret_scan = next(check for check in checks if check.name == "secret-scan")

    assert secret_scan.command[secret_scan.command.index("--base-ref") + 1] == "origin/main"


def test_secret_scan_checks_use_staged_mode_for_staged_precommit() -> None:
    config = MaintainerConfig(
        enable_secret_scanning=True,
        secret_scan_profiles=(PRECOMMIT_PROFILE,),
    )
    checks = maintainer_catalog.make_checks(config, "HEAD", "origin/main", staged=True)
    secret_scan = next(
        check
        for check in checks
        if check.name == "secret-scan" and PRECOMMIT_PROFILE in check.profiles
    )

    assert "staged" in secret_scan.command
