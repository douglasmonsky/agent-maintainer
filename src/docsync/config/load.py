"""Load DocSync repository configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from docsync.core.models import DocSyncConfig


class ConfigError(ValueError):
    """Raised when DocSync configuration cannot be loaded."""


def load_config(repo_root: Path, config_path: Path | None = None) -> DocSyncConfig:
    """Load and resolve DocSync configuration paths."""
    resolved_root = repo_root.resolve()
    resolved_config = _resolve_path(
        resolved_root,
        config_path or Path(".docsync/config.yml"),
    )
    if not resolved_config.exists():
        raise ConfigError(f"DocSync config not found: {resolved_config}")

    payload = load_yaml_mapping(resolved_config)
    outputs = _mapping_value(payload, "outputs")
    attestations = _mapping_value(payload, "attestations")
    markdown = _mapping_value(payload, "markdown")
    source_evidence = _mapping_value(payload, "source_evidence")
    return DocSyncConfig(
        repo_root=resolved_root,
        config_path=resolved_config,
        trace_path=resolved_root / ".docsync" / "trace.yml",
        attestations_dir=_resolve_path(
            resolved_root,
            Path(str(attestations.get("directory", ".docsync/attestations"))),
        ),
        index_json=_resolve_path(
            resolved_root,
            Path(str(outputs.get("index_json", ".docsync/out/index.json"))),
        ),
        report_json=_resolve_path(
            resolved_root,
            Path(str(outputs.get("report_json", ".docsync/out/report.json"))),
        ),
        review_packet_json=_resolve_path(
            resolved_root,
            Path(str(outputs.get("review_packet_json", ".docsync/out/review-packet.json"))),
        ),
        review_prompt_md=_resolve_path(
            resolved_root,
            Path(str(outputs.get("review_prompt_md", ".docsync/out/review-prompt.md"))),
        ),
        object_marker=str(markdown.get("object_marker", "docsync:object")),
        evidence_start_directive=str(
            source_evidence.get("start_directive", "docsync:evidence.start")
        ),
        evidence_end_directive=str(source_evidence.get("end_directive", "docsync:evidence.end")),
    )


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML file and require a mapping payload."""
    yaml_module = _yaml_module()
    payload = yaml_module.safe_load(path.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ConfigError(f"YAML file must contain mapping: {path}")
    return cast(dict[str, Any], payload)


def _mapping_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"DocSync config '{key}' must be a mapping")
    return cast(dict[str, Any], value)


def _resolve_path(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return repo_root / path


def _yaml_module() -> Any:
    return yaml
