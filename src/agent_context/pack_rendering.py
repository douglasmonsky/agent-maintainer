"""Render context pack Markdown and JSON outputs."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import cast

from agent_context.attention_rendering import attention_lines, attention_pointer_lines
from agent_context.budget import bound_text
from agent_context.formatting import UNTRUSTED_EXCERPT_LABEL
from agent_context.models import ContextBudget
from agent_context.next_actions import next_action_commands

HOOK_FACT_LIMIT = 3
HOOK_COMMAND_LIMIT = 3


def render_pack_markdown(
    payload: dict[str, object],
    *,
    log_dir: Path,
    budget: int,
    check: str | None,
) -> str:
    """Return Markdown context pack."""

    check_label = check or "<none>"
    lines = [
        "# Agent Maintainer Context Pack",
        "",
        f"- Log dir: `{log_dir}`",
        f"- Budget: `{budget}` characters",
        f"- Check filter: `{check_label}`",
        "",
    ]
    add_section(lines, "Exact Repair Facts", exact_fact_lines(payload["exact_repair_facts"]))
    add_section(lines, "Attention", attention_lines(payload.get("attention")))
    add_section(
        lines, "Supporting Context", supporting_context_lines(payload["supporting_context"])
    )
    add_section(
        lines, "Untrusted Content Labels", bullet_lines(payload["untrusted_content_labels"])
    )
    add_section(lines, "Ratchet State", ratchet_lines(payload["ratchet_state"]))
    add_section(lines, "Top Targets", top_target_lines(payload["top_targets"]))
    add_section(
        lines,
        "Selected File Outlines",
        supporting_item_lines(
            payload["selected_file_outlines"],
            "path",
            "No file outlines selected.",
        ),
    )
    add_section(
        lines,
        "Selected Logs",
        supporting_item_lines(payload["selected_logs"], "check", "No logs selected."),
    )
    add_section(lines, "Omitted Counts", omitted_count_lines(payload["omitted_counts"]))
    add_section(
        lines,
        "Expansion Commands",
        bullet_lines(payload["expansion_commands"], code=True),
    )
    return "\n".join(lines).rstrip()


def render_pack_json(payload: dict[str, object]) -> str:
    """Return stable JSON context pack."""

    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def render_pack_pointer(
    payload: dict[str, object],
    *,
    display_path: str,
    fact_limit: int = HOOK_FACT_LIMIT,
    command_limit: int = HOOK_COMMAND_LIMIT,
) -> str:
    """Return compact hook-safe repair capsule pointer."""

    lines = [
        "Result: FAIL",
        "Profile: agent-hook",
        "Run ID: unavailable",
        "",
        "Top repair facts:",
    ]
    facts = payload.get("exact_repair_facts")
    fact_lines = fact_pointer_lines(facts, fact_limit)
    ranked_commands = next_action_commands(facts, payload.get("expansion_commands"))
    lines.extend(fact_lines or ["1. (no structured repair facts found)"])
    lines.extend(attention_pointer_lines(payload.get("attention")))
    lines.extend(
        (
            "",
            "Likely next action:",
            next_action_line(ranked_commands),
            "",
            "Expand only if needed:",
        )
    )
    lines.extend(command_pointer_lines(ranked_commands, command_limit))
    lines.extend(("", f"Context pack artifact: {display_path}"))
    return "\n".join(lines)


def fact_pointer_lines(facts: object, limit: int) -> list[str]:
    """Return top exact fact lines for hook output."""

    fact_values = _json_array(facts)
    if fact_values is None:
        return []
    return [
        f"{index}. {fact_summary(fact)}"
        for index, value in enumerate(fact_values[:limit], start=1)
        if (fact := _json_object(value)) is not None
    ]


def fact_summary(fact: dict[str, object]) -> str:
    """Return compact exact-fact summary."""

    check = str(fact.get("check", "unknown"))
    message = str(fact.get("message", "")).strip()
    detail = "".join((fact_location(fact.get("path"), fact.get("line")), message))
    return f"{check}: {detail}".strip()


def fact_location(path: object, line: object) -> str:
    """Return compact location prefix for an exact fact."""

    if not path:
        return ""
    if isinstance(line, int):
        return f"{path}:{line} "
    return f"{path} "


def next_action_line(commands: object) -> str:
    """Return one likely next action from expansion commands."""

    command_values = _json_array(commands)
    if command_values:
        return str(command_values[0])
    return "Inspect the first failed check summary."


def command_pointer_lines(commands: object, limit: int) -> list[str]:
    """Return expansion command lines for hook output."""

    command_values = _json_array(commands)
    if command_values is None:
        return []
    if not command_values:
        return ["python -m agent_maintainer context failures --limit 20"]
    return [str(command) for command in command_values[:limit]]


def enforce_pack_budget(
    markdown: str,
    budget: int,
    expansion_commands: list[str],
) -> tuple[str, dict[str, int]]:
    """Return Markdown bounded to requested budget where practical."""

    bounded = bound_text(markdown, ContextBudget(max_chars=budget, max_items=1))
    if not bounded.truncated:
        return bounded.text, {
            "pack_markdown_omitted_chars": 0,
            "pack_markdown_omitted_lines": 0,
        }
    suffix = budget_suffix(bounded.omitted_chars, bounded.omitted_lines, expansion_commands)
    prefix_budget = max(0, budget - len(suffix))
    prefix = markdown[:prefix_budget].rstrip()
    text = "".join((prefix, suffix))
    return text[:budget], {
        "pack_markdown_omitted_chars": bounded.omitted_chars,
        "pack_markdown_omitted_lines": bounded.omitted_lines,
    }


def add_section(lines: list[str], title: str, body: list[str]) -> None:
    """Append one Markdown section."""

    lines.extend((f"## {title}", "", *body, ""))


def exact_fact_lines(facts: object) -> list[str]:
    """Return exact repair fact lines."""

    fact_values = _json_array(facts)
    if not fact_values:
        return ["- No failed checks found in the selected verifier manifest."]
    lines: list[str] = []
    for value in fact_values:
        fact = _json_object(value)
        if fact is None:
            lines.append("- Unknown failure fact.")
            continue
        location = fact_location(fact.get("path"), fact.get("line")).strip()
        symbol = fact.get("symbol")
        lines.extend(
            (
                f"- Check: `{fact.get('check', 'unknown')}`",
                f"  - Severity: `{fact.get('severity', 'unknown')}`",
                f"  - Location: `{location}`" if location else "  - Location: `<none>`",
                f"  - Symbol: `{symbol}`" if symbol else "  - Symbol: `<none>`",
                f"  - Message: {fact.get('message', '')}",
            ),
        )
    return lines


def supporting_context_lines(context: object) -> list[str]:
    """Return supporting context lines."""

    context_payload = _json_object(context)
    if context_payload is None:
        return ["- No supporting context selected."]
    return [
        str(context_payload.get("summary", "")),
        "",
        f"- Selected logs: `{context_payload.get('log_count', 0)}`",
        f"- Selected file outlines: `{context_payload.get('file_outline_count', 0)}`",
    ]


def ratchet_lines(state: object) -> list[str]:
    """Return ratchet state lines."""

    state_payload = _json_object(state)
    if state_payload is None or not state_payload.get("available"):
        reason = state_payload.get("reason", "unknown") if state_payload else "unknown"
        return [f"- Ratchet state unavailable: {reason}"]
    lines = [
        f"- Baseline: `{state_payload.get('baseline_path')}`",
        f"- Counts: `{json.dumps(state_payload.get('counts', {}), sort_keys=True)}`",
    ]
    stale = _json_array(state_payload.get("stale_reasons", []))
    if stale:
        lines.append("- Stale reasons:")
        lines.extend(f"  - {reason}" for reason in stale)
    return lines


def top_target_lines(targets: object) -> list[str]:
    """Return top ratchet target lines."""

    target_values = _json_array(targets)
    if not target_values:
        return ["- No ratchet targets selected."]
    lines: list[str] = []
    for value in target_values:
        target = _json_object(value)
        if target is None:
            lines.append("- Unknown target.")
            continue
        lines.extend(
            (
                f"- {target.get('rank')}. `{target.get('path')}`",
                f"  - Why: {target.get('why')}",
                f"  - Current: {target.get('current')}",
                f"  - First command: `{target.get('first_command')}`",
            ),
        )
    return lines


def supporting_item_lines(items: object, label_key: str, empty_message: str) -> list[str]:
    """Return selected untrusted supporting item lines."""

    item_values = _json_array(items)
    if not item_values:
        return [f"- {empty_message}"]
    lines: list[str] = []
    for value in item_values:
        item = _json_object(value)
        if item is None:
            lines.append("- Unknown supporting item.")
            continue
        label = item.get(label_key, item.get("source", "unknown"))
        source = item.get("source", item.get("path", label))
        lines.extend(
            (
                f"### {label}",
                "",
                UNTRUSTED_EXCERPT_LABEL,
                "",
                f"Source: `{source}`",
                "",
                "```text",
                str(item.get("text", "")),
                "```",
                "",
            ),
        )
    return lines


def omitted_count_lines(counts: object) -> list[str]:
    """Return omitted count lines."""

    count_values = _json_object(counts)
    if count_values is None:
        return []
    return [f"- {key}: `{value}`" for key, value in sorted(count_values.items())]


def bullet_lines(values: object, *, code: bool = False) -> list[str]:
    """Return bullet lines for string-like values."""

    item_values = _json_array(values)
    if code:
        return [f"- `{value}`" for value in item_values] if item_values else []
    return [f"- {value}" for value in item_values] if item_values else []


command_lines = partial(bullet_lines, code=True)


def _json_object(value: object) -> dict[str, object] | None:
    """Return a JSON object with string keys, or ``None`` when malformed."""

    if not isinstance(value, dict):
        return None
    raw = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in raw):
        return None
    return {key: item for key, item in raw.items() if isinstance(key, str)}


def _json_array(value: object) -> list[object] | None:
    """Return a JSON array with an explicit element boundary."""

    if not isinstance(value, list):
        return None
    return cast(list[object], value)


def budget_suffix(
    omitted_chars: int,
    omitted_lines: int,
    expansion_commands: list[str],
) -> str:
    """Return required budget metadata suffix after final truncation."""

    lines = [
        "",
        "",
        "## Omitted Counts",
        "",
        f"- pack_markdown_omitted_chars: `{omitted_chars}`",
        f"- pack_markdown_omitted_lines: `{omitted_lines}`",
        "",
        "## Expansion Commands",
        "",
    ]
    lines.extend(f"- `{command}`" for command in expansion_commands[:5])
    return "\n".join(lines)
