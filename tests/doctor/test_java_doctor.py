"""Tests static Java/Gradle doctor diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import java_provider
from agent_maintainer.doctor.support.models import (
    ACTIVE,
    MISSING,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)


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


def test_java_doctor_warns_for_missing_ratchet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _found_java)
    config = MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotless",),
            spotless_tasks=("spotlessCheck",),
            spotless_ratchet_ref="origin/main",
        ),
    )

    results = _java_results(tmp_path, config)

    ratchet = results["java-spotless-ratchet"]
    assert ratchet.status == WARNING
    assert ratchet.state == MISSING
    assert "origin/main" in ratchet.message


def test_java_doctor_accepts_spotbugs_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _found_java)
    baseline = tmp_path / "config" / "spotbugs" / "exclude.xml"
    baseline.parent.mkdir(parents=True)
    baseline.write_text("<FindBugsFilter/>\n", encoding="utf-8")
    config = _spotbugs_config("config/spotbugs/exclude.xml")
    results = _java_results(tmp_path, config)

    baseline_result = results["java-spotbugs-baseline"]
    assert baseline_result.status == OK
    assert baseline_result.state == ACTIVE


def test_java_doctor_rejects_escaping_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _found_java)
    outside = tmp_path.parent / f"{tmp_path.name}-outside.xml"
    outside.write_text("<FindBugsFilter/>\n", encoding="utf-8")
    baseline = tmp_path / "config" / "spotbugs" / "exclude.xml"
    baseline.parent.mkdir(parents=True)
    baseline.symlink_to(outside)
    config = _spotbugs_config("config/spotbugs/exclude.xml")
    results = _java_results(tmp_path, config)

    baseline_result = results["java-spotbugs-baseline"]
    assert baseline_result.status == WARNING
    assert baseline_result.state == UNSAFE_CONFIG


def test_java_doctor_warns_for_missing_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _found_java)
    config = _spotbugs_config("config/spotbugs/exclude.xml")
    results = _java_results(tmp_path, config)

    baseline_result = results["java-spotbugs-baseline"]
    assert baseline_result.status == WARNING
    assert baseline_result.state == MISSING


def test_java_doctor_rejects_bad_baseline_xml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_wrapper(tmp_path)
    monkeypatch.setattr(java_provider.shutil, "which", _found_java)
    baseline = tmp_path / "spotbugs.xml"
    baseline.write_text("<BugCollection/>\n", encoding="utf-8")

    results = _java_results(tmp_path, _spotbugs_config("spotbugs.xml"))

    baseline_result = results["java-spotbugs-baseline"]
    assert baseline_result.status == WARNING
    assert "FindBugsFilter" in baseline_result.message


def test_java_doctor_warns_for_coverage_policy(
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
            jacoco_line_property="custom.line",
            jacoco_branch_property="custom.branch",
        ),
    )

    results = _java_results(tmp_path, config)

    config_result = results["java-gradle-config"]
    assert config_result.status == WARNING
    assert config_result.state == UNSAFE_CONFIG
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


def _java_results(
    root: Path,
    config: MaintainerConfig,
) -> dict[str, DoctorResult]:
    return {result.name: result for result in java_provider.check_java_provider(root, config)}


def _spotbugs_config(baseline_path: str) -> MaintainerConfig:
    return MaintainerConfig(
        java=JavaGradleConfig(
            enabled=True,
            checks=("spotbugs",),
            spotbugs_tasks=("spotbugsMain",),
            spotbugs_baseline=baseline_path,
        ),
    )


def _missing_java(_executable: str, *, path: str | None = None) -> None:
    del path


def _found_java(_executable: str, *, path: str | None = None) -> str:
    del path
    return "/usr/bin/java"


# docsync:evidence.end evidence.java.provider_foundation_tests
