"""Tests repository-confined checked-in Gradle wrapper resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent_maintainer.ecosystems.java.wrapper import (
    GradleWrapperError,
    resolve_gradle_wrapper,
)


def write_wrapper(root: Path, name: str = "gradlew", *, executable: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    wrapper = root / name
    wrapper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    wrapper.chmod(0o755 if executable else 0o644)
    return wrapper


def test_resolves_executable_posix_wrapper_at_exact_gradle_root(tmp_path: Path) -> None:
    wrapper = write_wrapper(tmp_path / "backend")

    resolved = resolve_gradle_wrapper(tmp_path, "backend", platform="posix")

    assert resolved.workspace == tmp_path.resolve()
    assert resolved.gradle_root == (tmp_path / "backend").resolve()
    assert resolved.executable == wrapper.resolve()


def test_resolves_windows_batch_without_posix_execute_bit(tmp_path: Path) -> None:
    wrapper = write_wrapper(tmp_path, "gradlew.bat", executable=False)

    resolved = resolve_gradle_wrapper(tmp_path, ".", platform="windows")

    assert resolved.executable == wrapper.resolve()


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("missing", "checked-in Gradle wrapper is missing"),
        ("directory", "wrapper must be a regular file"),
        ("non-executable", "wrapper is not executable"),
    ],
)
def test_rejects_missing_non_file_and_non_executable_wrappers(
    tmp_path: Path,
    setup: str,
    message: str,
) -> None:
    if setup == "directory":
        (tmp_path / "gradlew").mkdir()
    elif setup == "non-executable":
        write_wrapper(tmp_path, executable=False)

    with pytest.raises(GradleWrapperError, match=message):
        resolve_gradle_wrapper(tmp_path, ".", platform="posix")


@pytest.mark.parametrize("gradle_root", ["../outside", "/tmp/outside"])
def test_rejects_gradle_root_escape(tmp_path: Path, gradle_root: str) -> None:
    with pytest.raises(GradleWrapperError, match="gradle_root escapes repository"):
        resolve_gradle_wrapper(tmp_path, gradle_root, platform="posix")


def test_rejects_gradle_root_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-root"
    write_wrapper(outside)
    (tmp_path / "backend").symlink_to(outside, target_is_directory=True)

    with pytest.raises(GradleWrapperError, match="gradle_root escapes repository"):
        resolve_gradle_wrapper(tmp_path, "backend", platform="posix")


def test_rejects_wrapper_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-wrapper"
    outside.mkdir()
    target = write_wrapper(outside)
    (tmp_path / "gradlew").symlink_to(target)

    with pytest.raises(GradleWrapperError, match="wrapper escapes gradle_root"):
        resolve_gradle_wrapper(tmp_path, ".", platform="posix")


def test_does_not_search_path_for_system_gradle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    write_wrapper(fake_bin, "gradle")
    monkeypatch.setenv("PATH", os.fspath(fake_bin))

    with pytest.raises(GradleWrapperError, match="checked-in Gradle wrapper is missing"):
        resolve_gradle_wrapper(tmp_path, ".", platform="posix")
