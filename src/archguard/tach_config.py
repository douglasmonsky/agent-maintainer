"""Tach architecture configuration validation helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from archguard import tach_config_domains as domains
from archguard import tach_config_sources as sources

MISSING_MODULE_SAMPLE_LIMIT = 5
MAX_MODULE_PATH_GROUP_SIZE = 8


def tach_config_issues(repo_root: Path, *, require_strict_root: bool) -> list[str]:
    """Return Tach configuration problems before Tach CLI runs."""
    config_path = repo_root / "tach.toml"
    if not config_path.exists():
        return ["tach.toml absent"]

    try:
        payload = _toml_table(tomllib.loads(config_path.read_text(encoding="utf-8")))
    except tomllib.TOMLDecodeError as exc:
        return [f"tach.toml invalid: {exc}"]
    if payload is None:
        return ["tach.toml must contain a top-level table"]

    issues: list[str] = []
    domain_load = domains.load_domain_payloads(repo_root, payload.get("source_roots"))
    domain_payloads = domain_load.payloads
    issues.extend(domain_load.errors)
    issues.extend(_source_root_issues(payload))
    issues.extend(_module_issues(payload, config_name="tach.toml"))
    issues.extend(_domain_payload_issues(domain_payloads))
    issues.extend(_stale_module_reference_issues(repo_root, payload, domain_payloads))
    issues.extend(_explicit_source_module_issues(repo_root, payload, domain_payloads))
    if require_strict_root and payload.get("root_module") != "forbid":
        issues.append('tach.toml must set root_module = "forbid"')
    return issues


def _source_root_issues(payload: domains.TachPayload) -> list[str]:
    if sources.non_empty_string_list(payload.get("source_roots")):
        return []
    return ["tach.toml must define source_roots"]


def _module_issues(payload: domains.TachPayload, *, config_name: str) -> list[str]:
    modules = payload.get("modules")
    if not isinstance(modules, list) or not modules:
        return [f"{config_name} must define at least one module"]
    module_values = cast(list[object], modules)
    if not all(sources.module_has_path(item) for item in module_values):
        return [f"each {config_name} module must define path or paths"]

    issues: list[str] = []
    issues.extend(_dependency_contract_issues(module_values, config_name=config_name))
    issues.extend(_large_path_group_issues(module_values, config_name=config_name))
    return issues


def _domain_payload_issues(domain_payloads: domains.DomainPayloads) -> list[str]:
    issues: list[str] = []
    for domain_root, payload in domain_payloads:
        issues.extend(_domain_module_issues(domain_root, payload))
    return issues


def _domain_module_issues(
    domain_root: str,
    payload: domains.TachPayload,
) -> list[str]:
    issues: list[str] = []
    root = _toml_table(payload.get("root"))
    if root is not None and "depends_on" not in root:
        issues.append(f"{domains.DOMAIN_CONFIG_NAME} root depends_on missing: {domain_root}")

    modules = payload.get("modules")
    if modules is None:
        return issues
    if not isinstance(modules, list):
        issues.append(f"{domains.DOMAIN_CONFIG_NAME} modules must be a list: {domain_root}")
        return issues

    module_values = cast(list[object], modules)
    issues.extend(
        _dependency_contract_issues(module_values, config_name=domains.DOMAIN_CONFIG_NAME)
    )
    issues.extend(_large_path_group_issues(module_values, config_name=domains.DOMAIN_CONFIG_NAME))
    return issues


def _dependency_contract_issues(modules: list[object], *, config_name: str) -> list[str]:
    missing = tuple(_module_label(item) for item in modules if _missing_depends_on(item))
    if not missing:
        return []
    return [f"each {config_name} module must define depends_on: {_module_sample(missing)}"]


def _large_path_group_issues(modules: list[object], *, config_name: str) -> list[str]:
    large_groups = tuple(_large_path_group_labels(modules))
    if not large_groups:
        return []
    return [
        f"{config_name} module path groups must be "
        f"<= {MAX_MODULE_PATH_GROUP_SIZE} paths: {_module_sample(large_groups)}"
    ]


def _large_path_group_labels(modules: list[object]) -> tuple[str, ...]:
    labels: list[str] = []
    for item in modules:
        module = _toml_table(item)
        if module is None:
            continue
        paths = module.get("paths")
        if sources.non_empty_string_list(paths) and len(paths) > MAX_MODULE_PATH_GROUP_SIZE:
            labels.append(_module_label(module))
    return tuple(labels)


def _missing_depends_on(item: object) -> bool:
    module = _toml_table(item)
    return module is None or "depends_on" not in module


def _module_label(item: object) -> str:
    module = _toml_table(item)
    if module is None:
        return "<invalid>"

    path = module.get("path")
    if sources.non_empty_string(path):
        return path

    paths = module.get("paths")
    if sources.non_empty_string_list(paths):
        return paths[0]
    return "<unknown>"


def _explicit_source_module_issues(
    repo_root: Path,
    payload: domains.TachPayload,
    domain_payloads: domains.DomainPayloads,
) -> list[str]:
    modules = sources.source_module_names(
        repo_root,
        payload.get("source_roots"),
        payload.get("exclude"),
    )
    configured = sources.configured_module_paths(payload.get("modules"))
    configured |= domains.configured_domain_module_paths(domain_payloads)
    domain_roots = domains.configured_domain_roots(domain_payloads)
    missing = tuple(
        module
        for module in modules
        if module not in configured and not domains.module_is_owned_by_domain(module, domain_roots)
    )
    if not missing:
        return []
    return [f"tach.toml must explicitly list source modules: {_module_sample(missing)}"]


def _stale_module_reference_issues(
    repo_root: Path,
    payload: domains.TachPayload,
    domain_payloads: domains.DomainPayloads,
) -> list[str]:
    source_roots = payload.get("source_roots")
    if not sources.non_empty_string_list(source_roots):
        return []

    configured_modules = sources.configured_module_paths(
        payload.get("modules")
    ) | domains.configured_domain_module_paths(domain_payloads)
    stale_modules = tuple(
        module_path
        for module_path in sorted(configured_modules)
        if not sources.module_path_exists(repo_root, source_roots, module_path)
    )
    if not stale_modules:
        return []
    return [f"tach.toml references modules without source files: {_module_sample(stale_modules)}"]


def _module_sample(modules: tuple[str, ...]) -> str:
    sample = ", ".join(modules[:MISSING_MODULE_SAMPLE_LIMIT])
    if len(modules) <= MISSING_MODULE_SAMPLE_LIMIT:
        return sample
    remaining = len(modules) - MISSING_MODULE_SAMPLE_LIMIT
    return f"{sample}, ... ({remaining} more)"


def _toml_table(value: object) -> domains.TachPayload | None:
    """Return a string-keyed TOML table with an explicit value boundary."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}
