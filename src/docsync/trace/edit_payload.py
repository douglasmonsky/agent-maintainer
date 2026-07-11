"""Read, validate, and write trace-authoring payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from docsync.config.io import write_text_file
from docsync.config.load import ConfigError, load_yaml_mapping
from docsync.config.paths import PathBoundaryError, resolve_input_within
from docsync.trace.errors import TraceEditError

TRACE_SECTIONS = ("documents", "objects", "claims", "evidence")


def load_payload(repo_root: Path, trace_path: Path | None) -> tuple[Path, dict[str, Any]]:
    """Load and validate one editable trace payload."""

    resolved_trace = _resolve_trace_path(repo_root, trace_path)
    payload = _load_trace_mapping(resolved_trace)
    _validate_payload(payload)
    return resolved_trace, payload


def payload_section(payload: dict[str, Any], section: str) -> dict[str, Any]:
    """Return one validated mutable trace section."""

    return cast(dict[str, Any], payload[section])


def reject_existing(section: dict[str, Any], item_id: str, force: bool) -> None:
    """Reject an existing trace entry unless replacement was requested."""

    if force or item_id not in section:
        return
    raise TraceEditError(f"DocSync trace entry already exists: {item_id}")


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    """Write an ordered trace payload to its preflighted target."""

    ordered: dict[str, Any] = {"version": payload.get("version", 1)}
    for section in TRACE_SECTIONS:
        values = cast(dict[str, Any], payload[section])
        ordered[section] = {key: values[key] for key in sorted(values)}
    write_text_file(
        path,
        yaml.safe_dump(ordered, sort_keys=False),
        label="DocSync trace edit output",
    )


def _resolve_trace_path(repo_root: Path, trace_path: Path | None) -> Path:
    candidate = Path(".docsync/trace.yml") if trace_path is None else trace_path
    try:
        return resolve_input_within(
            repo_root.resolve(),
            candidate,
            label="DocSync trace edit path",
        )
    except PathBoundaryError as exc:
        raise TraceEditError(str(exc)) from exc


def _load_trace_mapping(path: Path) -> dict[str, Any]:
    try:
        return load_yaml_mapping(path)
    except ConfigError as exc:
        raise TraceEditError(str(exc)) from exc


def _validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("version") != 1:
        raise TraceEditError("DocSync trace version must be 1")
    for section in TRACE_SECTIONS:
        payload.setdefault(section, {})
        if not isinstance(payload[section], dict):
            raise TraceEditError(f"DocSync trace '{section}' must be a mapping")
