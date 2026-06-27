"""Tach architecture configuration validation helpers."""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path
from typing import Any, TypeGuard

DEFAULT_SOURCE_EXCLUDES = (
    ".git/",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
)
MISSING_MODULE_SAMPLE_LIMIT = 5


def tach_config_issues(repo_root: Path, *, require_strict_root: bool) -> list[str]:
    """Return Tach configuration problems before the Tach CLI runs."""
    config_path = repo_root / "tach.toml"
    if not config_path.exists():
        return ["tach.toml is absent"]

    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"tach.toml is invalid: {exc}"]

    issues = []
    issues.extend(_source_root_issues(payload))
    issues.extend(_module_issues(payload))
    issues.extend(_stale_module_reference_issues(repo_root, payload))
    issues.extend(_explicit_source_module_issues(repo_root, payload))
    if require_strict_root and payload.get("root_module") != "forbid":
        issues.append('tach.toml must set root_module = "forbid"')
    return issues


def _source_root_issues(payload: dict[str, Any]) -> list[str]:
    source_roots = payload.get("source_roots")
    if _non_empty_string_list(source_roots):
        return []
    return ["tach.toml must define source_roots"]


def _module_issues(payload: dict[str, Any]) -> list[str]:
    modules = payload.get("modules")
    if not isinstance(modules, list) or not modules:
        return ["tach.toml must define at least one module"]
    if not all(_module_has_path(item) for item in modules):
        return ["each tach module must define path or paths"]
    return []


def _explicit_source_module_issues(repo_root: Path, payload: dict[str, Any]) -> list[str]:
    source_roots = payload.get("source_roots")
    module_paths = _configured_module_paths(payload.get("modules"))
    if not _non_empty_string_list(source_roots) or not module_paths:
        return []

    missing_modules = tuple(
        module
        for module in _source_module_names(repo_root, source_roots, payload.get("exclude"))
        if module not in module_paths
    )
    if not missing_modules:
        return []

    return [
        f"tach.toml must explicitly assign source modules: {_format_module_sample(missing_modules)}"
    ]


def _stale_module_reference_issues(repo_root: Path, payload: dict[str, Any]) -> list[str]:
    source_roots = payload.get("source_roots")
    module_paths = _configured_module_paths(payload.get("modules"))
    if not _non_empty_string_list(source_roots) or not module_paths:
        return []

    stale_modules = tuple(
        module_path
        for module_path in sorted(module_paths)
        if not _module_path_exists(repo_root, source_roots, module_path)
    )
    if not stale_modules:
        return []

    return [
        f"tach.toml references modules without source files: {_format_module_sample(stale_modules)}"
    ]


def _module_path_exists(repo_root: Path, source_roots: list[str], module_path: str) -> bool:
    module_parts = module_path.split(".")
    for source_root in source_roots:
        source_root_path = repo_root / source_root
        module_file = source_root_path.joinpath(*module_parts).with_suffix(".py")
        module_package = source_root_path.joinpath(*module_parts)
        if module_file.is_file() or _module_package_exists(module_package):
            return True
    return False


def _module_package_exists(module_package: Path) -> bool:
    return module_package.is_dir() and any(module_package.rglob("*.py"))


def _format_module_sample(modules: tuple[str, ...]) -> str:
    sample = ", ".join(modules[:MISSING_MODULE_SAMPLE_LIMIT])
    if len(modules) <= MISSING_MODULE_SAMPLE_LIMIT:
        return sample
    remaining = len(modules) - MISSING_MODULE_SAMPLE_LIMIT
    return f"{sample}, ... ({remaining} more)"


def _configured_module_paths(modules: object) -> frozenset[str]:
    if not isinstance(modules, list):
        return frozenset()

    paths: list[str] = []
    for item in modules:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if _non_empty_string(path):
            paths.append(path)
        module_paths = item.get("paths")
        if _non_empty_string_list(module_paths):
            paths.extend(module_paths)
    return frozenset(paths)


def _source_module_names(
    repo_root: Path,
    source_roots: object,
    configured_excludes: object,
) -> tuple[str, ...]:
    if not _non_empty_string_list(source_roots):
        return ()

    excludes = _configured_excludes(configured_excludes)
    modules: set[str] = set()
    for source_root in source_roots:
        root_path = repo_root / source_root
        if not root_path.exists():
            continue
        for source_path in root_path.rglob("*.py"):
            relative_path = source_path.relative_to(repo_root)
            if _is_excluded(relative_path, excludes) or source_path.name == "__init__.py":
                continue
            module_name = _module_name(root_path, source_path)
            if module_name:
                modules.add(module_name)
    return tuple(sorted(modules))


def _configured_excludes(configured_excludes: object) -> tuple[str, ...]:
    excludes: list[str] = list(DEFAULT_SOURCE_EXCLUDES)
    if _non_empty_string_list(configured_excludes):
        excludes.extend(configured_excludes)
    return tuple(excludes)


def _is_excluded(relative_path: Path, excludes: tuple[str, ...]) -> bool:
    path_text = relative_path.as_posix()
    return any(_matches_exclude(path_text, relative_path.parts, item) for item in excludes)


def _matches_exclude(path_text: str, path_parts: tuple[str, ...], pattern: str) -> bool:
    normalized = pattern.strip().rstrip("/")
    if not normalized:
        return False
    if "/" not in normalized and normalized in path_parts:
        return True
    return (
        path_text == normalized
        or path_text.startswith(f"{normalized}/")
        or fnmatch.fnmatch(path_text, pattern)
        or fnmatch.fnmatch(path_text, f"{normalized}/**")
    )


def _module_name(source_root: Path, source_path: Path) -> str:
    return ".".join(source_path.relative_to(source_root).with_suffix("").parts)


def _module_has_path(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return _non_empty_string(item.get("path")) or _non_empty_string_list(item.get("paths"))


def _non_empty_string(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value)


def _non_empty_string_list(value: object) -> TypeGuard[list[str]]:
    return (
        isinstance(value, list) and bool(value) and all(_non_empty_string(item) for item in value)
    )
