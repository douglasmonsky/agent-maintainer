"""Tests for guardrail setup diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.core import tool_capabilities as guardrail_tool_capabilities
from ai_guardrails.core.config import GuardrailConfig
from ai_guardrails.doctor import cli as guardrail_doctor
from ai_guardrails.doctor import setup as guardrail_doctor_setup
from ai_guardrails.models import FULL_PROFILES, Check


def write_repo_root(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    package_path = tmp_path / "src" / "ai_guardrails"
    package_path.mkdir(parents=True)
    (package_path / "__main__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.ai_guardrails]\n", encoding="utf-8")
    return tmp_path


def test_status_code_treats_warnings_as_strict_failures() -> None:
    results = [guardrail_doctor.DoctorResult("git-state", guardrail_doctor.WARNING, "ahead")]

    assert guardrail_doctor.status_code(results, strict=False) == 0
    assert guardrail_doctor.status_code(results, strict=True) == 1
    assert (
        guardrail_doctor.status_code(
            [guardrail_doctor.DoctorResult("layout", guardrail_doctor.ERROR, "missing")],
            strict=False,
        )
        == 1
    )


def test_python_version_passes_for_current_runtime() -> None:
    result = guardrail_doctor.check_python_version()

    assert result.status == guardrail_doctor.OK
    assert "Python" in result.message


def test_repo_root_and_virtualenv_checks_cover_pass_and_warning(tmp_path: Path) -> None:
    repo_root = write_repo_root(tmp_path)
    python_path = repo_root / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    assert guardrail_doctor.check_repo_root(repo_root).status == guardrail_doctor.OK
    assert guardrail_doctor.check_virtualenv(repo_root).status == guardrail_doctor.OK

    python_path.unlink()

    assert guardrail_doctor.check_virtualenv(repo_root).status == guardrail_doctor.WARNING


def test_repo_root_warns_without_pyproject(tmp_path: Path) -> None:
    repo_root = write_repo_root(tmp_path)
    (repo_root / "pyproject.toml").unlink()

    result = guardrail_doctor.check_repo_root(repo_root)

    assert result.status == guardrail_doctor.WARNING
    assert "pyproject.toml" in result.message


def test_repo_root_fails_when_required_paths_are_missing(tmp_path: Path) -> None:
    result = guardrail_doctor.check_repo_root(tmp_path)

    assert result.status == guardrail_doctor.ERROR
    assert ".git" in result.message


def test_layout_check_fails_when_configured_roots_are_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = GuardrailConfig(source_roots=("missing",), package_paths=("missing",))

    result = guardrail_doctor.check_layout(config)

    assert result.status == guardrail_doctor.ERROR
    assert "source root" in result.message


def test_layout_check_passes_when_roots_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    config = GuardrailConfig(
        source_roots=("scripts",),
        package_paths=("scripts",),
        test_roots=("tests",),
        coverage_source=("scripts",),
    )

    result = guardrail_doctor.check_layout(config)

    assert result.status == guardrail_doctor.OK
    assert "sources=scripts" in result.message


def test_tool_capabilities_fail_when_dependency_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        guardrail_doctor_setup,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check("custom", ["missing-tool"], FULL_PROFILES, required_executable="missing-tool")
        ],
    )
    monkeypatch.setattr(
        guardrail_tool_capabilities,
        "executable_exists",
        lambda repo_root, name: False,
    )

    result = guardrail_doctor.check_tool_capabilities(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.ERROR
    assert "missing-tool" in result.message


def test_tool_capabilities_pass_when_local_tool_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool_path = tmp_path / ".venv" / "bin" / "local-tool"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        guardrail_doctor_setup,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check("custom", ["local-tool"], FULL_PROFILES, required_executable="local-tool")
        ],
    )

    result = guardrail_doctor.check_tool_capabilities(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.OK
    assert guardrail_tool_capabilities.executable_exists(tmp_path, "local-tool")


def test_tool_capabilities_report_disabled_optional_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        guardrail_doctor_setup,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check(
                "import-linter",
                ["lint-imports"],
                FULL_PROFILES,
                required_executable="lint-imports",
                optional_skip_reason=".importlinter is absent",
            )
        ],
    )

    result = guardrail_doctor.check_tool_capabilities(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.OK
    assert "disabled" in result.message


def test_tests_check_warns_when_tests_are_disabled(tmp_path: Path) -> None:
    result = guardrail_doctor.check_tests(tmp_path, GuardrailConfig(require_tests=False))

    assert result.status == guardrail_doctor.WARNING
    assert "disabled" in result.message


def test_tests_check_fails_and_passes_for_required_tests(tmp_path: Path) -> None:
    config = GuardrailConfig(test_roots=("tests",), require_tests=True)

    assert guardrail_doctor.check_tests(tmp_path, config).status == guardrail_doctor.ERROR

    (tmp_path / "tests").mkdir()

    assert guardrail_doctor.check_tests(tmp_path, config).status == guardrail_doctor.OK


def test_pre_commit_hook_warns_when_config_exists_but_hook_is_absent(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    (tmp_path / ".git" / "hooks").mkdir(parents=True)

    result = guardrail_doctor.check_pre_commit(tmp_path)

    assert result.status == guardrail_doctor.WARNING
    assert "not installed" in result.message


def test_pre_commit_hook_passes_when_installed(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("#!/bin/sh\n", encoding="utf-8")

    result = guardrail_doctor.check_pre_commit(tmp_path)

    assert result.status == guardrail_doctor.OK


def test_codex_hooks_warn_and_pass(tmp_path: Path) -> None:
    assert guardrail_doctor.check_codex_hooks(tmp_path).status == guardrail_doctor.WARNING

    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = false\n", encoding="utf-8")

    assert guardrail_doctor.check_codex_hooks(tmp_path).status == guardrail_doctor.WARNING

    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")

    assert guardrail_doctor.check_codex_hooks(tmp_path).status == guardrail_doctor.OK
