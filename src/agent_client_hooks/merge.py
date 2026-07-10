"""Merge managed agent hook configuration files."""

from __future__ import annotations

from pathlib import Path

from agent_client_hooks import claude_merge, templates

CODEX_HOOK_FEATURE = "hooks = true"


def merge_claude_settings(path: Path, managed_content: str) -> str:
    """Retain the public Claude merge facade for compatibility."""

    return claude_merge.merge_claude_settings(path, managed_content)


def merge_claude_event(current: object, managed: object) -> list[object]:
    """Retain the public event merge facade for compatibility."""

    return claude_merge.merge_claude_event(current, managed)


def strip_managed_claude_entry(entry: object) -> tuple[object | None, bool]:
    """Retain the public narrow-removal facade for lifecycle callers."""

    return claude_merge.strip_managed_claude_entry(entry)


def merge_codex_config(existing: str, managed_block: str) -> str:
    """Merge managed Codex hook block into an existing config."""

    stripped = strip_managed_block(existing, templates.CODEX_MARKER).rstrip()
    without_agent_hooks = strip_previous_agent_codex_hooks(stripped).rstrip()
    with_features = ensure_codex_hooks_feature(without_agent_hooks).rstrip()
    return f"{with_features}\n\n{managed_block}"


def strip_managed_block(content: str, marker: str) -> str:
    """Remove all existing managed blocks for one marker."""

    start = f"# >>> {marker} >>>"
    end = f"# <<< {marker} <<<"
    result = content
    while start in result and end in result:
        start_index = result.index(start)
        end_index = result.index(end, start_index) + len(end)
        before_block = result[:start_index]
        after_block = result[end_index:]
        result = f"{before_block}{after_block}"
    return result


def strip_previous_agent_codex_hooks(content: str) -> str:
    """Remove old unmarked Agent Maintainer Codex hook blocks."""

    sections = split_toml_sections(content)
    drop_indexes = previous_agent_codex_hook_indexes(sections)
    kept_sections = [section for index, section in enumerate(sections) if index not in drop_indexes]
    return "\n".join(section.rstrip() for section in kept_sections if section.strip())


def previous_agent_codex_hook_indexes(sections: list[str]) -> set[int]:
    """Return section indexes for previous unmarked managed hook blocks."""

    drop_indexes = {
        index
        for index, section in enumerate(sections)
        if is_previous_agent_codex_hook_section(section)
    }
    for index in tuple(drop_indexes):
        parent_index = index - 1
        if parent_index >= 0 and is_parent_hook_section(sections[parent_index], sections[index]):
            drop_indexes.add(parent_index)
    for index, section in enumerate(sections):
        next_section = sections[index + 1] if index + 1 < len(sections) else ""
        if is_orphan_previous_agent_hook_parent(section, next_section):
            drop_indexes.add(index)
    return drop_indexes


def split_toml_sections(content: str) -> list[str]:
    """Split TOML-ish content into header sections for conservative merging."""

    sections: list[list[str]] = []
    current: list[str] = []
    for line in content.splitlines():
        if line.startswith("[") and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)
    return ["\n".join(section) for section in sections]


def is_previous_agent_codex_hook_section(section: str) -> bool:
    """Return whether a TOML section is an old unmarked managed hook."""

    first_line = section.lstrip().splitlines()[0] if section.strip() else ""
    is_hook_section = first_line.startswith("[[hooks.PostToolUse") or first_line.startswith(
        "[[hooks.Stop"
    )
    return is_hook_section and (
        "Agent Maintainer" in section
        or ".codex/hooks/post_edit_fast_gate.py" in section
        or ".codex/hooks/stop_full_verify.py" in section
    )


def is_parent_hook_section(parent: str, child: str) -> bool:
    """Return whether an event section owns a hook sub-section."""

    parent_line = parent.lstrip().splitlines()[0] if parent.strip() else ""
    child_line = child.lstrip().splitlines()[0] if child.strip() else ""
    return (
        parent_line == "[[hooks.PostToolUse]]"
        and child_line.startswith("[[hooks.PostToolUse.hooks")
    ) or (parent_line == "[[hooks.Stop]]" and child_line.startswith("[[hooks.Stop.hooks"))


def is_orphan_previous_agent_hook_parent(section: str, next_section: str) -> bool:
    """Return whether an old parent hook table is left without its sub-table."""

    first_line = section.lstrip().splitlines()[0] if section.strip() else ""
    next_line = next_section.lstrip().splitlines()[0] if next_section.strip() else ""
    if first_line == "[[hooks.PostToolUse]]":
        return 'matcher = "apply_patch|Edit|Write"' in section and not next_line.startswith(
            "[[hooks.PostToolUse.hooks"
        )
    return first_line == "[[hooks.Stop]]" and not next_line.startswith("[[hooks.Stop.hooks")


def ensure_codex_hooks_feature(content: str) -> str:
    """Ensure Codex hook support is enabled without duplicating features."""

    if not content.strip():
        return f"[features]\n{CODEX_HOOK_FEATURE}"

    lines = content.splitlines()
    section_start, section_end = features_section_bounds(lines)
    if section_start is None:
        return f"[features]\n{CODEX_HOOK_FEATURE}\n\n{content}"

    feature_section = normalize_feature_section(lines[section_start:section_end])
    return "\n".join([*lines[:section_start], *feature_section, *lines[section_end:]])


def features_section_bounds(lines: list[str]) -> tuple[int | None, int]:
    """Return features section bounds if present."""

    start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[features]":
            start = index
            continue
        if start is not None and stripped.startswith("[") and stripped.endswith("]"):
            return start, index
    return start, len(lines)


def normalize_feature_section(lines: list[str]) -> list[str]:
    """Return a features section with one enabled hook feature line."""

    output: list[str] = []
    inserted = False
    for line in lines:
        if line.strip().startswith("hooks"):
            if not inserted:
                output.append(CODEX_HOOK_FEATURE)
                inserted = True
            continue
        output.append(line)
    if not inserted:
        output.append(CODEX_HOOK_FEATURE)
    return output
