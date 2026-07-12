"""Build deterministic file attention ledgers."""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import cast

from agent_context.reading import file_safety
from agent_maintainer.attention import signal_context, signals
from agent_maintainer.attention.models import (
    SCHEMA_VERSION,
    AttentionFileScore,
    AttentionLedger,
)

DEFAULT_OUTPUT_PATH = Path(".verify-logs/attention/files.json")
MAX_ATTENTION_LEDGER_BYTES = file_safety.MAX_FILE_BYTES

WEIGHT_ITEMS = (
    ("git_changed", 0.24),
    ("git_churn", 0.18),
    ("runtime_events", 0.17),
    ("verifier_artifacts", 0.14),
    ("docsync", 0.1),
    ("file_baselines", 0.1),
    ("path", 0.07),
)


def build_attention_ledger(  # noqa: PLR0913
    target: Path,
    *,
    log_dir: Path | None = None,
    events_dir: Path | None = None,
    max_tracked_files: int = signal_context.DEFAULT_MAX_TRACKED_FILES,
    artifact_read_limit_bytes: int = (signal_context.DEFAULT_ARTIFACT_READ_LIMIT_BYTES),
    priority_paths: Sequence[str] = (),
) -> AttentionLedger:
    """Return deterministic attention ledger for target repository."""
    repo_root = target.resolve()
    resolved_log_dir = log_dir or Path(".verify-logs")
    resolved_events_dir = events_dir or Path(".verify-logs/events")
    tracked_paths = signals.tracked_files(repo_root)
    inventory_context = signal_context.AttentionSignalContext.from_paths(
        repo_root,
        tracked_paths,
        max_tracked_files=0,
        artifact_read_limit_bytes=artifact_read_limit_bytes,
    )
    changed = signals.changed_counts(repo_root)
    verifier_artifacts = signals.verifier_artifact_counts(
        repo_root,
        log_dir=repo_root / resolved_log_dir,
        context=inventory_context,
    )
    explicit_paths, priority_notes = _validated_priority_paths(
        priority_paths,
        tracked_paths=tracked_paths,
    )
    context = signal_context.AttentionSignalContext.from_paths(
        repo_root,
        tracked_paths,
        required_paths=(*changed, *verifier_artifacts, *explicit_paths),
        max_tracked_files=max_tracked_files,
        artifact_read_limit_bytes=artifact_read_limit_bytes,
    )
    context.performance_notes.extend(priority_notes)
    files = context.tracked_paths
    raw_components = {
        "git_changed": changed,
        "git_churn": signals.churn_counts(repo_root),
        "runtime_events": signals.runtime_event_counts(
            repo_root,
            events_dir=repo_root / resolved_events_dir,
            context=context,
        ),
        "verifier_artifacts": verifier_artifacts,
        "docsync": signals.docsync_counts(repo_root, context=context),
        "file_baselines": signals.file_baseline_counts(
            repo_root,
            log_dir=repo_root / resolved_log_dir,
            context=context,
        ),
    }
    normalized = {name: _normalize_counts(counts) for name, counts in raw_components.items()}
    scored_files = tuple(_score_file(path, normalized=normalized) for path in files)
    visible_files = tuple(
        sorted(
            (score for score in scored_files if score.score > 0),
            key=lambda score: (-score.score, score.path),
        )
    )
    return AttentionLedger(
        schema_version=SCHEMA_VERSION,
        target=str(repo_root),
        file_count=len(visible_files),
        inputs={
            "tracked_files": len(files),
            "log_dir": resolved_log_dir.as_posix(),
            "events_dir": resolved_events_dir.as_posix(),
            "performance_guards": {
                "all_tracked_file_count": context.all_tracked_file_count,
                "scored_file_count": len(files),
                "artifact_read_limit_bytes": context.artifact_read_limit_bytes,
                "notes": list(context.performance_notes),
            },
            **{f"{name}_files": len(counts) for name, counts in raw_components.items()},
        },
        files=visible_files,
    )


def write_attention_ledger(ledger: AttentionLedger, output_path: Path) -> Path:
    """Write ledger JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(ledger.to_payload(), indent=2, sort_keys=True)
    output_path.write_text(
        f"{payload}\n",
        encoding="utf-8",
    )
    return output_path


def read_attention_ledger(
    path: Path,
    *,
    workspace_root: Path,
    max_bytes: int = MAX_ATTENTION_LEDGER_BYTES,
) -> AttentionLedger | None:
    """Read one safe repository-confined attention ledger, when valid."""
    safe_read = file_safety.read_bounded_utf8_file(
        path,
        workspace_root=workspace_root,
        max_bytes=max_bytes,
    )
    if not safe_read.safety.allowed or safe_read.text is None:
        return None
    payload = _decode_ledger(safe_read.text)
    if payload is None:
        return None
    return _validated_ledger(payload)


def _decode_ledger(text: str) -> object | None:
    """Decode ledger JSON without propagating malformed input failures."""

    try:
        return json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        return None


def _validated_ledger(payload: object) -> AttentionLedger | None:
    """Return a schema-compatible ledger without propagating input failures."""

    try:
        return _attention_ledger(payload)
    except (KeyError, TypeError, ValueError):
        return None


def _attention_ledger(payload: object) -> AttentionLedger:
    """Return a typed ledger from one decoded JSON object."""

    ledger, raw_files, raw_inputs = _ledger_collections(payload)
    files = tuple(_attention_file_score(item) for item in raw_files)
    schema_version = _plain_int(ledger.get("schema_version"), "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    file_count = _plain_int(ledger.get("file_count"), "file_count")
    if file_count != len(files):
        raise ValueError("file_count must match files")
    if len({item.path for item in files}) != len(files):
        raise ValueError("files must not contain duplicate paths")
    return AttentionLedger(
        schema_version=schema_version,
        target=_nonempty_string(ledger.get("target"), "target"),
        file_count=file_count,
        inputs=raw_inputs,
        files=files,
    )


def _ledger_collections(
    payload: object,
) -> tuple[dict[str, object], Sequence[object], dict[str, object]]:
    """Return the typed object, file sequence, and input table for a ledger."""

    ledger = _json_object(payload)
    if ledger is None:
        raise TypeError("attention ledger must be an object")
    raw_files = _object_sequence(ledger.get("files", ()))
    raw_inputs = _json_object(ledger.get("inputs", {}))
    if raw_files is None or raw_inputs is None:
        raise TypeError("attention ledger collections have invalid types")
    return ledger, raw_files, raw_inputs


def _attention_file_score(item: object) -> AttentionFileScore:
    """Return one typed attention file score from decoded JSON."""

    score_payload = _json_object(item)
    if score_payload is None:
        raise TypeError("attention file score must be an object")
    components = _json_object(score_payload.get("components"))
    reasons = _object_sequence(score_payload.get("reasons"))
    if components is None or reasons is None:
        raise TypeError("attention file score collections have invalid types")
    return AttentionFileScore(
        path=_repo_relative_path(score_payload.get("path")),
        score=_unit_interval(score_payload.get("score"), "score"),
        components={
            _nonempty_string(key, "component name"): _unit_interval(
                value,
                f"component {key}",
            )
            for key, value in components.items()
        },
        reasons=tuple(_nonempty_string(reason, "reason") for reason in reasons),
    )


def _json_object(value: object) -> dict[str, object] | None:
    """Return a JSON object with string keys, or ``None`` when malformed."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}


def _object_sequence(value: object) -> Sequence[object] | None:
    """Return a non-string sequence with an explicit element boundary."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return cast(Sequence[object], value)


def _plain_int(value: object, label: str) -> int:
    """Return a non-boolean integer."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    return value


def _nonempty_string(value: object, label: str) -> str:
    """Return a non-empty string."""

    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a non-empty string")
    return value


def _repo_relative_path(value: object) -> str:
    """Return one canonical repository-relative POSIX path."""

    path_text = _nonempty_string(value, "path")
    path = PurePosixPath(path_text)
    lexical_invalid = "\\" in path_text or path_text == "."
    structural_invalid = path.is_absolute() or path.as_posix() != path_text or ".." in path.parts
    if lexical_invalid or structural_invalid:
        raise ValueError(f"path is not canonical repository-relative: {path_text!r}")
    return path_text


def _validated_priority_paths(
    values: Sequence[str],
    *,
    tracked_paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return safe tracked priority paths and bounded omission notes."""

    tracked = set(tracked_paths)
    retained: set[str] = set()
    omitted: list[str] = []
    for value in values:
        normalized = _repo_relative_path(value)
        if file_safety.sensitive_path(Path(normalized)):
            raise ValueError(f"priority path is sensitive: {normalized!r}")
        if normalized in tracked:
            retained.add(normalized)
        else:
            omitted.append(f"priority path not tracked and omitted: {normalized}")
    return tuple(sorted(retained)), tuple(omitted)


def _unit_interval(value: object, label: str) -> float:
    """Return one finite score in the closed interval 0..1."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number")
    score = float(value)
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError(f"{label} must be finite and between 0 and 1")
    return score


def _score_file(
    path: str,
    *,
    normalized: dict[str, dict[str, float]],
) -> AttentionFileScore:
    """Return weighted score for one file."""
    components = {name: values.get(path, float(0)) for name, values in normalized.items()}
    components["path"] = signals.path_heuristic_score(path)
    score = min(
        1.0,
        sum(weight * components[name] for name, weight in WEIGHT_ITEMS),
    )
    rounded_components = {
        name: round(value, 4) for name, value in sorted(components.items()) if value > 0
    }
    return AttentionFileScore(
        path=path,
        score=round(score, 4),
        components=rounded_components,
        reasons=_reasons(path, rounded_components),
    )


def _normalize_counts(counts: Counter[str]) -> dict[str, float]:
    """Normalize count values to 0..1."""
    if not counts:
        return {}
    max_count = max(counts.values())
    if max_count <= 0:
        return {}
    return {path: min(1.0, count / max_count) for path, count in counts.items() if count > 0}


def _reasons(path: str, components: dict[str, float]) -> tuple[str, ...]:
    """Return human-readable non-zero component reasons."""
    labels = {
        "docsync": "mentioned by DocSync evidence",
        "file_baselines": "mentioned by file-baseline evidence",
        "git_changed": "changed in current worktree or index",
        "git_churn": "recent committed churn",
        "path": "important repository path",
        "runtime_events": "mentioned by runtime events",
        "verifier_artifacts": "mentioned by verifier artifacts",
    }
    return tuple(f"{path}: {labels[name]}" for name in sorted(components))
