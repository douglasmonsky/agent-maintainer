"""Validate repository-controlled inputs used to build context packs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from agent_context import failures as context_failures
from agent_context.reading import file_safety

MAX_EXACT_FACT_INPUT_BYTES = 8_388_608


def safe_exact_fact_record(
    log_dir: Path,
    record: context_failures.FailureRecord,
    *,
    workspace_root: Path,
) -> context_failures.FailureRecord:
    """Remove unsafe manifest-controlled paths before exact-fact parsing."""

    return replace(
        record,
        log_path=(
            safe_manifest_input(
                log_dir,
                record.log_path,
                workspace_root=workspace_root,
            )
            or ""
        ),
        artifact_paths=tuple(
            path
            for path in record.artifact_paths
            if safe_manifest_input(
                log_dir,
                path,
                workspace_root=workspace_root,
            )
            is not None
        ),
    )


def safe_manifest_input(
    log_dir: Path,
    path_text: str,
    *,
    workspace_root: Path,
) -> str | None:
    """Return a safe relative manifest path, or refuse it without opening."""

    path = Path(path_text)
    if unsafe_manifest_path(path_text, path):
        return None
    root = workspace_root.resolve()
    resolved_log_dir = log_dir if log_dir.is_absolute() else root / log_dir
    rooted = root / path
    candidate = rooted if rooted.exists() else resolved_log_dir / path.name
    confined = file_safety.confined_path(candidate, workspace_root=root)
    if isinstance(confined, file_safety.FileSafety):
        return None
    safety = file_safety.inspect_path(confined, max_bytes=MAX_EXACT_FACT_INPUT_BYTES)
    return path_text if safety is None else None


def safe_baseline_path(path: Path | None) -> Path | None:
    """Return a bounded repository-relative ratchet baseline when safe."""

    if path is None or unsafe_relative_path(path):
        return None
    safety = file_safety.inspect_path(path, max_bytes=MAX_EXACT_FACT_INPUT_BYTES)
    return path if safety is None else None


def unsafe_manifest_path(path_text: str, path: Path) -> bool:
    """Return whether manifest text fails lexical and sensitivity policy."""

    return not path_text or unsafe_relative_path(path) or file_safety.sensitive_path(path)


def unsafe_relative_path(path: Path) -> bool:
    """Return whether a path is absolute or lexically escapes its root."""

    return path.is_absolute() or ".." in path.parts
