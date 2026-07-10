"""Load DocSync repository configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from docsync.config.errors import ConfigError, PathBoundaryError
from docsync.config.io import read_bounded_text
from docsync.config.resolution import ResolvedConfigPaths, resolve_config_path, resolve_config_paths
from docsync.core.models import DocSyncConfig


@dataclass(frozen=True)
class ConfigSections:
    """Typed mappings consumed from one DocSync configuration payload."""

    outputs: dict[str, Any]
    attestations: dict[str, Any]
    markdown: dict[str, Any]
    source_evidence: dict[str, Any]


def load_config(repo_root: Path, config_path: Path | None = None) -> DocSyncConfig:
    """Load and resolve DocSync configuration paths."""

    resolved_root = repo_root.resolve()
    candidate = config_path or Path(".docsync/config.yml")
    resolved_config = resolve_config_path(resolved_root, candidate)
    sections = _config_sections(load_yaml_mapping(resolved_config))
    paths = resolve_config_paths(
        resolved_root,
        resolved_config,
        sections.outputs,
        sections.attestations,
    )
    return _build_config(resolved_root, sections, paths)


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML file and require a mapping payload."""

    try:
        text = read_bounded_text(path, label="DocSync YAML input")
    except PathBoundaryError as exc:
        raise ConfigError(str(exc)) from exc
    return parse_yaml_mapping(text, path=path)


def parse_yaml_mapping(text: str, *, path: Path) -> dict[str, Any]:
    """Parse one already-bounded YAML mapping without reopening its source."""

    try:
        payload = _yaml_module().safe_load(text)
    except (yaml.YAMLError, RecursionError) as exc:
        raise ConfigError(f"Cannot parse DocSync YAML file: {path}") from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ConfigError(f"YAML file must contain mapping: {path}")
    return cast(dict[str, Any], payload)


def _config_sections(payload: dict[str, Any]) -> ConfigSections:
    return ConfigSections(
        outputs=_mapping_value(payload, "outputs"),
        attestations=_mapping_value(payload, "attestations"),
        markdown=_mapping_value(payload, "markdown"),
        source_evidence=_mapping_value(payload, "source_evidence"),
    )


def _mapping_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"DocSync config '{key}' must be a mapping")
    return cast(dict[str, Any], value)


def _bool_value(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"DocSync config '{key}' must be boolean")
    return value


def _build_config(
    repo_root: Path,
    sections: ConfigSections,
    paths: ResolvedConfigPaths,
) -> DocSyncConfig:
    object_marker = str(sections.markdown.get("object_marker", "docsync:object"))
    return DocSyncConfig(
        repo_root=repo_root,
        config_path=paths.config,
        trace_path=paths.trace,
        attestations_dir=paths.attestations,
        output_dir=paths.outputs.directory,
        index_json=paths.outputs.index_json,
        report_json=paths.outputs.report_json,
        review_packet_json=paths.outputs.review_packet_json,
        review_prompt_md=paths.outputs.review_prompt_md,
        object_marker=object_marker,
        object_end_marker=str(sections.markdown.get("object_end_marker", f"{object_marker}.end")),
        require_object_end_markers=_bool_value(
            sections.markdown,
            "require_object_end_markers",
            default=False,
        ),
        evidence_start_directive=str(
            sections.source_evidence.get("start_directive", "docsync:evidence.start")
        ),
        evidence_end_directive=str(
            sections.source_evidence.get("end_directive", "docsync:evidence.end")
        ),
    )


def _yaml_module() -> Any:
    return yaml
