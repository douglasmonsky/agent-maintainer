"""Attention ledger helpers for context packs."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from agent_context.reading import file_safety
from agent_maintainer.attention import builder as attention_builder
from agent_maintainer.attention.models import AttentionFileScore
from agent_maintainer.core.structured_values import json_array, json_objects

ATTENTION_LEDGER_PATH = Path("attention/files.json")
ATTENTION_CONTEXT_SCHEMA_VERSION = 1
MAX_ATTENTION_ENTRIES = 5
MAX_RISK_NOTES = 3
MAX_ATTENTION_LEDGER_BYTES = 1_048_576
DIRECT_RELEVANCE = "direct"
INFERRED_RELEVANCE = "inferred"
BACKGROUND_RELEVANCE = "background"
PATH_PATTERN = re.compile(
    r"(?P<path>(?:src|tests|docs|config|examples|\.github|\.codex|\.claude)/[^\s:'\"`]+)"
)


@dataclass(frozen=True)
class ContextAttentionEntry:
    """One context-selected path with explicit relevance provenance."""

    path: str
    relevance: str
    ledger_score: AttentionFileScore | None


def attention_payload(
    log_dir: Path,
    exact_facts: list[dict[str, object]],
    selected_logs: list[dict[str, object]],
    *,
    workspace_root: Path,
    requested_paths: Iterable[Path] = (),
) -> dict[str, object]:
    """Return optional attention block for one context pack."""
    ledger_path = log_dir / ATTENTION_LEDGER_PATH
    confined = file_safety.confined_path(ledger_path, workspace_root=workspace_root)
    if isinstance(confined, file_safety.FileSafety):
        return _unavailable_payload(ledger_path)
    safety = file_safety.inspect_path(
        confined,
        max_bytes=MAX_ATTENTION_LEDGER_BYTES,
    )
    if safety is not None:
        return _unavailable_payload(ledger_path)
    ledger = attention_builder.read_attention_ledger(
        confined,
        workspace_root=workspace_root,
    )
    if ledger is None:
        return _unavailable_payload(ledger_path)
    by_path = {score.path: score for score in ledger.files}
    direct_paths = _unique_paths(
        (*_fact_paths(exact_facts), *_requested_paths(requested_paths, workspace_root))
    )
    inferred_paths = tuple(
        path for path in _log_paths(selected_logs, by_path) if path not in direct_paths
    )
    entries = _context_entries(
        by_path,
        direct_paths,
        relevance=DIRECT_RELEVANCE,
    )
    entries.extend(
        _context_entries(
            by_path,
            inferred_paths,
            relevance=INFERRED_RELEVANCE,
        )
    )
    if not entries:
        entries = [
            ContextAttentionEntry(item.path, BACKGROUND_RELEVANCE, item)
            for item in ledger.files[:MAX_ATTENTION_ENTRIES]
        ]
    visible_entries = entries[:MAX_ATTENTION_ENTRIES]
    return {
        "schema_version": ATTENTION_CONTEXT_SCHEMA_VERSION,
        "available": True,
        "ledger_path": str(ledger_path),
        "entries": [_entry_payload(entry) for entry in visible_entries],
        "risk_notes": _risk_notes(visible_entries),
    }


def attach_attention_to_facts(
    facts: list[dict[str, object]],
    attention: dict[str, object],
) -> list[dict[str, object]]:
    """Attach attention score metadata to facts mentioning files."""
    entries = json_array(attention.get("entries"))
    if entries is None:
        return facts
    by_path = {str(entry["path"]): entry for entry in json_objects(entries) if entry.get("path")}
    attached: list[dict[str, object]] = []
    for fact in facts:
        path = fact.get("path")
        if not isinstance(path, str) or path not in by_path:
            attached.append(fact)
            continue
        fact_copy = dict(fact)
        fact_copy["attention"] = {
            "score": by_path[path].get("score"),
            "relevance": by_path[path].get("relevance"),
            "reasons": by_path[path].get("reasons", []),
        }
        attached.append(fact_copy)
    return attached


def _fact_paths(facts: list[dict[str, object]]) -> tuple[str, ...]:
    """Return unique file paths from exact repair facts."""
    return _unique_paths(str(path) for fact in facts if isinstance((path := fact.get("path")), str))


def _requested_paths(paths: Iterable[Path], workspace_root: Path) -> tuple[str, ...]:
    """Return safe requested paths as repository-relative POSIX paths."""

    normalized: list[str] = []
    for path in paths:
        confined = file_safety.confined_path(path, workspace_root=workspace_root)
        if isinstance(confined, file_safety.FileSafety):
            continue
        if file_safety.inspect_path(confined) is not None:
            continue
        normalized.append(confined.relative_to(workspace_root.resolve()).as_posix())
    return _unique_paths(normalized)


def _log_paths(
    selected_logs: list[dict[str, object]],
    by_path: dict[str, AttentionFileScore],
) -> tuple[str, ...]:
    """Return paths mentioned by selected logs."""
    mentions: list[str] = []
    for log in selected_logs:
        text = str(log.get("text", ""))
        source = str(log.get("source", ""))
        mentions.extend(path for path in by_path if path in text or path in source)
        mentions.extend(match.group("path").rstrip(".,)") for match in PATH_PATTERN.finditer(text))
    return _unique_paths(path for path in mentions if path in by_path)


def _context_entries(
    by_path: dict[str, AttentionFileScore],
    paths: tuple[str, ...],
    *,
    relevance: str,
) -> list[ContextAttentionEntry]:
    """Return provenance-aware entries for selected paths."""

    entries: list[ContextAttentionEntry] = []
    for path in paths:
        score = by_path.get(path)
        if score is None and relevance != DIRECT_RELEVANCE:
            continue
        entries.append(ContextAttentionEntry(path, relevance, score))
    return entries


def _risk_notes(entries: list[ContextAttentionEntry]) -> list[str]:
    """Return compact bounded risk notes."""
    notes: list[str] = []
    for entry in entries:
        if entry.relevance == BACKGROUND_RELEVANCE:
            continue
        if entry.ledger_score is None:
            notes.append(f"{entry.path} selected directly; no sampled attention score")
        else:
            reasons = "; ".join(entry.ledger_score.reasons[:2])
            notes.append(f"{entry.path} attention {entry.ledger_score.score:.4f}: {reasons}")
        if len(notes) == MAX_RISK_NOTES:
            break
    return notes


def _entry_payload(entry: ContextAttentionEntry) -> dict[str, object]:
    """Return JSON-safe attention entry."""

    score = entry.ledger_score
    if score is None:
        score_value: float | None = None
        components: dict[str, float] = {}
        reasons = ["direct context path has no sampled attention score"]
    else:
        score_value = score.score
        components = score.components
        reasons = list(score.reasons)
    return {
        "path": entry.path,
        "score": score_value,
        "relevance": entry.relevance,
        "components": components,
        "reasons": reasons,
    }


def _unavailable_payload(ledger_path: Path) -> dict[str, object]:
    """Return one schema-versioned unavailable attention block."""

    return {
        "schema_version": ATTENTION_CONTEXT_SCHEMA_VERSION,
        "available": False,
        "ledger_path": str(ledger_path),
        "entries": [],
        "risk_notes": [],
    }


def _unique_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """Return unique non-empty paths preserving order."""
    seen: set[str] = set()
    output: list[str] = []
    for path in paths:
        if path and path not in seen:
            seen.add(path)
            output.append(path)
    return tuple(output)
