"""Attention ledger helpers for context packs."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from agent_context.reading import file_safety
from agent_maintainer.attention import builder as attention_builder
from agent_maintainer.attention.models import AttentionFileScore
from agent_maintainer.core.structured_values import json_array, json_objects

ATTENTION_LEDGER_PATH = Path("attention/files.json")
MAX_ATTENTION_ENTRIES = 5
MAX_RISK_NOTES = 3
MAX_ATTENTION_LEDGER_BYTES = 1_048_576
PATH_PATTERN = re.compile(
    r"(?P<path>(?:src|tests|docs|config|examples|\.github|\.codex|\.claude)/[^\s:'\"`]+)"
)


def attention_payload(
    log_dir: Path,
    exact_facts: list[dict[str, object]],
    selected_logs: list[dict[str, object]],
    *,
    workspace_root: Path,
) -> dict[str, object]:
    """Return optional attention block for one context pack."""
    ledger_path = log_dir / ATTENTION_LEDGER_PATH
    confined = file_safety.confined_path(ledger_path, workspace_root=workspace_root)
    if isinstance(confined, file_safety.FileSafety):
        return {
            "available": False,
            "ledger_path": str(ledger_path),
            "entries": [],
            "risk_notes": [],
        }
    safety = file_safety.inspect_path(
        confined,
        max_bytes=MAX_ATTENTION_LEDGER_BYTES,
    )
    if safety is not None:
        return {
            "available": False,
            "ledger_path": str(ledger_path),
            "entries": [],
            "risk_notes": [],
        }
    ledger = attention_builder.read_attention_ledger(
        confined,
        workspace_root=workspace_root,
    )
    if ledger is None:
        return {
            "available": False,
            "ledger_path": str(ledger_path),
            "entries": [],
            "risk_notes": [],
        }
    by_path = {score.path: score for score in ledger.files}
    selected_paths = _fact_paths(exact_facts)
    if not selected_paths:
        selected_paths = _log_paths(selected_logs, by_path)
    entries = _selected_entries(by_path, selected_paths)
    if not entries:
        entries = list(ledger.files[:MAX_ATTENTION_ENTRIES])
    return {
        "available": True,
        "ledger_path": str(ledger_path),
        "entries": [_entry_payload(entry) for entry in entries[:MAX_ATTENTION_ENTRIES]],
        "risk_notes": _risk_notes(entries),
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
            "reasons": by_path[path].get("reasons", []),
        }
        attached.append(fact_copy)
    return attached


def _fact_paths(facts: list[dict[str, object]]) -> tuple[str, ...]:
    """Return unique file paths from exact repair facts."""
    return _unique_paths(str(path) for fact in facts if isinstance((path := fact.get("path")), str))


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


def _selected_entries(
    by_path: dict[str, AttentionFileScore],
    paths: tuple[str, ...],
) -> list[AttentionFileScore]:
    """Return attention entries matching selected paths."""
    entries = [by_path[path] for path in paths if path in by_path]
    return sorted(entries, key=lambda entry: (-entry.score, entry.path))


def _risk_notes(entries: list[AttentionFileScore]) -> list[str]:
    """Return compact bounded risk notes."""
    notes: list[str] = []
    for entry in entries[:MAX_RISK_NOTES]:
        reasons = "; ".join(entry.reasons[:2])
        notes.append(f"{entry.path} attention {entry.score:.4f}: {reasons}")
    return notes


def _entry_payload(entry: AttentionFileScore) -> dict[str, object]:
    """Return JSON-safe attention entry."""
    return {
        "path": entry.path,
        "score": entry.score,
        "components": entry.components,
        "reasons": list(entry.reasons),
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
