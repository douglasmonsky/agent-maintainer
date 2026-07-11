"""Identity-aware Claude Code hook configuration merging."""

from __future__ import annotations

import json
from pathlib import Path

from agent_client_hooks import constants, manifest
from agent_client_hooks.structured_values import json_array, json_object


def merge_claude_settings(path: Path, managed_content: str) -> str:
    """Merge managed hook settings into existing Claude settings JSON."""

    with path.open(encoding="utf-8") as stream:
        current = json.load(stream)
    current_payload = json_object(current) or {}
    managed = json_object(json.loads(managed_content))
    managed_hooks = None if managed is None else json_object(managed.get("hooks"))
    if managed_hooks is None:
        raise ValueError("managed Claude settings must contain a hooks object")
    hooks = json_object(current_payload.get("hooks")) or {}
    current_payload["hooks"] = hooks
    for event, entries in managed_hooks.items():
        hooks[event] = merge_claude_event(hooks.get(event), entries)
    return f"{json.dumps(current_payload, indent=2, sort_keys=True)}\n"


def merge_claude_event(current: object, managed: object) -> list[object]:
    """Replace only Agent Maintainer entries while preserving user ordering."""

    managed_entries = json_array(managed) or []
    current_entries = json_array(current)
    if current_entries is None:
        return managed_entries
    preserved, insertion_index = _preserved_entries(current_entries)
    insert_at = len(preserved) if insertion_index is None else insertion_index
    return [*preserved[:insert_at], *managed_entries, *preserved[insert_at:]]


def _preserved_entries(current: list[object]) -> tuple[list[object], int | None]:
    """Return third-party entries and the first managed insertion position."""

    preserved: list[object] = []
    insertion_index: int | None = None
    for entry in current:
        cleaned, removed = strip_managed_claude_entry(entry)
        if removed and insertion_index is None:
            insertion_index = len(preserved)
        if cleaned is not None:
            preserved.append(cleaned)
    return preserved, insertion_index


def strip_managed_claude_entry(entry: object) -> tuple[object | None, bool]:
    """Strip managed commands while preserving co-located third-party hooks."""

    payload = json_object(entry)
    if payload is None:
        return entry, False
    command = payload.get("command")
    if isinstance(command, str) and is_managed_claude_command(command):
        return None, True
    return _strip_nested_claude_hooks(payload)


def _strip_nested_claude_hooks(entry: dict[str, object]) -> tuple[object | None, bool]:
    """Remove managed hook objects nested under one event entry."""

    hooks = json_array(entry.get("hooks"))
    if hooks is None:
        return entry, False
    cleaned_hooks, removed = _clean_nested_hooks(hooks)
    return _retained_nested_entry(entry, cleaned_hooks, removed=removed)


def _clean_nested_hooks(hooks: list[object]) -> tuple[list[object], bool]:
    """Return nested hook objects without managed commands."""

    cleaned_hooks: list[object] = []
    removed = False
    for hook in hooks:
        cleaned, hook_removed = strip_managed_claude_entry(hook)
        removed = removed or hook_removed
        if cleaned is not None:
            cleaned_hooks.append(cleaned)
    return cleaned_hooks, removed


def _retained_nested_entry(
    entry: dict[str, object],
    cleaned_hooks: list[object],
    *,
    removed: bool,
) -> tuple[object | None, bool]:
    """Retain a mixed entry only when third-party nested hooks remain."""

    if not removed:
        return entry, False
    if not cleaned_hooks:
        return None, True
    cleaned = dict(entry)
    cleaned["hooks"] = cleaned_hooks
    return cleaned, True


def is_managed_claude_command(command: str) -> bool:
    """Return whether a command belongs to Agent Maintainer's Claude hooks."""

    if command.startswith("agent-maintainer hooks "):
        return True
    return any(
        item.relative_path in command for item in manifest.hook_files(constants.CLAUDE_CODE_CLIENT)
    )
