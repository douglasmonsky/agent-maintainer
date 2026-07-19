"""Tests for the nested C/C++ CMake configuration contract."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from agent_maintainer.config import loader, registry
from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.config.schema import MaintainerConfig
from agent_maintainer.config.validation import ConfigValidationError


def apply_cpp(raw: object) -> MaintainerConfig:
    return loader.apply_pyproject(MaintainerConfig(), {"cpp": raw})


def test_cpp_defaults_are_frozen_and_disabled() -> None:
    cpp = MaintainerConfig().cpp

    assert cpp == CppCmakeConfig()
    assert cpp.enabled is False
    assert cpp.cmake_root == "."
    assert cpp.format_command == ()
    assert cpp.static_analysis_command == ()
    assert cpp.build_command == ()
    assert cpp.test_command == ()
    assert cpp.coverage_command == ()
    assert cpp.format_profiles == ("precommit", "full", "ci")
    assert cpp.static_analysis_profiles == ("precommit", "full", "ci")
    assert cpp.build_profiles == ("full", "ci")
    assert cpp.test_profiles == ("full", "ci")
    assert cpp.coverage_profiles == ("full", "ci")
    with pytest.raises(FrozenInstanceError):
        cpp.enabled = True  # type: ignore[misc]


def test_cpp_is_a_nested_table_not_a_scalar_registry_field() -> None:
    assert "cpp" in registry.top_level_toml_keys()
    assert "cpp" not in registry.FIELD_SPECS


def test_complete_cpp_table_is_coerced_without_shell_parsing() -> None:
    cpp = apply_cpp(
        {
            "enabled": True,
            "cmake_root": "native",
            "format_command": ["cmake", "--build", "--preset", "ci", "--target", "format-check"],
            "static_analysis_command": ["./ci/static-analysis"],
            "build_command": ["cmake", "--build", "--preset", "ci"],
            "test_command": ["ctest", "--preset", "ci"],
            "coverage_command": ["./ci/coverage"],
            "format_profiles": ["precommit", "ci"],
            "static_analysis_profiles": ["full"],
            "build_profiles": ["ci"],
            "test_profiles": ["full"],
            "coverage_profiles": ["ci"],
        }
    ).cpp

    assert cpp.enabled is True
    assert cpp.cmake_root == "native"
    assert cpp.static_analysis_command == ("./ci/static-analysis",)
    assert cpp.test_command == ("ctest", "--preset", "ci")
    assert cpp.coverage_profiles == ("ci",)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ([], "cpp: must be a table"),
        ({"enabled": "yes"}, "cpp.enabled: must be a boolean"),
        ({"build_command": "cmake --build ."}, "cpp.build_command: must be a list of strings"),
        ({"build_command": ["cmake", ""]}, "cpp.build_command"),
        ({"build_command": ["bash", "-c", "cmake --build ."]}, "cpp.build_command"),
        ({"build_command": ["cmd.exe", "/c", "cmake --build ."]}, "cpp.build_command"),
        (
            {"build_command": ["PowerShell.EXE", "-Command", "cmake --build ."]},
            "cpp.build_command",
        ),
        ({"build_command": ["cmake", "|", "tee", "log"]}, "cpp.build_command"),
        ({"build_profiles": ["full", "full"]}, "cpp.build_profiles"),
        ({"test_profiles": ["unknown"]}, "cpp.test_profiles"),
        ({"cmake_root": "/tmp/native"}, "cpp.cmake_root"),
        ({"cmake_root": "../native"}, "cpp.cmake_root"),
        ({"cmake_root": r"C:\native"}, "cpp.cmake_root"),
        ({"cmake_root": "C:/native"}, "cpp.cmake_root"),
        ({"cmake_root": "C:native"}, "cpp.cmake_root"),
    ],
)
def test_cpp_config_rejects_invalid_values(raw: object, message: str) -> None:
    with pytest.raises(ConfigValidationError, match=re.escape(message)):
        apply_cpp(raw)


def test_cpp_config_rejects_unknown_nested_keys() -> None:
    with pytest.raises(
        ConfigValidationError,
        match=r"tool\.agent_maintainer\.cpp\.unknown",
    ):
        apply_cpp({"unknown": True})


@pytest.mark.parametrize("cmake_root", [".", "native", "native/subdirectory"])
def test_cpp_config_accepts_repository_relative_cmake_roots(cmake_root: str) -> None:
    assert apply_cpp({"cmake_root": cmake_root}).cpp.cmake_root == cmake_root
