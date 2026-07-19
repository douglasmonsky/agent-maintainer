"""Tests conservative C/C++ and CMake path classification."""

from __future__ import annotations

import pytest

from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.ecosystems.cpp.classification import classify_path
from agent_maintainer.ecosystems.models import FileRole


@pytest.mark.parametrize(
    ("path", "role", "generated", "ignored"),
    [
        ("src/main.c", FileRole.SOURCE, False, False),
        ("src/main.cpp", FileRole.SOURCE, False, False),
        ("include/api.hpp", FileRole.HEADER, False, False),
        ("tests/api_test.cc", FileRole.TEST, False, False),
        ("CMakeLists.txt", FileRole.CONFIG, False, False),
        ("cmake/toolchain.cmake", FileRole.CONFIG, False, False),
        ("CMakePresets.json", FileRole.CONFIG, False, False),
        (".clang-tidy", FileRole.CONFIG, False, False),
        ("vcpkg.json", FileRole.DEPENDENCY, False, False),
        ("conan.lock", FileRole.DEPENDENCY, False, False),
        ("build/generated/config.hpp", FileRole.GENERATED, True, True),
        ("third_party/lib/vendor.cc", FileRole.IGNORED, False, True),
        ("README.md", FileRole.DOCS, False, False),
        ("notes/data.json", None, False, False),
    ],
)
def test_cpp_path_roles(
    path: str,
    role: FileRole | None,
    generated: bool,
    ignored: bool,
) -> None:
    """C/C++ paths follow the provider's conservative precedence table."""
    result = classify_path(path, CppCmakeConfig(enabled=True))
    if role is None:
        assert result is None
        return
    assert result is not None
    assert result.role is role
    assert result.generated is generated
    assert result.ignored is ignored
