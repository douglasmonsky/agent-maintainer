"""Remove stable Agent Maintainer identities from client configuration."""

from __future__ import annotations

import json

from agent_client_hooks import merge, templates


def remove_claude_settings(existing: str) -> str:
    """Remove only managed Claude hook commands from settings JSON text."""

    payload = json.loads(existing)
    if not isinstance(payload, dict):
        raise ValueError("Claude settings must contain a JSON object")
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict):
        return existing
    changed = _remove_managed_claude_events(hooks)
    if not changed:
        return existing
    if not hooks:
        payload.pop("hooks", None)
    if not payload:
        return ""
    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def remove_codex_config(existing: str) -> str:
    """Remove managed current and legacy Codex hook blocks from config text."""

    without_block = merge.strip_managed_block(existing, templates.CODEX_MARKER)
    without_legacy = merge.strip_previous_agent_codex_hooks(without_block)
    if without_legacy == existing:
        return existing
    remaining = without_legacy.strip()
    return f"{remaining}\n" if remaining else ""


def _remove_managed_claude_events(hooks: dict[object, object]) -> bool:
    """Remove managed entries while retaining unrelated event content."""

    changed = False
    for event, entries in tuple(hooks.items()):
        if not isinstance(entries, list):
            continue
        cleaned_entries, removed = _clean_claude_entries(entries)
        if not removed:
            continue
        changed = True
        if cleaned_entries:
            hooks[event] = cleaned_entries
        else:
            hooks.pop(event, None)
    return changed


def _clean_claude_entries(entries: list[object]) -> tuple[list[object], bool]:
    """Return entries with managed commands removed at their narrowest owner."""

    cleaned_entries: list[object] = []
    removed = False
    for entry in entries:
        cleaned, entry_removed = merge.strip_managed_claude_entry(entry)
        removed = removed or entry_removed
        if cleaned is not None:
            cleaned_entries.append(cleaned)
    return cleaned_entries, removed
