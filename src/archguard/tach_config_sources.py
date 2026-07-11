"""Source-module helpers for Tach configuration validation."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import TypeGuard

from archguard.structured_values import structured_array, structured_object, structured_objects

DEFAULT_SOURCE_EXCLUDES = (
    ".git/",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
)


def configured_module_paths(modules: object) -> frozenset[str]:
    """Return module paths declared in a Tach module list."""
    paths: list[str] = []
    for item in structured_objects(modules):
        path = item.get("path")
        if non_empty_string(path):
            paths.append(path)
        module_paths = item.get("paths")
        if non_empty_string_list(module_paths):
            paths.extend(module_paths)
    return frozenset(paths)


def source_module_names(
    repo_root: Path,
    source_roots: object,
    configured_excludes: object,
) -> tuple[str, ...]:
    """Return source modules under configured Tach roots."""
    if not non_empty_string_list(source_roots):
        return ()

    excludes = _configured_excludes(configured_excludes)
    modules: set[str] = set()
    for source_root in source_roots:
        modules.update(_root_module_names(repo_root, source_root, excludes))
    return tuple(sorted(modules))


def module_path_exists(repo_root: Path, source_roots: list[str], module_path: str) -> bool:
    """Return whether a configured Tach module resolves to source."""
    module_parts = module_path.split(".")
    for source_root in source_roots:
        source_root_path = repo_root / source_root
        module_file = source_root_path.joinpath(*module_parts).with_suffix(".py")
        module_package = source_root_path.joinpath(*module_parts)
        if module_file.is_file() or _module_package_exists(module_package):
            return True
    return False


def module_has_path(item: object) -> bool:
    """Return whether a Tach module item declares path ownership."""
    payload = structured_object(item)
    if payload is None:
        return False
    return non_empty_string(payload.get("path")) or non_empty_string_list(
        payload.get("paths"),
    )


def matches_exclude(path_text: str, path_parts: tuple[str, ...], pattern: str) -> bool:
    """Return whether a path matches a Tach exclude pattern."""
    normalized = pattern.strip().rstrip("/")
    if not normalized:
        return False
    return (
        normalized in path_parts
        or fnmatch.fnmatch(path_text, pattern)
        or fnmatch.fnmatch(path_text, f"{normalized}/**")
    )


def non_empty_string(value: object) -> TypeGuard[str]:
    """Return whether value is a non-empty string."""
    return isinstance(value, str) and bool(value)


def non_empty_string_list(value: object) -> TypeGuard[list[str]]:
    """Return whether value is a non-empty list of strings."""
    values = structured_array(value)
    return values is not None and bool(values) and all(non_empty_string(item) for item in values)


def _root_module_names(
    repo_root: Path,
    source_root: str,
    excludes: tuple[str, ...],
) -> set[str]:
    root_path = repo_root / source_root
    if not root_path.exists():
        return set()

    modules: set[str] = set()
    for source_path in root_path.rglob("*.py"):
        relative_path = source_path.relative_to(repo_root)
        if _is_excluded(relative_path, excludes) or source_path.name == "__init__.py":
            continue
        modules.add(_module_name(root_path, source_path))
    return modules


def _configured_excludes(configured_excludes: object) -> tuple[str, ...]:
    excludes: list[str] = list(DEFAULT_SOURCE_EXCLUDES)
    if non_empty_string_list(configured_excludes):
        excludes.extend(configured_excludes)
    return tuple(excludes)


def _is_excluded(relative_path: Path, excludes: tuple[str, ...]) -> bool:
    path_text = relative_path.as_posix()
    return any(matches_exclude(path_text, relative_path.parts, item) for item in excludes)


def _module_name(source_root: Path, source_path: Path) -> str:
    return ".".join(source_path.relative_to(source_root).with_suffix("").parts)


def _module_package_exists(module_package: Path) -> bool:
    return module_package.is_dir() and any(module_package.rglob("*.py"))
