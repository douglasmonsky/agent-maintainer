"""Domain-file helpers for Tach configuration validation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from archguard import tach_config_sources as sources

DOMAIN_CONFIG_NAME = "tach.domain.toml"
TachPayload = dict[str, Any]
DomainPayload = tuple[str, TachPayload]
DomainPayloads = tuple[DomainPayload, ...]


def domain_payloads(repo_root: Path, source_roots: object) -> DomainPayloads:
    """Return parsed Tach domain files under configured source roots."""
    if not sources.non_empty_string_list(source_roots):
        return ()

    payloads: list[DomainPayload] = []
    for source_root in source_roots:
        root_path = repo_root / source_root
        if not root_path.exists():
            continue
        payloads.extend(_root_domain_payloads(root_path))
    return tuple(payloads)


def configured_domain_module_paths(payloads: DomainPayloads) -> frozenset[str]:
    """Return full module paths configured in Tach domain files."""
    paths: set[str] = set()
    for domain_root, payload in payloads:
        paths.update(_payload_module_paths(domain_root, payload))
    return frozenset(paths)


def configured_domain_roots(payloads: DomainPayloads) -> frozenset[str]:
    """Return domain roots that explicitly declare package ownership."""
    return frozenset(
        domain_root for domain_root, payload in payloads if isinstance(payload.get("root"), dict)
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


def _root_domain_payloads(root_path: Path) -> tuple[DomainPayload, ...]:
    payloads: list[DomainPayload] = []
    for config_path in sorted(root_path.rglob(DOMAIN_CONFIG_NAME)):
        payload = _read_domain_payload(config_path)
        domain_root = ".".join(config_path.parent.relative_to(root_path).parts)
        if payload is not None and domain_root:
            payloads.append((domain_root, payload))
    return tuple(payloads)


def _read_domain_payload(config_path: Path) -> TachPayload | None:
    try:
        return tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None


def _payload_module_paths(domain_root: str, payload: TachPayload) -> tuple[str, ...]:
    paths: list[str] = []
    if isinstance(payload.get("root"), dict):
        paths.append(domain_root)

    modules = payload.get("modules")
    if isinstance(modules, list):
        for item in modules:
            paths.extend(_domain_item_module_paths(domain_root, item))
    return tuple(paths)


def _domain_item_module_paths(domain_root: str, item: object) -> tuple[str, ...]:
    if not isinstance(item, dict):
        return ()

    path = item.get("path")
    if sources.non_empty_string(path):
        return (domain_module_path(domain_root, path),)

    module_paths = item.get("paths")
    if sources.non_empty_string_list(module_paths):
        return tuple(domain_module_path(domain_root, path) for path in module_paths)
    return ()
