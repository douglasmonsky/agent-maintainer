"""Identity-aware Claude Code hook configuration merging."""

from __future__ import annotations

import json
from pathlib import Path

from agent_client_hooks import constants, manifest


def merge_claude_settings(path: Path, managed_content: str) -> str:
    """Merge managed hook settings into existing Claude settings JSON."""

    with path.open(encoding="utf-8") as stream:
        current = json.load(stream)
    managed = json.loads(managed_content)
    if not isinstance(current, dict):
        current = {}
    hooks = current.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        current["hooks"] = {}
        hooks = current["hooks"]
    for event, entries in managed["hooks"].items():
        hooks[event] = merge_claude_event(hooks.get(event), entries)
    return f"{json.dumps(current, indent=2, sort_keys=True)}\n"


def merge_claude_event(current: object, managed: object) -> list[object]:
    """Replace only Agent Maintainer entries while preserving user ordering."""

    managed_entries = list(managed) if isinstance(managed, list) else []
    if not isinstance(current, list):
        return managed_entries
    preserved, insertion_index = _preserved_entries(current)
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

    if not isinstance(entry, dict):
        return entry, False
    command = entry.get("command")
    if isinstance(command, str) and is_managed_claude_command(command):
        return None, True
    return _strip_nested_claude_hooks(entry)


def _strip_nested_claude_hooks(entry: dict[object, object]) -> tuple[object | None, bool]:
    """Remove managed hook objects nested under one event entry."""

    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
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
    entry: dict[object, object],
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
