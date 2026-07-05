"""Render optional attention metadata in context packs."""

from __future__ import annotations

MAX_POINTER_NOTES = 3
MAX_MARKDOWN_ENTRIES = 5


def attention_pointer_lines(attention: object) -> list[str]:
    """Return bounded attention notes for hook-safe pointer output."""
    if not isinstance(attention, dict) or not attention.get("available"):
        return []
    notes = _bounded_string_lines(attention.get("risk_notes"), limit=MAX_POINTER_NOTES)
    if not notes:
        return []
    return ["", "Attention notes:", *[f"- {note}" for note in notes]]


def attention_lines(attention: object) -> list[str]:
    """Return Markdown attention section."""
    if not isinstance(attention, dict) or not attention.get("available"):
        return ["- Attention ledger unavailable."]
    return [
        f"- Ledger: `{attention.get('ledger_path', '<unknown>')}`",
        *_attention_note_lines(attention.get("risk_notes")),
        *_attention_entry_section(attention.get("entries")),
    ]


def _attention_note_lines(notes: object) -> list[str]:
    """Return Markdown risk-note lines."""
    bounded_notes = _bounded_string_lines(notes, limit=MAX_POINTER_NOTES)
    if not bounded_notes:
        return []
    return ["- Risk notes:", *[f"  - {note}" for note in bounded_notes]]


def _attention_entry_section(entries: object) -> list[str]:
    """Return Markdown entry section."""
    if not isinstance(entries, list) or not entries:
        return []
    return ["- Entries:", *_attention_entry_lines(entries[:MAX_MARKDOWN_ENTRIES])]


def _bounded_string_lines(values: object, *, limit: int) -> list[str]:
    """Return bounded string values."""
    if not isinstance(values, list):
        return []
    return [value for value in values[:limit] if isinstance(value, str)]


def _attention_entry_lines(entries: list[object]) -> list[str]:
    """Return compact attention entry lines."""
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path", "<unknown>")
        score = entry.get("score", 0)
        lines.append(f"  - {score}: {path}")
    return lines
