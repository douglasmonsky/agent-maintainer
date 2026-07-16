"""Conservative Java/Gradle repository path classification."""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from agent_maintainer.config.java import JavaGradleConfig
from agent_maintainer.ecosystems.models import FileClassification, FileRole

ECOSYSTEM_NAME = "java"
BUILD_CONFIG_NAMES = frozenset(
    (
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradle.properties",
    )
)
DEPENDENCY_NAMES = frozenset(("gradlew", "gradlew.bat", "gradle.lockfile"))
IGNORED_PARTS = frozenset((".gradle", ".idea", "build", "out"))
CONFIG_PATH_PARTS = ("/config/checkstyle/", "/config/pmd/", "/config/spotbugs/")


def classify_path(path: str | PurePosixPath, config: JavaGradleConfig) -> FileClassification:
    """Classify one repository-relative path without guessing Java ownership."""

    normalized = str(path).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    pure = PurePosixPath(normalized)
    special = _special_role(pure)
    if special is None:
        role = _owned_role(normalized, pure, config)
        generated = False
        ignored = False
    else:
        role, generated, ignored = special
    return _result(normalized, role, generated=generated, ignored=ignored)


def _special_role(pure: PurePosixPath) -> tuple[FileRole, bool, bool] | None:
    parts = set(pure.parts)
    if "build" in parts and ("generated" in parts or pure.suffix == ".java"):
        return FileRole.GENERATED, True, True
    if parts & IGNORED_PARTS:
        return FileRole.IGNORED, False, True
    return None


def _owned_role(path: str, pure: PurePosixPath, config: JavaGradleConfig) -> FileRole:
    role = FileRole.UNKNOWN
    if _is_dependency_path(path, pure.name):
        role = FileRole.DEPENDENCY
    elif _is_config_path(path, pure.name):
        role = FileRole.CONFIG
    elif pure.suffix == ".java":
        role = _java_source_role(path, config)
    return role


def _java_source_role(path: str, config: JavaGradleConfig) -> FileRole:
    if _matches_roots(path, config.test_roots):
        return FileRole.TEST
    if _matches_roots(path, config.source_roots):
        return FileRole.SOURCE
    return FileRole.UNKNOWN


def _is_dependency_path(path: str, name: str) -> bool:
    return (
        name in DEPENDENCY_NAMES
        or "/gradle/wrapper/" in f"/{path}"
        or "/gradle/verification-metadata" in f"/{path}"
    )


def _is_config_path(path: str, name: str) -> bool:
    framed = f"/{path}"
    return (
        name in BUILD_CONFIG_NAMES
        or path.endswith("gradle/libs.versions.toml")
        or any(part in framed for part in CONFIG_PATH_PARTS)
    )


def _matches_roots(path: str, roots: tuple[str, ...]) -> bool:
    return any(_matches_root(path, root) for root in roots)


def _matches_root(path: str, root: str) -> bool:
    normalized = root.replace("\\", "/").strip("/")
    if normalized.startswith("**/"):
        suffix = normalized[3:]
        return path.startswith(f"{suffix}/") or f"/{suffix}/" in path
    return path.startswith(f"{normalized}/") or fnmatchcase(path, f"{normalized}/*")


def _result(
    path: str,
    role: FileRole,
    *,
    generated: bool = False,
    ignored: bool = False,
) -> FileClassification:
    return FileClassification(
        path=path,
        ecosystem=ECOSYSTEM_NAME,
        role=role,
        generated=generated,
        ignored=ignored,
        reason=f"java-gradle:{role.value}",
    )
