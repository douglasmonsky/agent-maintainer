"""Domain-file helpers for Tach configuration validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from archguard import tach_config_sources as sources

DOMAIN_CONFIG_NAME = "tach.domain.toml"
TachPayload = dict[str, object]
DomainPayload = tuple[str, TachPayload]
DomainPayloads = tuple[DomainPayload, ...]


@dataclass(frozen=True)
class DomainLoadResult:
    """Parsed domain payloads plus bounded fail-closed errors."""

    payloads: DomainPayloads
    errors: tuple[str, ...]


@dataclass(frozen=True)
class DomainModuleRule:
    """One normalized nested-domain ownership and dependency rule."""

    name: str
    depends_on: tuple[str, ...] | None
    domain_root: str


def load_domain_payloads(repo_root: Path, source_roots: object) -> DomainLoadResult:
    """Return parsed Tach domain files and bounded loader errors."""
    if not sources.non_empty_string_list(source_roots):
        return DomainLoadResult((), ())

    payloads: list[DomainPayload] = []
    errors: list[str] = []
    for source_root in source_roots:
        root_path = repo_root / source_root
        if not root_path.exists():
            continue
        result = _root_domain_payloads(repo_root, root_path)
        payloads.extend(result.payloads)
        errors.extend(result.errors)
    return DomainLoadResult(tuple(sorted(payloads)), tuple(sorted(errors)))


def configured_domain_module_paths(payloads: DomainPayloads) -> frozenset[str]:
    """Return full module paths configured in Tach domain files."""
    paths: set[str] = set()
    for domain_root, payload in payloads:
        paths.update(_payload_module_paths(domain_root, payload))
    return frozenset(paths)


def domain_module_rules(payloads: DomainPayloads) -> tuple[DomainModuleRule, ...]:
    """Return normalized ownership and dependency rules for nested domains."""

    rules: list[DomainModuleRule] = []
    for domain_root, payload in payloads:
        rules.extend(_payload_module_rules(domain_root, payload))
    return tuple(sorted(rules, key=lambda rule: rule.name))


def _payload_module_rules(domain_root: str, payload: TachPayload) -> tuple[DomainModuleRule, ...]:
    """Return normalized rules declared by one domain payload."""

    rules: list[DomainModuleRule] = []
    root = _toml_table(payload.get("root"))
    if root is not None:
        rules.append(_domain_rule(domain_root, domain_root, root))
    for item in _object_list(payload.get("modules")):
        module = _toml_table(item)
        if module is None:
            continue
        rules.extend(_domain_rule(domain_root, path, module) for path in _module_paths(module))
    return tuple(rules)


def _domain_rule(
    domain_root: str,
    path: str,
    payload: TachPayload,
) -> DomainModuleRule:
    """Return one normalized domain rule from a config table."""

    name = domain_root if path == domain_root else domain_module_path(domain_root, path)
    return DomainModuleRule(name, _dependency_paths(payload, domain_root), domain_root)


def _dependency_paths(payload: TachPayload, domain_root: str) -> tuple[str, ...] | None:
    """Return an explicit normalized dependency allowlist when present."""

    if "depends_on" not in payload:
        return None
    values = _object_list(payload.get("depends_on"))
    return tuple(
        _dependency_path(value, domain_root) for value in values if sources.non_empty_string(value)
    )


def _dependency_path(value: str, domain_root: str) -> str:
    """Return one absolute or domain-local dependency module path."""

    return value[2:] if value.startswith("//") else domain_module_path(domain_root, value)


def _object_list(value: object) -> tuple[object, ...]:
    """Return a list value with an explicit object boundary."""

    if not isinstance(value, list):
        return ()
    return tuple(cast(list[object], value))


def _module_paths(payload: TachPayload) -> tuple[str, ...]:
    """Return configured local paths from one module payload."""

    path = payload.get("path")
    if sources.non_empty_string(path):
        return (path,)
    return tuple(
        value for value in _object_list(payload.get("paths")) if sources.non_empty_string(value)
    )


def configured_domain_roots(payloads: DomainPayloads) -> frozenset[str]:
    """Return domain roots that explicitly declare package ownership."""
    return frozenset(
        domain_root
        for domain_root, payload in payloads
        if _toml_table(payload.get("root")) is not None
    )


def module_is_owned_by_domain(module_path: str, domain_roots: frozenset[str]) -> bool:
    """Return whether a configured domain root owns a source-module descendant."""
    return any(
        module_path == domain_root or module_path.startswith(f"{domain_root}.")
        for domain_root in domain_roots
    )


def domain_module_path(domain_root: str, path: str) -> str:
    """Return full module path for a domain-local module path."""
    if path in {"", ".", "<root>"}:
        return domain_root
    return f"{domain_root}.{path}"


def _root_domain_payloads(repo_root: Path, root_path: Path) -> DomainLoadResult:
    payloads: list[DomainPayload] = []
    errors: list[str] = []
    for config_path in sorted(root_path.rglob(DOMAIN_CONFIG_NAME)):
        payload, error = _read_domain_payload(config_path)
        domain_root = ".".join(config_path.parent.relative_to(root_path).parts)
        if payload is not None and domain_root:
            payloads.append((domain_root, payload))
        if error is not None:
            path = config_path.relative_to(repo_root).as_posix()
            errors.append(f"{path}: {error}")
    return DomainLoadResult(tuple(payloads), tuple(errors))


def _read_domain_payload(config_path: Path) -> tuple[TachPayload | None, str | None]:
    try:
        return _toml_table(tomllib.loads(config_path.read_text(encoding="utf-8"))), None
    except tomllib.TOMLDecodeError:
        return None, "invalid_toml"
    except UnicodeError:
        return None, "invalid_utf8"
    except OSError:
        return None, "read_error"


def _payload_module_paths(domain_root: str, payload: TachPayload) -> tuple[str, ...]:
    paths: list[str] = []
    if _toml_table(payload.get("root")) is not None:
        paths.append(domain_root)

    modules = payload.get("modules")
    if isinstance(modules, list):
        for item in cast(list[object], modules):
            paths.extend(_domain_item_module_paths(domain_root, item))
    return tuple(paths)


def _domain_item_module_paths(domain_root: str, item: object) -> tuple[str, ...]:
    module = _toml_table(item)
    if module is None:
        return ()

    path = module.get("path")
    if sources.non_empty_string(path):
        return (domain_module_path(domain_root, path),)

    module_paths = module.get("paths")
    if sources.non_empty_string_list(module_paths):
        return tuple(domain_module_path(domain_root, path) for path in module_paths)
    return ()


def _toml_table(value: object) -> TachPayload | None:
    """Return a string-keyed TOML table with an explicit value boundary."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}
