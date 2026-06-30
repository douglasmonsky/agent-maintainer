"""Tests for maintainer setup diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_maintainer.core import tool_capabilities as maintainer_tool_capabilities
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor import setup as maintainer_doctor_setup
from agent_maintainer.doctor.support import models as maintainer_doctor_models
from agent_maintainer.models import FULL_PROFILES, Check


def write_repo_root(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    package_path = tmp_path / "src" / "agent_maintainer"
    package_path.mkdir(parents=True)
    (package_path / "__main__.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.agent_maintainer]\n", encoding="utf-8")
    return tmp_path


def test_status_code_treats_warnings_as_strict_failures() -> None:
    results = [maintainer_doctor.DoctorResult("git-state", maintainer_doctor.WARNING, "ahead")]

    assert maintainer_doctor.status_code(results, strict=False) == 0
    assert maintainer_doctor.status_code(results, strict=True) == 1
    assert (
        maintainer_doctor.status_code(
            [maintainer_doctor.DoctorResult("layout", maintainer_doctor.ERROR, "missing")],
            strict=False,
        )
        == 1
    )


def test_python_version_passes_for_current_runtime() -> None:
    result = maintainer_doctor.check_python_version()

    assert result.status == maintainer_doctor.OK
    assert "Python" in result.message


def test_repo_root_and_virtualenv_checks_cover_pass_and_warning(tmp_path: Path) -> None:
    repo_root = write_repo_root(tmp_path)
    python_path = repo_root / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    assert maintainer_doctor.check_repo_root(repo_root).status == maintainer_doctor.OK
    assert maintainer_doctor.check_virtualenv(repo_root).status == maintainer_doctor.OK

    python_path.unlink()

    assert maintainer_doctor.check_virtualenv(repo_root).status == maintainer_doctor.WARNING


def test_repo_root_warns_without_pyproject(tmp_path: Path) -> None:
    repo_root = write_repo_root(tmp_path)
    (repo_root / "pyproject.toml").unlink()

    result = maintainer_doctor.check_repo_root(repo_root)

    assert result.status == maintainer_doctor.WARNING
    assert "pyproject.toml" in result.message


def test_unknown_config_key_check_warns_with_full_key_paths(tmp_path: Path) -> None:
    """Doctor warns when Agent Maintainer config contains ignored keys."""

    repo_root = write_repo_root(tmp_path)
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            (
                "[tool.agent_maintainer]",
                'mode = "custom"',
                "coverage_fail_nder = 90",
                "[tool.agent_maintainer.diagnostics]",
                "lod_dir = '.verify-logs'",
            )
        ),
        encoding="utf-8",
    )

    result = maintainer_doctor.check_unknown_config_keys(repo_root)

    assert result.status == maintainer_doctor.WARNING
    assert result.state == maintainer_doctor_models.UNSAFE_CONFIG
    assert "tool.agent_maintainer.coverage_fail_nder" in result.message
    assert "tool.agent_maintainer.diagnostics.lod_dir" in result.message
    assert "Fix typos" in result.hint


def test_repo_root_fails_when_required_paths_are_missing(tmp_path: Path) -> None:
    result = maintainer_doctor.check_repo_root(tmp_path)

    assert result.status == maintainer_doctor.ERROR
    assert ".git" in result.message


def test_layout_check_fails_when_configured_roots_are_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = MaintainerConfig(source_roots=("missing",), package_paths=("missing",))

    result = maintainer_doctor.check_layout(config)

    assert result.status == maintainer_doctor.ERROR
    assert "source root" in result.message


def test_layout_check_passes_when_roots_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests").mkdir()
    config = MaintainerConfig(
        source_roots=("scripts",),
        package_paths=("scripts",),
        test_roots=("tests",),
        coverage_source=("scripts",),
    )

    result = maintainer_doctor.check_layout(config)

    assert result.status == maintainer_doctor.OK
    assert "sources=scripts" in result.message


def test_tool_capabilities_fail_when_dependency_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        maintainer_doctor_setup,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check("custom", ["missing-tool"], FULL_PROFILES, required_executable="missing-tool")
        ],
    )
    monkeypatch.setattr(
        maintainer_tool_capabilities,
        "executable_exists",
        lambda repo_root, name: False,
    )

    result = maintainer_doctor.check_tool_capabilities(tmp_path, MaintainerConfig())

    assert result.status == maintainer_doctor.ERROR
    assert "missing-tool" in result.message


def test_tool_capabilities_pass_when_local_tool_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool_path = tmp_path / ".venv" / "bin" / "local-tool"
    tool_path.parent.mkdir(parents=True)
    tool_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        maintainer_doctor_setup,
        "make_checks",
        lambda config, base_ref, compare_branch: [
            Check("custom", ["local-tool"], FULL_PROFILES, required_executable="local-tool")
        ],
    )

    result = maintainer_doctor.check_tool_capabilities(tmp_path, MaintainerConfig())

    assert result.status == maintainer_doctor.OK
    assert maintainer_tool_capabilities.executable_exists(tmp_path, "local-tool")


def test_tool_capabilities_report_disabled_optional_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        maintainer_doctor_setup,
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

    result = maintainer_doctor.check_tool_capabilities(tmp_path, MaintainerConfig())

    assert result.status == maintainer_doctor.OK
    assert "disabled" in result.message


def test_tests_check_warns_when_tests_are_disabled(tmp_path: Path) -> None:
    result = maintainer_doctor.check_tests(tmp_path, MaintainerConfig(require_tests=False))

    assert result.status == maintainer_doctor.WARNING
    assert "disabled" in result.message


def test_tests_check_fails_and_passes_for_required_tests(tmp_path: Path) -> None:
    config = MaintainerConfig(test_roots=("tests",), require_tests=True)

    assert maintainer_doctor.check_tests(tmp_path, config).status == maintainer_doctor.ERROR

    (tmp_path / "tests").mkdir()

    assert maintainer_doctor.check_tests(tmp_path, config).status == maintainer_doctor.OK


def test_pre_commit_hook_warns_when_config_exists_but_hook_is_absent(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    (tmp_path / ".git" / "hooks").mkdir(parents=True)

    result = maintainer_doctor.check_pre_commit(tmp_path)

    assert result.status == maintainer_doctor.WARNING
    assert "not installed" in result.message


def test_pre_commit_hook_passes_when_installed(tmp_path: Path) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True)
    hook_path.write_text("#!/bin/sh\n", encoding="utf-8")

    result = maintainer_doctor.check_pre_commit(tmp_path)

    assert result.status == maintainer_doctor.OK


def test_codex_hooks_warn_and_pass(tmp_path: Path) -> None:
    assert maintainer_doctor.check_codex_hooks(tmp_path).status == maintainer_doctor.WARNING

    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = false\n", encoding="utf-8")

    assert maintainer_doctor.check_codex_hooks(tmp_path).status == maintainer_doctor.WARNING

    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")

    assert maintainer_doctor.check_codex_hooks(tmp_path).status == maintainer_doctor.OK


def test_claude_code_hooks_warn_and_pass(tmp_path: Path) -> None:
    assert maintainer_doctor.check_claude_code_hooks(tmp_path).status == maintainer_doctor.WARNING

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir()
    settings_path.write_text('{"hooks": {}}\n', encoding="utf-8")
    assert maintainer_doctor.check_claude_code_hooks(tmp_path).status == maintainer_doctor.WARNING

    hook_dir = tmp_path / ".claude" / "hooks"
    hook_dir.mkdir()
    for name in ("post_tool_use.py", "stop.py", "subagent_stop.py"):
        (hook_dir / name).write_text("agent_maintainer\n", encoding="utf-8")
    assert maintainer_doctor.check_claude_code_hooks(tmp_path).status == maintainer_doctor.WARNING

    settings_path.write_text(
        '{"hooks": {"Stop": [{"command": ".claude/hooks/stop.py"}]}}\n',
        encoding="utf-8",
    )
    assert maintainer_doctor.check_claude_code_hooks(tmp_path).status == maintainer_doctor.OK
