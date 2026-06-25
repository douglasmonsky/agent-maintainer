"""Tests for guardrail setup diagnostics."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import guardrail_doctor
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import FULL_PROFILES, Check


def test_status_code_treats_warnings_as_strict_failures() -> None:
    results = [guardrail_doctor.DoctorResult("git-state", guardrail_doctor.WARNING, "ahead")]

    assert guardrail_doctor.status_code(results, strict=False) == 0
    assert guardrail_doctor.status_code(results, strict=True) == 1


def test_main_emits_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(guardrail_doctor, "load_config", GuardrailConfig)
    monkeypatch.setattr(
        guardrail_doctor,
        "run_doctor",
        lambda repo_root, config: [
            guardrail_doctor.DoctorResult("python-version", guardrail_doctor.OK, "ok")
        ],
    )

    assert guardrail_doctor.main(["--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload == [{"name": "python-version", "status": "PASS", "message": "ok"}]


def test_layout_check_fails_when_configured_roots_are_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = GuardrailConfig(source_roots=("missing",), package_paths=("missing",))

    result = guardrail_doctor.check_layout(config)

    assert result.status == guardrail_doctor.ERROR
    assert "source root" in result.message


def test_required_executables_fail_when_dependency_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        guardrail_doctor,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check("custom", ["missing-tool"], FULL_PROFILES, required_executable="missing-tool")
        ],
    )
    monkeypatch.setattr(guardrail_doctor, "executable_exists", lambda repo_root, name: False)

    result = guardrail_doctor.check_required_executables(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.ERROR
    assert "missing-tool" in result.message


def test_pre_commit_hook_warns_when_config_exists_but_hook_is_absent(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    (tmp_path / ".git" / "hooks").mkdir(parents=True)

    result = guardrail_doctor.check_pre_commit(tmp_path)

    assert result.status == guardrail_doctor.WARNING
    assert "not installed" in result.message


def test_optional_gates_warn_for_legacy_defaults(tmp_path: Path) -> None:
    result = guardrail_doctor.check_optional_gates(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.WARNING
    assert ".importlinter" in result.message
    assert "pip-audit disabled" in result.message


def test_canonical_commands_fail_on_legacy_workflow_entrypoint(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "verify.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("python3 scripts/guardrail.py verify --profile ci\n", encoding="utf-8")

    result = guardrail_doctor.check_canonical_commands(tmp_path)

    assert result.status == guardrail_doctor.ERROR
    assert ".github/workflows/verify.yml" in result.message


def test_git_state_warns_for_dirty_ahead_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    completed = subprocess.CompletedProcess(
        ["git"],
        0,
        stdout="## main...origin/main [ahead 1]\n M README.md\n",
        stderr="",
    )
    monkeypatch.setattr(guardrail_doctor.subprocess, "run", lambda *args, **_kwargs: completed)

    result = guardrail_doctor.check_git_state(tmp_path)

    assert result.status == guardrail_doctor.WARNING
    assert "ahead 1" in result.message
    assert "changed path" in result.message
