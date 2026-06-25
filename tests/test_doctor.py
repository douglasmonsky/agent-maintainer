"""Tests for guardrail setup diagnostics."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import guardrail_doctor, guardrail_doctor_policy, guardrail_guidance
from scripts.guardrail_config import GuardrailConfig
from scripts.guardrail_models import FULL_PROFILES, Check


def write_repo_root(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "guardrail.py").write_text("", encoding="utf-8")
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


def test_main_emits_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(guardrail_doctor.guardrail_config, "load_config", GuardrailConfig)
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


def test_main_emits_text(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(guardrail_doctor.guardrail_config, "load_config", GuardrailConfig)
    monkeypatch.setattr(
        guardrail_doctor,
        "run_doctor",
        lambda repo_root, config: [
            guardrail_doctor.DoctorResult("virtualenv", guardrail_doctor.WARNING, "missing")
        ],
    )

    assert guardrail_doctor.main([]) == 0

    assert "WARN virtualenv: missing" in capsys.readouterr().out


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


def test_required_executables_pass_when_local_tool_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool_path = tmp_path / ".venv" / "bin" / "local-tool"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        guardrail_doctor,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check("custom", ["local-tool"], FULL_PROFILES, required_executable="local-tool")
        ],
    )

    result = guardrail_doctor.check_required_executables(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.OK
    assert guardrail_doctor.executable_exists(tmp_path, "local-tool")


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


def test_optional_gates_warn_for_legacy_defaults(tmp_path: Path) -> None:
    result = guardrail_doctor.check_optional_gates(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.WARNING
    assert ".importlinter" in result.message
    assert "pip-audit disabled" in result.message
    assert "interrogate disabled" in result.message


def test_optional_gates_pass_when_enabled(tmp_path: Path) -> None:
    (tmp_path / ".importlinter").write_text("[importlinter]\n", encoding="utf-8")
    config = GuardrailConfig(
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = guardrail_doctor.check_optional_gates(tmp_path, config)

    assert result.status == guardrail_doctor.OK


def test_optional_gates_warn_when_tach_config_is_missing(tmp_path: Path) -> None:
    config = GuardrailConfig(
        architecture_tool="tach",
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = guardrail_doctor.check_optional_gates(tmp_path, config)

    assert result.status == guardrail_doctor.WARNING
    assert "tach.toml is absent" in result.message


def test_optional_gates_warn_when_fresh_strict_tach_is_permissive(tmp_path: Path) -> None:
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "ignore"

[[modules]]
path = "scripts"
""".strip(),
        encoding="utf-8",
    )
    config = GuardrailConfig(
        mode="fresh-strict",
        architecture_tool="tach",
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = guardrail_doctor.check_optional_gates(tmp_path, config)

    assert result.status == guardrail_doctor.WARNING
    assert 'root_module = "forbid"' in result.message


def test_optional_gates_pass_when_tach_is_strict(tmp_path: Path) -> None:
    (tmp_path / "tach.toml").write_text(
        """
source_roots = ["."]
root_module = "forbid"

[[modules]]
path = "scripts"
""".strip(),
        encoding="utf-8",
    )
    config = GuardrailConfig(
        mode="fresh-strict",
        architecture_tool="tach",
        enable_pip_audit=True,
        enable_wemake=True,
        enable_interrogate=True,
    )

    result = guardrail_doctor.check_optional_gates(tmp_path, config)

    assert result.status == guardrail_doctor.OK
    assert "Tach" in result.message


def test_pip_audit_safety_warns_or_fails_for_empty_args() -> None:
    custom = GuardrailConfig(enable_pip_audit=True, pip_audit_args=())
    strict = GuardrailConfig(mode="fresh-strict", enable_pip_audit=True, pip_audit_args=())
    safe = GuardrailConfig(enable_pip_audit=True, pip_audit_args=("-r", "requirements.txt"))

    assert guardrail_doctor_policy.check_pip_audit_safety(custom).status == guardrail_doctor.WARNING
    assert guardrail_doctor_policy.check_pip_audit_safety(strict).status == guardrail_doctor.ERROR
    assert guardrail_doctor_policy.check_pip_audit_safety(safe).status == guardrail_doctor.OK


def test_pyright_config_check_reports_mode_mismatch(tmp_path: Path) -> None:
    (tmp_path / "pyrightconfig.json").write_text(
        '{"typeCheckingMode": "basic"}\n',
        encoding="utf-8",
    )
    config = GuardrailConfig(pyright_type_checking_mode="strict")

    result = guardrail_doctor_policy.check_pyright_config(tmp_path, config)

    assert result.status == guardrail_doctor.WARNING
    assert "basic" in result.message
    assert "strict" in result.message


def test_canonical_commands_fail_on_legacy_workflow_entrypoint(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "verify.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("python3 scripts/guardrail.py verify --profile ci\n", encoding="utf-8")

    result = guardrail_doctor.check_canonical_commands(tmp_path)

    assert result.status == guardrail_doctor.ERROR
    assert ".github/workflows/verify.yml" in result.message


def test_canonical_commands_warn_for_missing_files(tmp_path: Path) -> None:
    result = guardrail_doctor.check_canonical_commands(tmp_path)

    assert result.status == guardrail_doctor.WARNING
    assert "Missing command files" in result.message


def test_canonical_commands_pass_when_all_files_use_module_entrypoint(tmp_path: Path) -> None:
    files = {
        ".github/workflows/verify.yml": "python3 -m scripts.guardrail verify\n",
        ".pre-commit-config.yaml": "python3 -m scripts.guardrail verify --profile precommit\n",
        ".codex/hooks/post_edit_fast_gate.py": "scripts.guardrail\n",
        ".codex/hooks/stop_full_verify.py": "scripts.guardrail\n",
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    result = guardrail_doctor.check_canonical_commands(tmp_path)

    assert result.status == guardrail_doctor.OK


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


def test_git_state_warns_when_git_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(guardrail_doctor.shutil, "which", lambda name: None)

    result = guardrail_doctor.check_git_state(tmp_path)

    assert result.status == guardrail_doctor.WARNING
    assert "git executable" in result.message


def test_git_state_passes_for_clean_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(["git"], 0, stdout="## main...origin/main\n", stderr="")
    monkeypatch.setattr(guardrail_doctor.shutil, "which", lambda name: "/usr/bin/git")
    monkeypatch.setattr(guardrail_doctor.subprocess, "run", lambda *args, **_kwargs: completed)

    result = guardrail_doctor.check_git_state(tmp_path)

    assert result.status == guardrail_doctor.OK
    assert result.message == "main...origin/main"


def test_recent_logs_warn_and_pass(tmp_path: Path) -> None:
    assert guardrail_doctor.check_recent_logs(tmp_path).status == guardrail_doctor.WARNING

    log_dir = tmp_path / ".verify-logs"
    log_dir.mkdir()

    assert guardrail_doctor.check_recent_logs(tmp_path).status == guardrail_doctor.WARNING

    (log_dir / "ruff.log").write_text("ok\n", encoding="utf-8")

    result = guardrail_doctor.check_recent_logs(tmp_path)

    assert result.status == guardrail_doctor.OK
    assert "ruff.log" in result.message


def test_agent_guidance_check_warns_for_missing_custom_sidecar(tmp_path: Path) -> None:
    result = guardrail_doctor.check_agent_guidance(tmp_path, GuardrailConfig())

    assert result.status == guardrail_doctor.WARNING
    assert "AGENTS.guardrails.md" in result.message


def test_agent_guidance_check_fails_for_stale_fresh_strict_sidecar(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.guardrails.md").write_text("stale\n", encoding="utf-8")
    config = GuardrailConfig(mode="fresh-strict")

    result = guardrail_doctor.check_agent_guidance(tmp_path, config)

    assert result.status == guardrail_doctor.ERROR
    assert "stale" in result.message


def test_agent_guidance_check_passes_for_current_sidecar(tmp_path: Path) -> None:
    config = GuardrailConfig(mode="fresh-strict")
    expected = guardrail_guidance.render_guidance(config)
    (tmp_path / "AGENTS.guardrails.md").write_text(expected, encoding="utf-8")

    result = guardrail_doctor.check_agent_guidance(tmp_path, config)

    assert result.status == guardrail_doctor.OK
