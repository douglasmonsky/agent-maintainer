"""Tests for standalone helper scripts and guardrail entrypoint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ai_guardrails import cli as guardrail_cli
from ai_guardrails.core import args as guardrail_args
from ai_guardrails.core import bootstrap as guardrail_bootstrap

BOOTSTRAP_STATUS = 11
DOCTOR_STATUS = 14
INSTALL_STATUS = 12
VERIFY_STATUS = 13
GUIDANCE_STATUS = 15
UNKNOWN_COMMAND_STATUS = 2
DEPENDENCY_FAILURE_STATUS = 7


def test_justfile_full_output_recipe_uses_repo_roots() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    justfile = (repo_root / "justfile").read_text(encoding="utf-8")
    recipe = justfile.split("verify-full-output:", maxsplit=1)[1].split(
        "clean-verify-logs:",
        maxsplit=1,
    )[0]

    assert "--cov=src/ai_guardrails" in recipe
    assert "--cov=guardrail_lib" not in recipe
    assert "--cov-fail-under=90" in recipe
    assert "--cov-fail-under=80" not in recipe
    assert "radon cc src" not in recipe
    assert "pylint src" not in recipe
    assert "bandit -q -r src" not in recipe


def test_scripted_entrypoints_disable_python_bytecode_writes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pre_commit = (repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    justfile = (repo_root / "justfile").read_text(encoding="utf-8")

    assert "env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m ai_guardrails" in pre_commit
    assert 'export PYTHONDONTWRITEBYTECODE := "1"' in justfile


def test_guardrail_main_routes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardrail_cli, "bootstrap", lambda: BOOTSTRAP_STATUS)
    monkeypatch.setattr(guardrail_cli, "doctor_main", lambda args: DOCTOR_STATUS)
    monkeypatch.setattr(guardrail_cli, "guidance_main", lambda args: GUIDANCE_STATUS)
    monkeypatch.setattr(guardrail_cli, "install", lambda: INSTALL_STATUS)
    monkeypatch.setattr(guardrail_cli, "verify_main", lambda args: VERIFY_STATUS)

    assert guardrail_cli.main(["bootstrap"]) == BOOTSTRAP_STATUS
    assert guardrail_cli.main(["doctor", "--strict"]) == DOCTOR_STATUS
    assert guardrail_cli.main(["guidance", "--check"]) == GUIDANCE_STATUS
    assert guardrail_cli.main(["install"]) == INSTALL_STATUS
    assert guardrail_cli.main(["verify", "--profile", "fast"]) == VERIFY_STATUS
    assert guardrail_cli.main(["unknown"]) == UNKNOWN_COMMAND_STATUS


def test_verify_parser_accepts_manual_profile() -> None:
    args = guardrail_args.parse_args(["--profile", "manual"])

    assert args.profile == "manual"


def test_guardrail_package_entrypoint_help() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "ai_guardrails", "--help"],
        cwd=repo_root,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "python -m ai_guardrails doctor" in result.stdout


def test_guardrail_project_root_prefers_working_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    nested = repo_root / "nested"
    nested.mkdir(parents=True)
    (repo_root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")

    monkeypatch.chdir(nested)

    assert guardrail_bootstrap.project_root() == repo_root


def test_guardrail_install_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert guardrail_bootstrap.install_pre_commit(tmp_path) == 0

    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(guardrail_bootstrap, "find_pre_commit", lambda repo_root: None)
    assert guardrail_bootstrap.install_pre_commit(tmp_path) == 1

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "example"\n', encoding="utf-8")
    dependency_file = tmp_path / "config" / "dev-dependencies.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")

    calls: list[list[str]] = []
    repairs: list[tuple[Path, Path]] = []
    links: list[tuple[Path, Path]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(guardrail_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "repair_pth_visibility",
        lambda repo_root, python_path_arg: repairs.append((repo_root, python_path_arg)),
    )
    monkeypatch.setattr(
        guardrail_bootstrap,
        "ensure_editable_package_link",
        lambda repo_root, python_path_arg: links.append((repo_root, python_path_arg)),
    )
    assert guardrail_bootstrap.install_dependencies(tmp_path, python_path) == 0
    assert calls[0][-2:] == ["-r", "config/dev-dependencies.txt"]
    assert calls[1][-4:] == ["install", "-e", ".", "--no-deps"]
    assert repairs == [(tmp_path, python_path), (tmp_path, python_path)]
    assert links == [(tmp_path, python_path)]

    (tmp_path / "config" / "dev-lock.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
    calls.clear()
    repairs.clear()
    links.clear()
    assert guardrail_bootstrap.install_dependencies(tmp_path, python_path) == 0
    assert calls[0][-2:] == ["-r", "config/dev-lock.txt"]
    assert calls[1][-4:] == ["install", "-e", ".", "--no-deps"]
    assert repairs == [(tmp_path, python_path), (tmp_path, python_path)]
    assert links == [(tmp_path, python_path)]


def test_guardrail_bootstrap_and_virtualenv_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"
    monkeypatch.setattr(guardrail_bootstrap.shutil, "which", lambda name: "/usr/bin/python3")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        python_path.parent.mkdir(parents=True)
        python_path.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(guardrail_bootstrap.subprocess, "run", fake_run)

    assert guardrail_bootstrap.ensure_virtualenv(tmp_path) == python_path

    monkeypatch.setattr(guardrail_bootstrap, "ensure_virtualenv", lambda repo_root: python_path)
    monkeypatch.setattr(guardrail_bootstrap, "install_dependencies", lambda repo_root, path: 0)
    monkeypatch.setattr(guardrail_bootstrap, "install", lambda: 0)
    assert guardrail_bootstrap.bootstrap() == 0


def test_guardrail_bootstrap_failure_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(guardrail_bootstrap, "ensure_virtualenv", lambda repo_root: None)
    assert guardrail_bootstrap.bootstrap() == 1

    python_path = tmp_path / ".venv" / "bin" / "python"
    monkeypatch.setattr(guardrail_bootstrap, "ensure_virtualenv", lambda repo_root: python_path)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "install_dependencies",
        lambda repo_root, path: DEPENDENCY_FAILURE_STATUS,
    )
    assert guardrail_bootstrap.bootstrap() == DEPENDENCY_FAILURE_STATUS


def test_guardrail_virtualenv_failure_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    existing = tmp_path / ".venv" / "bin" / "python"
    existing.parent.mkdir(parents=True)
    existing.write_text("", encoding="utf-8")
    assert guardrail_bootstrap.ensure_virtualenv(tmp_path) == existing

    missing_python_root = tmp_path / "missing-python"
    monkeypatch.setattr(guardrail_bootstrap.shutil, "which", lambda name: None)
    assert guardrail_bootstrap.ensure_virtualenv(missing_python_root) is None
    assert "python3 command not found" in capsys.readouterr().err

    failed_venv_root = tmp_path / "failed-venv"
    monkeypatch.setattr(guardrail_bootstrap.shutil, "which", lambda name: "/usr/bin/python3")
    monkeypatch.setattr(
        guardrail_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, "", ""),
    )
    assert guardrail_bootstrap.ensure_virtualenv(failed_venv_root) is None


def test_guardrail_dependency_install_requires_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    python_path = tmp_path / ".venv" / "bin" / "python"

    assert guardrail_bootstrap.install_dependencies(tmp_path, python_path) == 1
    assert "dev-lock.txt or config/dev-dependencies.txt" in capsys.readouterr().err


def test_guardrail_repairs_hidden_pth_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    pth_file = site_packages / "__editable__.ai_guardrails.pth"
    pth_file.write_text("src\n", encoding="utf-8")
    cleared: list[tuple[Path, int]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, f"{site_packages}\n", "")

    monkeypatch.setattr(guardrail_bootstrap, "hidden_file_flag", lambda: 1)
    monkeypatch.setattr(guardrail_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "clear_hidden_file_flag",
        lambda path, flag: cleared.append((path, flag)),
    )

    guardrail_bootstrap.repair_pth_visibility(tmp_path, tmp_path / "python")

    assert cleared == [(pth_file, 1)]


def test_guardrail_skips_pth_repair_when_platform_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(guardrail_bootstrap, "hidden_file_flag", lambda: None)
    monkeypatch.setattr(
        guardrail_bootstrap.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("site package lookup should be skipped"),
    )

    guardrail_bootstrap.repair_pth_visibility(tmp_path, tmp_path / "python")


def test_guardrail_creates_editable_package_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_package = tmp_path / "src" / "ai_guardrails"
    source_package.mkdir(parents=True)
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    monkeypatch.setattr(
        guardrail_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    guardrail_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    package_link = site_packages / "ai_guardrails"
    assert package_link.is_symlink()
    assert package_link.resolve() == source_package


def test_guardrail_does_not_replace_real_installed_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "src" / "ai_guardrails").mkdir(parents=True)
    site_packages = tmp_path / "site-packages"
    installed_package = site_packages / "ai_guardrails"
    installed_package.mkdir(parents=True)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    guardrail_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    assert installed_package.is_dir()
    assert not installed_package.is_symlink()


def test_guardrail_dependency_install_explains_python_package_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dependency_file = tmp_path / "config" / "dev-lock.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest==9.1.1\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        guardrail_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )

    assert guardrail_bootstrap.install_dependencies(tmp_path, python_path) == 0

    output = capsys.readouterr().out
    assert "Installing Python package guardrail tools" in output
    assert "External binaries, GitHub-only tools, and manual optional tools" in output


def test_guardrail_reports_codex_hooks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text("[features]\nhooks = true\n", encoding="utf-8")

    guardrail_bootstrap.report_codex_hooks(tmp_path)

    assert "Codex hooks configured" in capsys.readouterr().out
