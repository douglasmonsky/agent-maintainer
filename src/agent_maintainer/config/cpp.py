"""Frozen public configuration model for the C/C++ CMake provider."""

from __future__ import annotations

from dataclasses import dataclass

PRECOMMIT_PROFILES = ("precommit", "full", "ci")
FULL_PROFILES = ("full", "ci")


@dataclass(frozen=True)
class CppCmakeConfig:
    """Resolved disabled-by-default C/C++ CMake provider configuration."""

    enabled: bool = False
    cmake_root: str = "."
    format_command: tuple[str, ...] = ()
    static_analysis_command: tuple[str, ...] = ()
    build_command: tuple[str, ...] = ()
    test_command: tuple[str, ...] = ()
    coverage_command: tuple[str, ...] = ()
    format_profiles: tuple[str, ...] = PRECOMMIT_PROFILES
    static_analysis_profiles: tuple[str, ...] = PRECOMMIT_PROFILES
    build_profiles: tuple[str, ...] = FULL_PROFILES
    test_profiles: tuple[str, ...] = FULL_PROFILES
    coverage_profiles: tuple[str, ...] = FULL_PROFILES
