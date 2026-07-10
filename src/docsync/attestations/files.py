"""Bounded loading of DocSync attestation YAML files."""

from __future__ import annotations

import heapq
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from docsync.config.io import MAX_REPOSITORY_INPUT_BYTES
from docsync.config.load import ConfigError, load_yaml_mapping
from docsync.config.paths import PathBoundaryError, resolve_input_within
from docsync.core.models import Attestation, DocSyncIndex, Finding, LineSpan

MAX_ATTESTATION_FILES = 128
MAX_ATTESTATION_TOTAL_BYTES = MAX_REPOSITORY_INPUT_BYTES + MAX_REPOSITORY_INPUT_BYTES


@dataclass
class AttestationLoadState:
    """Mutable bounded-attestation loading state."""

    records: list[Attestation] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)
    remaining_bytes: int = MAX_ATTESTATION_TOTAL_BYTES


def load_attestation_files(index: DocSyncIndex) -> tuple[list[Attestation], list[Finding]]:
    """Load bounded attestation records and syntax findings."""

    directory = index.config.attestations_dir
    if not directory.exists():
        return [], []
    state = AttestationLoadState()
    candidates, overflow = _discover_attestation_candidates(directory)
    for candidate in candidates:
        if not _consume_attestation_candidate(index, candidate, state):
            break
    if overflow is not None:
        state.findings.append(_file_limit_finding(overflow))
    return state.records, state.findings


def _discover_attestation_candidates(directory: Path) -> tuple[tuple[Path, ...], Path | None]:
    """Select a deterministic candidate prefix using bounded memory."""

    discovery_limit = MAX_ATTESTATION_FILES + 1
    with os.scandir(directory) as entries:
        selected = heapq.nsmallest(
            discovery_limit,
            _attestation_paths(directory, entries),
            key=lambda path: path.name,
        )
    if len(selected) <= MAX_ATTESTATION_FILES:
        return tuple(selected), None
    return tuple(selected[:-1]), selected[-1]


def _attestation_paths(
    directory: Path,
    entries: Iterator[os.DirEntry[str]],
) -> Iterator[Path]:
    return (directory / entry.name for entry in entries if entry.name.endswith((".yml", ".yaml")))


def _consume_attestation_candidate(
    index: DocSyncIndex,
    candidate: Path,
    state: AttestationLoadState,
) -> bool:
    resolved = _resolve_attestation_candidate(index, candidate)
    if isinstance(resolved, Finding):
        state.findings.append(resolved)
        return True
    budget_finding = _consume_byte_budget(state, resolved)
    if budget_finding is not None:
        state.findings.append(budget_finding)
        return False
    loaded, load_findings = _load_attestation_file(resolved)
    state.findings.extend(load_findings)
    _append_attestation_records(state, loaded)
    return True


def _file_limit_finding(path: Path) -> Finding:
    return _finding(
        "DS301",
        f"Attestation file limit exceeded: {MAX_ATTESTATION_FILES}.",
        path,
    )


def _resolve_attestation_candidate(index: DocSyncIndex, candidate: Path) -> Path | Finding:
    try:
        return resolve_input_within(
            index.config.repo_root,
            candidate.relative_to(index.config.repo_root),
            label="DocSync attestation input",
        )
    except (PathBoundaryError, ValueError) as exc:
        return _finding("DS301", str(exc), candidate)


def _consume_byte_budget(state: AttestationLoadState, path: Path) -> Finding | None:
    size = path.stat().st_size
    if size <= state.remaining_bytes:
        state.remaining_bytes -= size
        return None
    return _finding(
        "DS301",
        f"Attestation inputs exceed {MAX_ATTESTATION_TOTAL_BYTES} bytes.",
        path,
    )


def _append_attestation_records(
    state: AttestationLoadState,
    records: tuple[Attestation, ...],
) -> None:
    for record in records:
        if record.attestation_id in state.seen_ids:
            state.findings.append(
                _finding(
                    "DS305",
                    f"Duplicate attestation {record.attestation_id}.",
                    record.path,
                )
            )
            continue
        state.seen_ids.add(record.attestation_id)
        state.records.append(record)


def _load_attestation_file(path: Path) -> tuple[tuple[Attestation, ...], list[Finding]]:
    try:
        raw_records_value = load_yaml_mapping(path).get("attestations", [])
    except ConfigError as exc:
        return (), [_finding("DS301", str(exc), path)]
    if not isinstance(raw_records_value, list):
        return (), [_finding("DS301", "attestations must be a list", path)]
    raw_records = cast(list[object], raw_records_value)
    records: list[Attestation] = []
    findings: list[Finding] = []
    for index, raw_record in enumerate(raw_records):
        if not isinstance(raw_record, dict):
            findings.append(_finding("DS301", f"attestations[{index}] must be a mapping", path))
            continue
        records.append(_record(path, cast(dict[str, Any], raw_record)))
    return tuple(records), findings


def _record(path: Path, payload: dict[str, Any]) -> Attestation:
    return Attestation(
        attestation_id=str(payload.get("id", "")),
        claim_id=str(payload.get("claim", "")),
        doc_object_id=str(payload.get("doc_object", "")),
        evidence_ids=_string_tuple(payload.get("evidence", ())),
        reason=str(payload.get("reason", "")),
        evidence_fingerprints=_fingerprint_map(payload.get("evidence_fingerprints", {})),
        evidence_anchor_fingerprints=_anchor_fingerprint_map(
            payload.get("evidence_anchor_fingerprints", {})
        ),
        reviewer=_optional_string(payload.get("reviewer")),
        reviewed_at=_optional_string(payload.get("reviewed_at")),
        base_ref=_optional_string(payload.get("base")),
        head_ref=_optional_string(payload.get("head")),
        expires_at=_optional_string(payload.get("expires_at")),
        statement=_optional_string(payload.get("statement")),
        path=path,
    )


def _fingerprint_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    mapping = cast(dict[object, object], value)
    return {str(key): str(item) for key, item in mapping.items()}


def _anchor_fingerprint_map(value: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        return {}
    mapping = cast(dict[object, object], value)
    return {str(key): _string_tuple(item) for key, item in mapping.items()}


def _string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        items = cast(list[object] | tuple[object, ...], value)
        return tuple(str(item) for item in items)
    return (str(value),)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _finding(code: str, message: str, path: Path) -> Finding:
    return Finding(
        code=code,
        severity="error",
        message=message,
        locations=(LineSpan(path=path, start_line=1, end_line=1),),
    )
