"""Resolve configured DocSync read and write roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docsync.config.defaults import DEFAULT_FRESHNESS_FILENAME
from docsync.config.errors import ConfigError, PathBoundaryError
from docsync.config.io import validate_write_target
from docsync.config.paths import (
    require_strict_descendant,
    require_unreserved_output,
    require_within,
    resolve_directory_within,
    resolve_input_within,
    resolve_within,
)

DEFAULT_OUTPUT_ROOT = Path(".docsync/out")


@dataclass(frozen=True)
class ResolvedOutputs:
    """Validated DocSync generated-output paths."""

    directory: Path
    index_json: Path
    report_json: Path
    review_packet_json: Path
    review_prompt_md: Path


@dataclass(frozen=True)
class ResolvedConfigPaths:
    """Validated filesystem paths derived from DocSync configuration."""

    config: Path
    trace: Path
    attestations: Path
    outputs: ResolvedOutputs


def resolve_config_path(repo_root: Path, candidate: Path) -> Path:
    """Resolve one bounded repository-owned configuration file."""

    try:
        return _resolve_config_path(repo_root, candidate)
    except PathBoundaryError as exc:
        raise ConfigError(str(exc)) from exc


def resolve_config_paths(
    repo_root: Path,
    config_path: Path,
    outputs: dict[str, Any],
    attestations: dict[str, Any],
) -> ResolvedConfigPaths:
    """Resolve all configured DocSync filesystem paths."""

    try:
        return _resolve_config_paths(repo_root, config_path, outputs, attestations)
    except PathBoundaryError as exc:
        raise ConfigError(str(exc)) from exc


def _resolve_config_path(repo_root: Path, candidate: Path) -> Path:
    resolved = resolve_within(repo_root, candidate, label="DocSync config path")
    if resolved.exists():
        return resolve_input_within(repo_root, candidate, label="DocSync config path")
    raise ConfigError(f"DocSync config not found: {resolved}")


def _resolve_config_paths(
    repo_root: Path,
    config_path: Path,
    outputs: dict[str, Any],
    attestations: dict[str, Any],
) -> ResolvedConfigPaths:
    resolved_outputs = _resolve_outputs(repo_root, outputs)
    attestation_dir = _resolve_attestation_directory(repo_root, attestations)
    trace_path = resolve_within(
        repo_root,
        Path(".docsync/trace.yml"),
        label="DocSync trace path",
    )
    return ResolvedConfigPaths(
        config=config_path,
        trace=trace_path,
        attestations=attestation_dir,
        outputs=resolved_outputs,
    )


def _resolve_outputs(repo_root: Path, configured: dict[str, Any]) -> ResolvedOutputs:
    generated_root = resolve_within(
        repo_root,
        DEFAULT_OUTPUT_ROOT,
        label="DocSync generated-output root",
    )
    output_dir = _resolve_output_directory(repo_root, generated_root, configured)
    index_json = _resolve_output_path(repo_root, output_dir, configured, "index_json", "index.json")
    report_json = _resolve_output_path(
        repo_root,
        output_dir,
        configured,
        "report_json",
        "report.json",
    )
    review_packet_json = _resolve_output_path(
        repo_root,
        output_dir,
        configured,
        "review_packet_json",
        "review-packet.json",
    )
    review_prompt_md = _resolve_output_path(
        repo_root,
        output_dir,
        configured,
        "review_prompt_md",
        "review-prompt.md",
    )
    sarif_path = _derived_sarif_path(output_dir, report_json)
    freshness_path = output_dir / DEFAULT_FRESHNESS_FILENAME
    _require_distinct_outputs(
        output_dir,
        index_json,
        report_json,
        sarif_path,
        review_packet_json,
        review_prompt_md,
        freshness_path,
    )
    return ResolvedOutputs(
        directory=output_dir,
        index_json=index_json,
        report_json=report_json,
        review_packet_json=review_packet_json,
        review_prompt_md=review_prompt_md,
    )


def _resolve_output_directory(
    repo_root: Path,
    generated_root: Path,
    configured: dict[str, Any],
) -> Path:
    candidate = Path(str(configured.get("directory", DEFAULT_OUTPUT_ROOT)))
    resolved = resolve_directory_within(repo_root, candidate, label="DocSync output directory")
    return require_within(generated_root, resolved, label="DocSync output directory")


def _resolve_output_path(
    repo_root: Path,
    output_dir: Path,
    outputs: dict[str, Any],
    key: str,
    default_name: str,
) -> Path:
    configured = outputs.get(key)
    candidate = _output_candidate(repo_root, output_dir, configured, default_name)
    resolved = resolve_within(repo_root, candidate, label=f"DocSync output '{key}'")
    contained = require_strict_descendant(output_dir, resolved, label=f"DocSync output '{key}'")
    label = f"DocSync output '{key}'"
    return validate_write_target(require_unreserved_output(contained, label=label), label=label)


def _output_candidate(
    repo_root: Path,
    output_dir: Path,
    configured: object,
    default_name: str,
) -> Path:
    if configured is not None:
        return Path(str(configured))
    return output_dir.relative_to(repo_root) / default_name


def _derived_sarif_path(output_dir: Path, report_json: Path) -> Path:
    path = require_strict_descendant(
        output_dir,
        report_json.with_suffix(".sarif.json"),
        label="DocSync derived SARIF output",
    )
    return validate_write_target(path, label="DocSync derived SARIF output")


def _require_distinct_outputs(output_dir: Path, *paths: Path) -> None:
    collision_keys = {_output_collision_key(output_dir, path) for path in paths}
    if len(collision_keys) == len(paths):
        return
    raise PathBoundaryError("DocSync configured output files must be distinct")


def _output_collision_key(output_dir: Path, path: Path) -> str:
    """Return a platform-conservative generated-output identity."""

    return path.relative_to(output_dir).as_posix().casefold()


def _resolve_attestation_directory(repo_root: Path, configured: dict[str, Any]) -> Path:
    root = resolve_within(
        repo_root,
        Path(".docsync/attestations"),
        label="DocSync attestation root",
    )
    candidate = Path(str(configured.get("directory", ".docsync/attestations")))
    directory = resolve_directory_within(
        repo_root,
        candidate,
        label="DocSync attestation directory",
        reject_sensitive=True,
    )
    return require_within(root, directory, label="DocSync attestation directory")
