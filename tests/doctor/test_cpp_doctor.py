"""Tests static C/C++ CMake doctor diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.core.config import MaintainerConfig
from agent_maintainer.doctor import cli as maintainer_doctor
from agent_maintainer.doctor.support import cpp_provider
from agent_maintainer.doctor.support.models import (
    ACTIVE,
    MISSING,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)


def test_cpp_doctor_is_silent_when_provider_disabled(tmp_path: Path) -> None:
    """Disabled C/C++ support emits no provider-specific rows."""
    assert cpp_provider.check_cpp_provider(tmp_path, MaintainerConfig()) == ()


def test_cpp_doctor_warns_when_cmake_root_is_missing(tmp_path: Path) -> None:
    """The configured CMake root must already exist."""
    config = _cpp_config(cmake_root="native")

    result = _cpp_results(tmp_path, config)["cpp-cmake-root"]

    assert result.status == WARNING
    assert result.state == MISSING
    assert "native" in result.message


def test_cpp_doctor_warns_when_no_commands_are_configured(tmp_path: Path) -> None:
    """An enabled provider needs at least one explicit command."""
    config = MaintainerConfig(cpp=CppCmakeConfig(enabled=True))

    result = _cpp_results(tmp_path, config)["cpp-command-config"]

    assert result.status == WARNING
    assert result.state == UNSAFE_CONFIG


def test_cpp_doctor_warns_for_missing_system_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bare executables must resolve on the configured search path."""
    monkeypatch.setattr(cpp_provider.shutil, "which", lambda *_args, **_kwargs: None)

    result = _cpp_results(tmp_path, _cpp_config())["cpp-command-executables"]

    assert result.status == WARNING
    assert result.state == MISSING
    assert "cpp-format (missing-cpp-tool)" in result.message


@pytest.mark.parametrize("wrapper_kind", ["outside", "symlink"])
def test_cpp_doctor_rejects_unsafe_repository_wrapper(
    tmp_path: Path,
    wrapper_kind: str,
) -> None:
    """Explicit wrappers cannot escape the repository or use a symlink."""
    outside = tmp_path.parent / f"{tmp_path.name}-cpp-tool"
    _write_executable(outside)
    executable = str(outside)
    if wrapper_kind == "symlink":
        wrapper = tmp_path / "cpp-tool"
        wrapper.symlink_to(outside)
        executable = "./cpp-tool"
    config = _cpp_config(format_command=(executable, "--check"))

    result = _cpp_results(tmp_path, config)["cpp-command-executables"]

    assert result.status == WARNING
    assert result.state == UNSAFE_CONFIG


def test_cpp_doctor_accepts_repository_executable_wrapper(tmp_path: Path) -> None:
    """A confined regular executable wrapper is safe static configuration."""
    _write_executable(tmp_path / "tools" / "cpp-format")
    config = _cpp_config(format_command=("./tools/cpp-format", "--check"))

    result = _cpp_results(tmp_path, config)["cpp-command-executables"]

    assert result.status == OK
    assert result.state == ACTIVE


def test_cpp_doctor_rejects_symlink_traversed_before_parent_segment(
    tmp_path: Path,
) -> None:
    """Lexical parent traversal cannot erase an earlier symlink component."""
    (tmp_path / "real-dir").mkdir()
    (tmp_path / "linked-dir").symlink_to(tmp_path / "real-dir", target_is_directory=True)
    _write_executable(tmp_path / "cpp-tool")
    config = _cpp_config(
        format_command=("./linked-dir/../cpp-tool", "--check"),
    )

    result = _cpp_results(tmp_path, config)["cpp-command-executables"]

    assert result.status == WARNING
    assert result.state == UNSAFE_CONFIG


def test_cpp_doctor_warns_when_preset_command_has_no_preset_file(tmp_path: Path) -> None:
    """Preset-based commands need a checked-in CMake preset file."""
    config = _cpp_config(format_command=("missing-cpp-tool", "--preset", "lint"))

    results = cpp_provider.check_cpp_provider(tmp_path, config)

    assert [result.name for result in results] == [
        "cpp-cmake-root",
        "cpp-command-config",
        "cpp-command-executables",
        "cpp-cmake-presets",
    ]
    assert results[-1].status == WARNING
    assert results[-1].state == MISSING


@pytest.mark.parametrize("preset_name", ["CMakePresets.json", "CMakeUserPresets.json"])
def test_cpp_doctor_accepts_existing_preset_file(
    tmp_path: Path,
    preset_name: str,
) -> None:
    """Either standard CMake preset filename satisfies static diagnostics."""
    (tmp_path / preset_name).write_text("{}\n", encoding="utf-8")
    config = _cpp_config(format_command=("missing-cpp-tool", "--preset=lint"))

    result = _cpp_results(tmp_path, config)["cpp-cmake-presets"]

    assert result.status == OK
    assert result.state == ACTIVE


def test_cpp_doctor_never_executes_configured_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal doctor only reads configuration and the filesystem."""

    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("normal doctor must not execute C/C++ commands")

    monkeypatch.setattr(subprocess, "run", fail_run)

    assert cpp_provider.check_cpp_provider(tmp_path, _cpp_config())


def test_run_doctor_includes_cpp_rows_only_when_enabled(tmp_path: Path) -> None:
    """Full doctor appends C/C++ diagnostics only for explicit enablement."""
    disabled = maintainer_doctor.run_doctor(tmp_path, MaintainerConfig())
    enabled = maintainer_doctor.run_doctor(tmp_path, _cpp_config())

    assert not [result for result in disabled if result.name.startswith("cpp-")]
    assert [result for result in enabled if result.name == "cpp-command-config"]


def _cpp_config(
    *,
    cmake_root: str = ".",
    format_command: tuple[str, ...] = ("missing-cpp-tool", "--check"),
) -> MaintainerConfig:
    return MaintainerConfig(
        cpp=CppCmakeConfig(
            enabled=True,
            cmake_root=cmake_root,
            format_command=format_command,
        )
    )


def _cpp_results(
    root: Path,
    config: MaintainerConfig,
) -> dict[str, DoctorResult]:
    return {result.name: result for result in cpp_provider.check_cpp_provider(root, config)}


def _write_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
