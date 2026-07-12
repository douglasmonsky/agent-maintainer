"""Read-only architecture impact analysis from Tach configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from archguard import tach_config_domains as domains
from archguard.structured_values import non_empty_strings, structured_object, structured_objects

NO_OWNER = "<unassigned>"
MAX_AFFECTED_TESTS = 12


@dataclass(frozen=True)
class ModuleRule:
    """Configured Tach module ownership and dependency rule."""

    name: str
    layer: str = NO_OWNER
    depends_on: tuple[str, ...] | None = None
    domain_root: str = ""


@dataclass(frozen=True)
class ArchitectureMap:
    """Parsed Tach architecture map."""

    source_roots: tuple[str, ...]
    layers: tuple[str, ...]
    modules: tuple[ModuleRule, ...]
    load_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class OwnedModule:
    """Resolved module ownership for a file path."""

    file_path: Path
    module_name: str
    owner: ModuleRule | None

    @property
    def owner_name(self) -> str:
        """Return display ownership name."""

        return self.owner.name if self.owner else NO_OWNER

    @property
    def layer(self) -> str:
        """Return display layer name."""

        return self.owner.layer if self.owner else NO_OWNER


def load_architecture(repo_root: Path) -> ArchitectureMap:
    """Load Tach architecture map from repository root."""

    config_path = repo_root / "tach.toml"
    try:
        payload = structured_object(tomllib.loads(config_path.read_text(encoding="utf-8"))) or {}
    except tomllib.TOMLDecodeError:
        return ArchitectureMap((), (), (), ("tach.toml: invalid_toml",))
    except UnicodeError:
        return ArchitectureMap((), (), (), ("tach.toml: invalid_utf8",))
    except OSError:
        return ArchitectureMap((), (), (), ("tach.toml: read_error",))
    domain_load = domains.load_domain_payloads(repo_root, payload.get("source_roots"))
    return ArchitectureMap(
        source_roots=non_empty_strings(payload.get("source_roots")),
        layers=non_empty_strings(payload.get("layers")),
        modules=_all_module_rules(payload.get("modules"), domain_load.payloads),
        load_errors=domain_load.errors,
    )


def _all_module_rules(
    root_modules: object,
    domain_payloads: domains.DomainPayloads,
) -> tuple[ModuleRule, ...]:
    """Return root and nested domain rules sorted by full module name."""

    rules = list(module_rules(root_modules))
    rules.extend(
        ModuleRule(rule.name, depends_on=rule.depends_on, domain_root=rule.domain_root)
        for rule in domains.domain_module_rules(domain_payloads)
    )
    return tuple(sorted(rules, key=lambda rule: rule.name))


def module_rules(modules: object) -> tuple[ModuleRule, ...]:
    """Return flattened module ownership rules."""

    rules: list[ModuleRule] = []
    for item in structured_objects(modules):
        layer = string_value(item.get("layer"))
        paths = module_paths(item)
        rules.extend(ModuleRule(name=path, layer=layer) for path in paths)
    return tuple(sorted(rules, key=lambda rule: rule.name))


def module_paths(item: dict[str, object]) -> tuple[str, ...]:
    """Return module paths from one Tach module item."""

    path = item.get("path")
    paths = item.get("paths")
    if isinstance(path, str) and path:
        return (path,)
    return non_empty_strings(paths)


def string_value(value: object) -> str:
    """Return string value or unassigned marker."""

    return value if isinstance(value, str) and value else NO_OWNER


def render_map(architecture: ArchitectureMap) -> str:
    """Render module ownership map."""

    source_roots = ", ".join(architecture.source_roots)
    layer_names = ", ".join(architecture.layers)
    lines = [
        "# Architecture Map",
        f"Source roots: {source_roots}",
        f"Layers: {layer_names}",
        "",
        "Modules:",
    ]
    for rule in architecture.modules:
        lines.append(_render_rule(rule))
    if architecture.load_errors:
        lines.extend(("", "Policy load errors:"))
        lines.extend(f"- {error}" for error in architecture.load_errors)
    return join_lines(lines)


def _render_rule(rule: ModuleRule) -> str:
    """Render one ownership rule without changing legacy map lines."""

    line = f"- {rule.name} [{rule.layer}]"
    if rule.depends_on is None:
        return line
    dependencies = ", ".join(rule.depends_on) or "<none>"
    return f"{line} depends on: {dependencies}"


def render_impact(repo_root: Path, architecture: ArchitectureMap, file_path: Path) -> str:
    """Render architecture impact for a changed file."""

    owned = resolve_file(repo_root, architecture, file_path)
    lines = [
        "# Architecture Impact",
        f"File: {file_path.as_posix()}",
        f"Module ownership: {owned.owner_name}",
        f"Dependency direction: {dependency_direction(architecture, owned.owner)}",
        f"Changed modules: {owned.owner_name}",
        f"Affected tests: {affected_tests(repo_root, owned)}",
        "Boundary violations: run `tach check --exact`.",
        "Decision notes: update `docs/architecture/decisions/` when policy changes.",
    ]
    return join_lines(lines)


def render_boundary(
    repo_root: Path,
    architecture: ArchitectureMap,
    source_path: Path,
    target_path: Path,
) -> str:
    """Render architecture boundary explanation for two files."""

    source = resolve_file(repo_root, architecture, source_path)
    target = resolve_file(repo_root, architecture, target_path)
    lines = [
        "# Architecture Boundary",
        f"Source file: {source_path.as_posix()}",
        f"Source module ownership: {source.owner_name}",
        f"Source layer: {source.layer}",
        f"Target file: {target_path.as_posix()}",
        f"Target module ownership: {target.owner_name}",
        f"Target layer: {target.layer}",
        f"Dependency direction: {boundary_status(architecture, source.owner, target.owner)}",
        "Boundary violations: run `tach check --exact`.",
        "Decision notes: update `docs/architecture/decisions/` when policy changes.",
    ]
    return join_lines(lines)


def resolve_file(
    repo_root: Path,
    architecture: ArchitectureMap,
    file_path: Path,
) -> OwnedModule:
    """Resolve source file to Tach module ownership."""

    absolute_path = (repo_root / file_path).resolve()
    module_name = module_name_for_path(repo_root, architecture, absolute_path)
    return OwnedModule(
        file_path=file_path,
        module_name=module_name,
        owner=owner_for_module(architecture, module_name),
    )


def module_name_for_path(
    repo_root: Path,
    architecture: ArchitectureMap,
    absolute_path: Path,
) -> str:
    """Return Python module name for a file under Tach source roots."""

    for source_root in architecture.source_roots:
        root_path = (repo_root / source_root).resolve()
        if not absolute_path.is_relative_to(root_path):
            continue
        relative_path = absolute_path.relative_to(root_path)
        if relative_path.suffix != ".py":
            return NO_OWNER
        parts = relative_path.with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else NO_OWNER
    return NO_OWNER


def owner_for_module(
    architecture: ArchitectureMap,
    module_name: str,
) -> ModuleRule | None:
    """Return nearest configured Tach owner for module name."""

    candidates = [
        rule
        for rule in architecture.modules
        if module_name == rule.name or module_name.startswith(f"{rule.name}.")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda rule: len(rule.name))


def dependency_direction(
    architecture: ArchitectureMap,
    owner: ModuleRule | None,
) -> str:
    """Return allowed dependency direction for an owner."""

    if architecture.load_errors:
        return "unknown: architecture policy is incomplete"
    if owner is not None and owner.depends_on is not None:
        if not owner.depends_on:
            return f"{owner.name} may not depend on other configured modules"
        dependencies = ", ".join(owner.depends_on)
        return f"{owner.name} may depend on {dependencies}"
    if owner is None or owner.layer not in architecture.layers:
        return "unknown"
    layer_index = architecture.layers.index(owner.layer)
    allowed_targets = architecture.layers[layer_index:]
    allowed_sources = architecture.layers[: layer_index + 1]
    target_text = ", ".join(allowed_targets)
    source_text = ", ".join(allowed_sources)
    return f"{owner.layer} may depend on {target_text}; may be used by {source_text}"


def boundary_status(
    architecture: ArchitectureMap,
    source: ModuleRule | None,
    target: ModuleRule | None,
) -> str:
    """Return boundary status if source imports target."""

    if architecture.load_errors or source is None or target is None:
        return (
            "unknown: architecture policy is incomplete"
            if architecture.load_errors
            else "unknown; at least one file is not owned by Tach"
        )
    if source.name == target.name:
        return "same module"
    if source.depends_on is not None:
        return _explicit_boundary_status(source, target)
    if source.layer not in architecture.layers or target.layer not in architecture.layers:
        return "unknown; at least one layer is not configured"
    source_index = architecture.layers.index(source.layer)
    target_index = architecture.layers.index(target.layer)
    return (
        f"allowed: {source.layer} can depend on {target.layer}"
        if source_index <= target_index
        else f"violation: {source.layer} must not depend on {target.layer}"
    )


def _explicit_boundary_status(source: ModuleRule, target: ModuleRule) -> str:
    """Return explicit dependency allowlist status for two owned modules."""

    allowed = any(
        target.name == dependency or target.name.startswith(f"{dependency}.")
        for dependency in source.depends_on or ()
    )
    if allowed:
        return f"allowed: {source.name} declares {target.name}"
    return f"violation: {source.name} does not declare {target.name}"


def affected_tests(repo_root: Path, owned: OwnedModule) -> str:
    """Return compact affected test candidates for owned module."""

    tests_root = repo_root / "tests"
    if not tests_root.exists() or owned.owner is None:
        return "none found"
    leaf = owned.owner.name.rsplit(".", maxsplit=1)[-1].replace("_", "-")
    domain_segment = owned.owner.domain_root.rsplit(".", maxsplit=1)[-1]
    candidates = sorted(
        path.relative_to(repo_root).as_posix()
        for path in tests_root.rglob("test_*.py")
        if leaf.replace("-", "_") in path.stem
        or domain_segment in path.relative_to(tests_root).parts
    )
    if not candidates:
        return "none found"
    displayed = candidates[:MAX_AFFECTED_TESTS]
    omitted = len(candidates) - len(displayed)
    hint_text = ", ".join(displayed)
    return f"{hint_text} (+{omitted} more)" if omitted else hint_text


def join_lines(lines: list[str]) -> str:
    """Return newline-terminated text."""

    return "\n".join((*lines, ""))
