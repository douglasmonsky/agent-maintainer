"""Static doctor checks for the experimental C/C++ CMake provider."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.doctor.support.models import (
    ACTIVE,
    MISSING,
    NOT_APPLICABLE,
    OK,
    UNSAFE_CONFIG,
    WARNING,
    DoctorResult,
)
from agent_maintainer.doctor.support.providers import path_with_local_bins

CppCommand = tuple[str, tuple[str, ...]]


def check_cpp_provider(
    repo_root: Path,
    config: MaintainerConfig,
) -> tuple[DoctorResult, ...]:
    """Return static C/C++ CMake health without executing a command."""
    if not config.cpp.enabled:
        return ()
    commands = configured_cpp_commands(config.cpp)
    results = (
        _check_cmake_root(repo_root, config.cpp),
        _check_command_config(commands),
        _check_command_executables(repo_root, commands),
    )
    if not _uses_cmake_preset(commands):
        return results
    return (*results, _check_cmake_presets(repo_root, config.cpp))


def configured_cpp_commands(cpp: CppCmakeConfig) -> tuple[CppCommand, ...]:
    """Return stable check-name and non-empty command pairs."""
    configured = (
        ("cpp-format", cpp.format_command),
        ("cpp-static-analysis", cpp.static_analysis_command),
        ("cpp-build", cpp.build_command),
        ("cpp-test", cpp.test_command),
        ("cpp-coverage", cpp.coverage_command),
    )
    return tuple((name, command) for name, command in configured if command)


def resolve_repository_wrapper(repo_root: Path, executable: str) -> Path:
    """Resolve one explicit path-like executable to a confined regular file."""
    canonical_root = repo_root.resolve(strict=True)
    if not _is_path_like(executable):
        resolved = shutil.which(executable, path=path_with_local_bins(canonical_root))
        if resolved is None:
            raise FileNotFoundError(f"executable is unavailable: {executable}")
        return Path(resolved)

    configured = Path(executable)
    candidate = configured if configured.is_absolute() else canonical_root / configured
    _reject_symlink_path(candidate, canonical_root)
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"wrapper is missing: {executable}") from exc
    if not resolved.is_relative_to(canonical_root):
        raise ValueError(f"wrapper escapes repository: {executable}")
    if not resolved.is_file():
        raise ValueError(f"wrapper is not a regular file: {executable}")
    if os.name == "posix" and not os.access(resolved, os.X_OK):
        raise ValueError(f"wrapper is not executable: {executable}")
    return resolved


def _check_cmake_root(repo_root: Path, cpp: CppCmakeConfig) -> DoctorResult:
    try:
        root = _resolve_cmake_root(repo_root, cpp.cmake_root)
    except ValueError as exc:
        return DoctorResult(
            "cpp-cmake-root",
            WARNING,
            f"C/C++ CMake root is unsafe: {exc}.",
            state=UNSAFE_CONFIG,
            hint="Set cpp.cmake_root to an existing repository-confined directory.",
        )
    except OSError as exc:
        return DoctorResult(
            "cpp-cmake-root",
            WARNING,
            f"C/C++ CMake root is unavailable at {cpp.cmake_root}: {exc}.",
            state=MISSING,
            hint="Create or correct cpp.cmake_root; doctor never creates it.",
        )
    relative = root.relative_to(repo_root.resolve(strict=True)).as_posix()
    return DoctorResult(
        "cpp-cmake-root",
        OK,
        f"C/C++ CMake root is ready: {relative}.",
        state=ACTIVE,
    )


def _check_command_config(commands: tuple[CppCommand, ...]) -> DoctorResult:
    if not commands:
        return DoctorResult(
            "cpp-command-config",
            WARNING,
            "C/C++ provider is enabled but no commands are configured.",
            state=UNSAFE_CONFIG,
            hint="Configure explicit cpp command fields or disable cpp.enabled.",
        )
    names = ", ".join(name for name, _command in commands)
    return DoctorResult(
        "cpp-command-config",
        OK,
        f"Configured C/C++ command checks: {names}.",
        state=ACTIVE,
    )


def _check_command_executables(
    repo_root: Path,
    commands: tuple[CppCommand, ...],
) -> DoctorResult:
    if not commands:
        return DoctorResult(
            "cpp-command-executables",
            OK,
            "No configured C/C++ command executables to resolve.",
            state=NOT_APPLICABLE,
        )
    missing: list[str] = []
    unsafe: list[str] = []
    for check_name, command in commands:
        executable = command[0]
        try:
            resolve_repository_wrapper(repo_root, executable)
        except ValueError:
            unsafe.append(f"{check_name} ({executable})")
        except OSError:
            missing.append(f"{check_name} ({executable})")
    if unsafe:
        names = ", ".join(unsafe)
        return DoctorResult(
            "cpp-command-executables",
            WARNING,
            f"Unsafe C/C++ command executable(s): {names}.",
            state=UNSAFE_CONFIG,
            hint="Use system executables or repository-confined regular executable wrappers.",
        )
    if missing:
        names = ", ".join(missing)
        return DoctorResult(
            "cpp-command-executables",
            WARNING,
            f"Missing C/C++ command executable(s): {names}.",
            state=MISSING,
            hint="Install missing tools or configure explicit repository wrappers.",
        )
    names = ", ".join(name for name, _command in commands)
    return DoctorResult(
        "cpp-command-executables",
        OK,
        f"C/C++ command executables are available: {names}.",
        state=ACTIVE,
    )


def _check_cmake_presets(repo_root: Path, cpp: CppCmakeConfig) -> DoctorResult:
    try:
        cmake_root = _resolve_cmake_root(repo_root, cpp.cmake_root)
    except (OSError, ValueError):
        return _missing_preset_result(cpp.cmake_root)
    preset_names = ("CMakePresets.json", "CMakeUserPresets.json")
    present = tuple(name for name in preset_names if (cmake_root / name).is_file())
    if not present:
        return _missing_preset_result(cpp.cmake_root)
    return DoctorResult(
        "cpp-cmake-presets",
        OK,
        f"CMake preset file is available: {present[0]}.",
        state=ACTIVE,
    )


def _missing_preset_result(cmake_root: str) -> DoctorResult:
    return DoctorResult(
        "cpp-cmake-presets",
        WARNING,
        f"Preset command configured without a CMake preset file under {cmake_root}.",
        state=MISSING,
        hint="Add CMakePresets.json or CMakeUserPresets.json under cpp.cmake_root.",
    )


def _resolve_cmake_root(repo_root: Path, configured_root: str) -> Path:
    canonical_root = repo_root.resolve(strict=True)
    candidate = (canonical_root / configured_root).resolve(strict=True)
    if not candidate.is_relative_to(canonical_root):
        raise ValueError("cpp.cmake_root escapes repository")
    if not candidate.is_dir():
        raise FileNotFoundError("not an existing directory")
    return candidate


def _uses_cmake_preset(commands: tuple[CppCommand, ...]) -> bool:
    return any(
        argument == "--preset" or argument.startswith("--preset=")
        for _name, command in commands
        for argument in command[1:]
    )


def _is_path_like(executable: str) -> bool:
    return (
        "/" in executable
        or "\\" in executable
        or executable.startswith(".")
        or re.match(r"^[A-Za-z]:", executable) is not None
    )


def _reject_symlink_path(candidate: Path, repo_root: Path) -> None:
    lexical = Path(os.path.abspath(candidate))
    if not lexical.is_relative_to(repo_root):
        raise ValueError(f"wrapper escapes repository: {candidate}")
    relative = lexical.relative_to(repo_root)
    current = repo_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"wrapper uses a symlink: {candidate}")
