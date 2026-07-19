"""Conservative C/C++ and CMake repository path classification."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from agent_maintainer.config.cpp import CppCmakeConfig
from agent_maintainer.ecosystems.models import FileClassification, FileRole

ECOSYSTEM_NAME = "cpp"
C_SOURCE_EXTENSIONS = frozenset((".c",))
CPP_SOURCE_EXTENSIONS = frozenset((".c++", ".cc", ".cpp", ".cxx"))
HEADER_EXTENSIONS = frozenset((".h", ".hh", ".hpp", ".hxx", ".inl"))
TEST_PARTS = frozenset(("spec", "specs", "test", "tests"))
TEST_MARKERS = ("_test.", "_tests.", ".test.", ".spec.")
BUILD_IGNORED_PARTS = frozenset(
    (
        ".cache",
        "CMakeFiles",
        "_deps",
        "build",
        "cmake-build-debug",
        "cmake-build-release",
        "out",
    ),
)
VENDOR_PARTS = frozenset(("third_party", "vendor"))
ALWAYS_IGNORED_PARTS = frozenset((".git", ".idea", ".vscode"))
GENERATED_PARTS = frozenset(("generated", "gen"))
CMAKE_NAMES = frozenset(
    ("CMakeLists.txt", "CMakePresets.json", "CMakeUserPresets.json"),
)
TOOL_CONFIG_NAMES = frozenset(
    (
        ".clang-format",
        ".clang-tidy",
        ".cppcheck",
        ".cppcheck-suppressions",
        "cppcheck-suppressions.txt",
    ),
)
DEPENDENCY_NAMES = frozenset(
    (
        "conan.lock",
        "conanfile.py",
        "conanfile.txt",
        "vcpkg-configuration.json",
        "vcpkg.json",
    ),
)
DOC_EXTENSIONS = frozenset((".md", ".rst", ".txt"))
SOURCE_EXTENSIONS = C_SOURCE_EXTENSIONS | CPP_SOURCE_EXTENSIONS
OWNED_EXTENSIONS = SOURCE_EXTENSIONS | HEADER_EXTENSIONS


def classify_path(
    path: str | Path,
    _config: CppCmakeConfig,
) -> FileClassification | None:
    """Classify one repository-relative C/C++ or CMake path."""
    normalized = str(path).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    pure = PurePosixPath(normalized)
    parts = frozenset(pure.parts)

    special = _special_role(pure, parts)
    if special is not None:
        role, generated, ignored = special
        return _result(normalized, role, generated=generated, ignored=ignored)
    role = _owned_role(pure, parts)
    if role is None:
        return None
    return _result(normalized, role)


def _special_role(
    pure: PurePosixPath,
    parts: frozenset[str],
) -> tuple[FileRole, bool, bool] | None:
    """Return roles that take precedence over source and header ownership."""
    if pure.suffix in OWNED_EXTENSIONS and (parts & BUILD_IGNORED_PARTS or parts & GENERATED_PARTS):
        return FileRole.GENERATED, True, True
    if parts & (BUILD_IGNORED_PARTS | VENDOR_PARTS | ALWAYS_IGNORED_PARTS):
        return FileRole.IGNORED, False, True
    role = _metadata_role(pure)
    if role is None:
        return None
    return role, False, False


def _metadata_role(pure: PurePosixPath) -> FileRole | None:
    """Return roles for C/C++ repository metadata and documentation."""
    if pure.name in DEPENDENCY_NAMES:
        return FileRole.DEPENDENCY
    if pure.name in CMAKE_NAMES or pure.name in TOOL_CONFIG_NAMES or pure.suffix == ".cmake":
        return FileRole.CONFIG
    if pure.suffix in DOC_EXTENSIONS:
        return FileRole.DOCS
    return None


def _owned_role(
    pure: PurePosixPath,
    parts: frozenset[str],
) -> FileRole | None:
    """Return the role for a recognized C/C++ source or header path."""
    if pure.suffix not in OWNED_EXTENSIONS:
        return None
    if parts & TEST_PARTS or any(marker in pure.name for marker in TEST_MARKERS):
        return FileRole.TEST
    if pure.suffix in HEADER_EXTENSIONS:
        return FileRole.HEADER
    return FileRole.SOURCE


def _result(
    path: str,
    role: FileRole,
    *,
    generated: bool = False,
    ignored: bool = False,
) -> FileClassification:
    """Build one C/C++ classification result."""
    return FileClassification(
        path=path,
        ecosystem=ECOSYSTEM_NAME,
        role=role,
        generated=generated,
        ignored=ignored,
        reason=f"cpp-cmake:{role.value}",
    )
