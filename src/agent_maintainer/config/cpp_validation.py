"""Fail-closed validation for C/C++ CMake provider configuration."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from agent_maintainer import models
from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config.issues import ConfigIssue

COMMAND_FIELDS = (
    "format_command",
    "static_analysis_command",
    "build_command",
    "test_command",
    "coverage_command",
)
PROFILE_FIELDS = (
    "format_profiles",
    "static_analysis_profiles",
    "build_profiles",
    "test_profiles",
    "coverage_profiles",
)
SHELL_EXECUTABLES = frozenset(("bash", "cmd", "powershell", "pwsh", "sh", "zsh"))
SHELL_CONTROL_TOKENS = frozenset(("&&", ";", "<", ">", ">>", "|", "||"))


def cpp_issues(cpp: CppCmakeConfig, *, source: str) -> tuple[ConfigIssue, ...]:
    """Return deterministic C/C++ provider configuration issues."""

    issues: list[ConfigIssue] = []
    normalized_root = cpp.cmake_root.replace("\\", "/")
    root_path = PurePosixPath(normalized_root)
    windows_root = PureWindowsPath(cpp.cmake_root)
    if (
        root_path.is_absolute()
        or ".." in root_path.parts
        or bool(windows_root.drive)
        or bool(windows_root.anchor)
    ):
        issues.append(ConfigIssue(source, "cpp.cmake_root", "must stay repository-relative"))
    issues.extend(_command_issues(cpp, source=source))
    issues.extend(_profile_issues(cpp, source=source))
    return tuple(issues)


def _command_issues(cpp: CppCmakeConfig, *, source: str) -> tuple[ConfigIssue, ...]:
    return tuple(
        issue
        for field_name in COMMAND_FIELDS
        for issue in _command_field_issues(
            getattr(cpp, field_name),
            field_name=field_name,
            source=source,
        )
    )


def _command_field_issues(
    command: tuple[str, ...],
    *,
    field_name: str,
    source: str,
) -> tuple[ConfigIssue, ...]:
    issues: list[ConfigIssue] = []
    if any(not item for item in command):
        issues.append(ConfigIssue(source, f"cpp.{field_name}", "must not contain empty elements"))
    executable_name = _executable_name(command)
    if executable_name in SHELL_EXECUTABLES:
        issues.append(
            ConfigIssue(source, f"cpp.{field_name}", "must not invoke a shell executable")
        )
    if any(item in SHELL_CONTROL_TOKENS for item in command):
        issues.append(
            ConfigIssue(source, f"cpp.{field_name}", "must not contain shell control tokens")
        )
    return tuple(issues)


def _executable_name(command: tuple[str, ...]) -> str:
    if not command:
        return ""
    return PurePosixPath(command[0].replace("\\", "/")).name.lower().removesuffix(".exe")


def _profile_issues(cpp: CppCmakeConfig, *, source: str) -> tuple[ConfigIssue, ...]:
    return tuple(
        issue
        for field_name in PROFILE_FIELDS
        for issue in _profile_field_issues(
            getattr(cpp, field_name),
            field_name=field_name,
            source=source,
        )
    )


def _profile_field_issues(
    profiles: tuple[str, ...],
    *,
    field_name: str,
    source: str,
) -> tuple[ConfigIssue, ...]:
    issues: list[ConfigIssue] = []
    if len(profiles) != len(set(profiles)):
        issues.append(ConfigIssue(source, f"cpp.{field_name}", "profiles must be unique"))
    invalid = sorted(set(profiles) - models.VALID_PROFILES)
    if invalid:
        invalid_names = ", ".join(invalid)
        issues.append(
            ConfigIssue(source, f"cpp.{field_name}", f"invalid profiles: {invalid_names}")
        )
    return tuple(issues)
