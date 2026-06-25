"""Tach architecture configuration validation helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


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


def _module_has_path(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return _non_empty_string(item.get("path")) or _non_empty_string_list(item.get("paths"))


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _non_empty_string_list(value: object) -> bool:
    return (
        isinstance(value, list) and bool(value) and all(_non_empty_string(item) for item in value)
    )
