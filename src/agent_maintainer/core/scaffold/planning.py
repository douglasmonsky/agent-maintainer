"""Plan safe initializer behavior for empty and existing repositories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from agent_client_hooks import merge as hook_merge
from agent_client_hooks import templates as hook_templates
from agent_maintainer.core.scaffold.templates import StarterFile


class InitAction(StrEnum):
    """Review classification for one initializer destination."""

    ADD = "ADD"
    UNCHANGED = "UNCHANGED"
    MERGE = "MERGE"
    CONFLICT = "CONFLICT"
    SKIP = "SKIP"


@dataclass(frozen=True)
class InitPlanItem:
    """One classified initializer destination and proposed content."""

    starter: StarterFile
    destination: Path
    action: InitAction
    content: str | None
    reason: str


def build_plan(target: Path, files: tuple[StarterFile, ...]) -> tuple[InitPlanItem, ...]:
    """Return a deterministic preflight plan without mutating the target."""

    return tuple(_plan_item(target, starter) for starter in files)


def has_conflicts(plan: tuple[InitPlanItem, ...]) -> bool:
    """Return whether applying the plan requires explicit force."""

    return any(item.action == InitAction.CONFLICT for item in plan)


def writable_items(
    plan: tuple[InitPlanItem, ...],
    *,
    force: bool,
) -> tuple[InitPlanItem, ...]:
    """Return additions, merges, and explicitly forced conflicts."""

    actions = {InitAction.ADD, InitAction.MERGE}
    if force:
        actions.add(InitAction.CONFLICT)
    return tuple(item for item in plan if item.action in actions)


def render_plan(plan: tuple[InitPlanItem, ...]) -> str:
    """Return one compact review line per initializer destination."""

    return "\n".join(_render_item(item) for item in plan)


def _render_item(item: InitPlanItem) -> str:
    action = item.action.value
    path = item.starter.path
    return f"{action:<9} {path} — {item.reason}"


def _plan_item(target: Path, starter: StarterFile) -> InitPlanItem:
    destination = target / starter.path
    if not destination.exists():
        return InitPlanItem(starter, destination, InitAction.ADD, starter.content, "missing")
    try:
        current = destination.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return InitPlanItem(
            starter,
            destination,
            InitAction.CONFLICT,
            starter.content,
            f"cannot safely read existing file: {exc}",
        )
    if current == starter.content:
        return InitPlanItem(starter, destination, InitAction.UNCHANGED, None, "already current")
    return _existing_item(starter, destination, current)


def _existing_item(starter: StarterFile, destination: Path, current: str) -> InitPlanItem:
    if starter.path == "AGENTS.md":
        return InitPlanItem(
            starter,
            destination,
            InitAction.SKIP,
            None,
            "user guidance is preserved",
        )
    merged = _merge_existing(starter.path, current, starter.content)
    if merged is None:
        return InitPlanItem(
            starter,
            destination,
            InitAction.CONFLICT,
            starter.content,
            "existing content requires explicit replacement",
        )
    if merged == current:
        return InitPlanItem(starter, destination, InitAction.UNCHANGED, None, "already satisfies")
    return InitPlanItem(starter, destination, InitAction.MERGE, merged, "preserve existing content")


def _merge_existing(path: str, current: str, starter: str) -> str | None:
    if path == ".codex/config.toml":
        return hook_merge.merge_codex_config(current, hook_templates.codex_config_block())
    if path == ".claude/settings.json":
        return _merge_claude_text(current, starter)
    if path == "config/dev-dependencies.txt":
        return _merge_dependency_lines(current, starter)
    if path == "package.json":
        return _merge_package_json(current, starter)
    return None


def _merge_claude_text(current: str, starter: str) -> str | None:
    try:
        payload = json.loads(current)
    except (json.JSONDecodeError, RecursionError):
        return None
    if not isinstance(payload, dict):
        return None
    hooks = payload.setdefault("hooks", {})
    managed = json.loads(starter).get("hooks", {})
    if not isinstance(hooks, dict) or not isinstance(managed, dict):
        return None
    for event, entries in managed.items():
        hooks[event] = hook_merge.merge_claude_event(hooks.get(event), entries)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    return f"{rendered}\n"


def _merge_dependency_lines(current: str, starter: str) -> str:
    lines = current.splitlines()
    existing = {line.strip() for line in lines if line.strip()}
    additions = [line for line in starter.splitlines() if line.strip() not in existing]
    merged = [*lines, *additions]
    content = "\n".join(merged).rstrip()
    return f"{content}\n"


def _merge_package_json(current: str, starter: str) -> str | None:
    try:
        payload, starter_payload = _decode_json_pair(current, starter)
    except (json.JSONDecodeError, RecursionError):
        return None
    if not isinstance(payload, dict) or not isinstance(starter_payload, dict):
        return None
    current_dependencies = payload.setdefault("devDependencies", {})
    starter_dependencies = starter_payload.get("devDependencies", {})
    if not isinstance(current_dependencies, dict) or not isinstance(starter_dependencies, dict):
        return None
    if _dependency_version_conflict(current_dependencies, starter_dependencies):
        return None
    current_dependencies.update(starter_dependencies)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    return f"{rendered}\n"


def _decode_json_pair(current: str, starter: str) -> tuple[object, object]:
    """Decode current and starter JSON as one fallible operation."""

    return json.loads(current), json.loads(starter)


def _dependency_version_conflict(
    current: dict[object, object], starter: dict[object, object]
) -> bool:
    return any(key in current and current[key] != value for key, value in starter.items())
