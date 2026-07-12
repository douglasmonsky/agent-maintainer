"""Render optional attention metadata in context packs."""

from __future__ import annotations

from agent_context.structured_values import json_array, json_object, json_objects

MAX_POINTER_NOTES = 3
MAX_MARKDOWN_ENTRIES = 5


def attention_pointer_lines(attention: object) -> list[str]:
    """Return bounded attention notes for hook-safe pointer output."""
    payload = json_object(attention)
    if payload is None or not payload.get("available"):
        return []
    notes = _bounded_string_lines(payload.get("risk_notes"), limit=MAX_POINTER_NOTES)
    if not notes:
        return []
    return ["", "Attention notes:", *[f"- {note}" for note in notes]]


def attention_lines(attention: object) -> list[str]:
    """Return Markdown attention section."""
    payload = json_object(attention)
    if payload is None or not payload.get("available"):
        return ["- Attention ledger unavailable."]
    return [
        f"- Ledger: `{payload.get('ledger_path', '<unknown>')}`",
        *_attention_note_lines(payload.get("risk_notes")),
        *_attention_entry_section(payload.get("entries")),
    ]


def _attention_note_lines(notes: object) -> list[str]:
    """Return Markdown risk-note lines."""
    bounded_notes = _bounded_string_lines(notes, limit=MAX_POINTER_NOTES)
    if not bounded_notes:
        return []
    return ["- Risk notes:", *[f"  - {note}" for note in bounded_notes]]


def _attention_entry_section(entries: object) -> list[str]:
    """Return Markdown entry section."""
    parsed = json_objects(entries)
    if not parsed:
        return []
    return ["- Entries:", *_attention_entry_lines(parsed[:MAX_MARKDOWN_ENTRIES])]


def _bounded_string_lines(values: object, *, limit: int) -> list[str]:
    """Return bounded string values."""
    parsed = json_array(values)
    if parsed is None:
        return []
    return [value for value in parsed[:limit] if isinstance(value, str)]


def _attention_entry_lines(entries: list[dict[str, object]]) -> list[str]:
    """Return compact attention entry lines."""
    lines: list[str] = []
    for entry in entries:
        path = entry.get("path", "<unknown>")
        score = entry.get("score")
        score_text = "unscored" if score is None else str(score)
        lines.append(f"  - {score_text}: {path}")
    return lines
