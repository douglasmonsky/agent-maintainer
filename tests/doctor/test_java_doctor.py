"""Tests static Java/Gradle doctor diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import java_provider
from agent_maintainer.doctor.support.models import MISSING, OK, UNSAFE_CONFIG, WARNING


# docsync:evidence.start evidence.java.provider_foundation_tests
def test_java_doctor_is_silent_when_provider_disabled(tmp_path: Path) -> None:
    assert java_provider.check_java_provider(tmp_path, MaintainerConfig()) == ()


def test_java_doctor_reports_missing_wrapper_runtime_and_tasks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(java_provider.shutil, "which", _missing_java)
    config = MaintainerConfig(
        java=JavaGradleConfig(enabled=True, checks=("spotbugs",)),
    )

    results = {
        result.name: result for result in java_provider.check_java_provider(tmp_path, config)
    }

    assert results["java-gradle-wrapper"].status == WARNING
    assert results["java-gradle-wrapper"].state == MISSING
    assert results["java-runtime"].status == WARNING
    assert results["java-runtime"].state == MISSING
    assert results["java-gradle-config"].status == WARNING
    assert results["java-gradle-config"].state == UNSAFE_CONFIG
    assert "java.spotbugs_tasks" in results["java-gradle-config"].message


def test_java_doctor_passes_static_foundation_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(
        java_provider.shutil,
        "which",
        _found_java,
    )
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("test",),
            test_tasks=("test",),
        ),
    )

    results = java_provider.check_java_provider(tmp_path, config)

    assert [result.name for result in results] == [
        "java-gradle-wrapper",
        "java-runtime",
        "java-gradle-config",
    ]
    assert {result.status for result in results} == {OK}


def test_java_doctor_never_executes_gradle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _missing_java)

    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("normal doctor must not execute Gradle")

    monkeypatch.setattr(subprocess, "run", fail_run)
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("test",),
            test_tasks=("test",),
        ),
    )

    assert java_provider.check_java_provider(tmp_path, config)


def test_java_doctor_warns_when_deferred_policy_is_customized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _found_java)
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("test",),
            test_tasks=("test",),
            spotless_ratchet_ref="origin/main",
            spotbugs_baseline="config/spotbugs/exclude.xml",
            jacoco_line_property="custom.line",
            jacoco_branch_property="custom.branch",
        ),
    )

    results = {
        result.name: result for result in java_provider.check_java_provider(tmp_path, config)
    }

    config_result = results["java-gradle-config"]
    assert config_result.status == WARNING
    assert config_result.state == UNSAFE_CONFIG
    assert "java.spotless_ratchet_ref" in config_result.message
    assert "java.spotbugs_baseline" in config_result.message
    assert "java.jacoco_line_property" in config_result.message
    assert "java.jacoco_branch_property" in config_result.message


def test_run_doctor_includes_java_rows_only_when_enabled(tmp_path: Path) -> None:
    disabled = maintainer_doctor.run_doctor(tmp_path, MaintainerConfig())
    enabled = maintainer_doctor.run_doctor(
        tmp_path,
        MaintainerConfig(
            java=JavaGradleConfig(
                enabled=True,
                checks=("test",),
                test_tasks=("test",),
            ),
        ),
    )

    assert not [result for result in disabled if result.name.startswith("java-")]
    assert [result for result in enabled if result.name == "java-gradle-config"]


def _write_wrapper(root: Path) -> None:
    wrapper = root / "gradlew"
    wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    wrapper.chmod(0o755)


def _missing_java(_executable: str, *, path: str | None = None) -> None:
    del path


def _found_java(_executable: str, *, path: str | None = None) -> str:
    del path
    return "/usr/bin/java"


# docsync:evidence.end evidence.java.provider_foundation_tests
