"""Tests bootstrap and local install helper behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_guardrails.core import bootstrap as guardrail_bootstrap

INSTALL_STATUS = 12
DEPENDENCY_FAILURE_STATUS = 7


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


def test_guardrail_project_root_falls_back_to_package_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd = tmp_path / "outside"
    package_root = tmp_path / "package-root"
    module_path = package_root / "src" / "ai_guardrails" / "core" / "bootstrap.py"
    cwd.mkdir()
    module_path.parent.mkdir(parents=True)
    module_path.write_text("", encoding="utf-8")
    (package_root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")

    monkeypatch.chdir(cwd)
    monkeypatch.setattr(guardrail_bootstrap, "__file__", str(module_path))

    assert guardrail_bootstrap.project_root() == package_root


def test_guardrail_project_root_falls_back_to_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = tmp_path / "package" / "bootstrap.py"
    module_path.parent.mkdir()
    module_path.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(guardrail_bootstrap, "__file__", str(module_path))

    assert guardrail_bootstrap.project_root() == tmp_path


def test_guardrail_install_runs_hook_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(guardrail_bootstrap, "project_root", lambda: tmp_path)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "install_pre_commit",
        lambda repo_root: calls.append(("pre-commit", repo_root)) or INSTALL_STATUS,
    )
    monkeypatch.setattr(
        guardrail_bootstrap,
        "report_codex_hooks",
        lambda repo_root: calls.append(("codex-hooks", repo_root)),
    )

    assert guardrail_bootstrap.install() == INSTALL_STATUS
    assert calls == [("pre-commit", tmp_path), ("codex-hooks", tmp_path)]


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


def test_guardrail_dependency_install_returns_pip_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependency_file = tmp_path / "config" / "dev-dependencies.txt"
    dependency_file.parent.mkdir()
    dependency_file.write_text("pytest\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"

    monkeypatch.setattr(
        guardrail_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, DEPENDENCY_FAILURE_STATUS, "", ""
        ),
    )

    assert (
        guardrail_bootstrap.install_dependencies(tmp_path, python_path) == DEPENDENCY_FAILURE_STATUS
    )


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


def test_guardrail_site_package_paths_returns_empty_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        guardrail_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 2, "", ""),
    )

    assert guardrail_bootstrap.site_package_paths(tmp_path, tmp_path / "python") == ()


def test_guardrail_hidden_file_flag_requires_chflags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(guardrail_bootstrap.os, "chflags", None, raising=False)

    assert guardrail_bootstrap.hidden_file_flag() is None


def test_guardrail_clear_hidden_file_flag_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pth_file = tmp_path / "tool.pth"
    pth_file.write_text("src\n", encoding="utf-8")
    calls: list[tuple[Path, int]] = []

    monkeypatch.setattr(guardrail_bootstrap.os, "chflags", None, raising=False)
    guardrail_bootstrap.clear_hidden_file_flag(pth_file, 1)
    assert not calls

    monkeypatch.setattr(
        guardrail_bootstrap.os,
        "chflags",
        lambda path, flags: calls.append((path, flags)),
        raising=False,
    )
    guardrail_bootstrap.clear_hidden_file_flag(pth_file, 1)
    assert not calls

    class BrokenPath:
        """Path-like object whose stat call fails."""

        def stat(self) -> object:
            raise OSError

    guardrail_bootstrap.clear_hidden_file_flag(BrokenPath(), 1)  # type: ignore[arg-type]
    assert not calls


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


def test_guardrail_replaces_stale_editable_package_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_package = tmp_path / "src" / "ai_guardrails"
    stale_package = tmp_path / "stale" / "ai_guardrails"
    site_packages = tmp_path / "site-packages"
    source_package.mkdir(parents=True)
    stale_package.mkdir(parents=True)
    site_packages.mkdir()
    package_link = site_packages / "ai_guardrails"
    package_link.symlink_to(stale_package, target_is_directory=True)
    monkeypatch.setattr(
        guardrail_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    guardrail_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    assert package_link.resolve() == source_package


def test_guardrail_skips_editable_package_link_when_source_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    monkeypatch.setattr(
        guardrail_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    guardrail_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    assert not (site_packages / "ai_guardrails").exists()


def test_guardrail_install_pre_commit_success_and_path_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(guardrail_bootstrap, "find_pre_commit", lambda repo_root: "pre-commit")
    monkeypatch.setattr(
        guardrail_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "", ""),
    )

    assert guardrail_bootstrap.install_pre_commit(tmp_path) == 0


def test_guardrail_find_pre_commit_uses_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(guardrail_bootstrap.shutil, "which", lambda name: "/bin/pre-commit")

    assert guardrail_bootstrap.find_pre_commit(tmp_path) == "/bin/pre-commit"


def test_guardrail_report_codex_hooks_absent_is_quiet(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    guardrail_bootstrap.report_codex_hooks(tmp_path)

    assert capsys.readouterr().out == ""


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
