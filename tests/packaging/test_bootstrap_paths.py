"""Tests bootstrap filesystem and package path behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import pytest

from agent_maintainer.core import bootstrap as maintainer_bootstrap


def test_maintainer_project_root_prefers_working_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    nested = repo_root / "nested"
    nested.mkdir(parents=True)
    (repo_root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")

    monkeypatch.chdir(nested)

    assert maintainer_bootstrap.project_root() == repo_root


def test_maintainer_project_root_falls_back_to_package_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd = tmp_path / "outside"
    package_root = tmp_path / "package-root"
    module_path = package_root / "src" / "agent_maintainer" / "core" / "bootstrap.py"
    cwd.mkdir()
    module_path.parent.mkdir(parents=True)
    module_path.write_text("", encoding="utf-8")
    (package_root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")

    monkeypatch.chdir(cwd)
    monkeypatch.setattr(maintainer_bootstrap, "__file__", str(module_path))

    assert maintainer_bootstrap.project_root() == package_root


def test_maintainer_project_root_falls_back_to_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_path = tmp_path / "package" / "bootstrap.py"
    module_path.parent.mkdir()
    module_path.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(maintainer_bootstrap, "__file__", str(module_path))

    assert maintainer_bootstrap.project_root() == tmp_path


def test_maintainer_repairs_hidden_pth_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    pth_file = site_packages / "__editable__.agent_maintainer.pth"
    pth_file.write_text("src\n", encoding="utf-8")
    cleared: list[tuple[Path, int]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, f"{site_packages}\n", "")

    monkeypatch.setattr(maintainer_bootstrap, "hidden_file_flag", lambda: 1)
    monkeypatch.setattr(maintainer_bootstrap.subprocess, "run", fake_run)
    monkeypatch.setattr(
        maintainer_bootstrap,
        "clear_hidden_file_flag",
        lambda path, flag: cleared.append((path, flag)),
    )

    maintainer_bootstrap.repair_pth_visibility(tmp_path, tmp_path / "python")

    assert cleared == [(pth_file, 1)]


def test_maintainer_skips_pth_repair_when_platform_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maintainer_bootstrap, "hidden_file_flag", lambda: None)
    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("site package lookup should be skipped"),
    )

    maintainer_bootstrap.repair_pth_visibility(tmp_path, tmp_path / "python")


def test_maintainer_site_package_paths_returns_empty_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 2, "", ""),
    )

    assert maintainer_bootstrap.site_package_paths(tmp_path, tmp_path / "python") == ()


def test_maintainer_hidden_file_flag_requires_chflags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maintainer_bootstrap, "chflags_command", lambda: None)

    assert maintainer_bootstrap.hidden_file_flag() is None


def test_maintainer_hidden_file_flag_uses_chflags_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maintainer_bootstrap, "chflags_command", lambda: "chflags")

    assert maintainer_bootstrap.hidden_file_flag() == maintainer_bootstrap.MACOS_HIDDEN_FILE_FLAG


def test_maintainer_clear_hidden_file_flag_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pth_file = tmp_path / "tool.pth"
    pth_file.write_text("src\n", encoding="utf-8")
    calls: list[list[str]] = []

    monkeypatch.setattr(maintainer_bootstrap, "chflags_command", lambda: None)
    maintainer_bootstrap.clear_hidden_file_flag(pth_file, 1)
    assert not calls

    monkeypatch.setattr(maintainer_bootstrap, "chflags_command", lambda: "chflags")
    monkeypatch.setattr(
        maintainer_bootstrap.subprocess,
        "run",
        lambda command, **_kwargs: (
            calls.append(command) or subprocess.CompletedProcess(command, 0, "", "")
        ),
    )
    maintainer_bootstrap.clear_hidden_file_flag(pth_file, 1)
    assert not calls

    class BrokenPath:
        """Path-like object whose stat call fails."""

        def stat(self) -> object:
            raise OSError

    maintainer_bootstrap.clear_hidden_file_flag(cast("Path", BrokenPath()), 1)
    assert not calls

    class HiddenPath:
        """Path-like object with hidden file stat flags."""

        def stat(self) -> object:
            return type("StatResult", (), {"st_flags": 1})()

        def __str__(self) -> str:
            return "hidden.pth"

    maintainer_bootstrap.clear_hidden_file_flag(cast("Path", HiddenPath()), 1)
    assert calls == [["chflags", "nohidden", "hidden.pth"]]


def test_maintainer_creates_editable_package_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_package = tmp_path / "src" / "agent_maintainer"
    source_package.mkdir(parents=True)
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    monkeypatch.setattr(
        maintainer_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    maintainer_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    package_link = site_packages / "agent_maintainer"
    assert package_link.is_symlink()
    assert package_link.resolve() == source_package


def test_maintainer_does_not_replace_real_installed_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "src" / "agent_maintainer").mkdir(parents=True)
    site_packages = tmp_path / "site-packages"
    installed_package = site_packages / "agent_maintainer"
    installed_package.mkdir(parents=True)
    monkeypatch.setattr(
        maintainer_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    maintainer_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    assert installed_package.is_dir()
    assert not installed_package.is_symlink()


def test_maintainer_replaces_stale_editable_package_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_package = tmp_path / "src" / "agent_maintainer"
    stale_package = tmp_path / "stale" / "agent_maintainer"
    site_packages = tmp_path / "site-packages"
    source_package.mkdir(parents=True)
    stale_package.mkdir(parents=True)
    site_packages.mkdir()
    package_link = site_packages / "agent_maintainer"
    package_link.symlink_to(stale_package, target_is_directory=True)
    monkeypatch.setattr(
        maintainer_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    maintainer_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    assert package_link.resolve() == source_package


def test_maintainer_skips_editable_package_link_when_source_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    monkeypatch.setattr(
        maintainer_bootstrap,
        "site_package_paths",
        lambda repo_root, python_path: (site_packages,),
    )

    maintainer_bootstrap.ensure_editable_package_link(tmp_path, tmp_path / "python")

    assert not (site_packages / "agent_maintainer").exists()
