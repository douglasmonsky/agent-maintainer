"""Render context pack Markdown and JSON outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_maintainer.context.budget import bound_text
from agent_maintainer.context.formatting import UNTRUSTED_EXCERPT_LABEL
from agent_maintainer.context.models import ContextBudget

HOOK_FACT_LIMIT = 3
HOOK_COMMAND_LIMIT = 3


def render_pack_markdown(
    payload: dict[str, Any],
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
    add_section(lines, "Expansion Commands", command_lines(payload["expansion_commands"]))
    return "\n".join(lines).rstrip()


def render_pack_json(payload: dict[str, Any]) -> str:
    """Return stable JSON context pack."""

    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def render_pack_pointer(
    payload: dict[str, object],
    *,
    display_path: str,
    fact_limit: int = HOOK_FACT_LIMIT,
    command_limit: int = HOOK_COMMAND_LIMIT,
) -> str:
    """Return compact hook-safe pointer to a context pack."""

    lines = [f"Read: {display_path}"]
    lines.extend(fact_pointer_lines(payload.get("exact_repair_facts"), fact_limit))
    lines.extend(command_pointer_lines(payload.get("expansion_commands"), command_limit))
    return "\n".join(lines)


def fact_pointer_lines(facts: object, limit: int) -> list[str]:
    """Return top exact fact lines for hook output."""

    if not isinstance(facts, list):
        return []
    return [
        f"Top finding: {fact_summary(fact)}" for fact in facts[:limit] if isinstance(fact, dict)
    ]


def fact_summary(fact: dict[object, object]) -> str:
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


def command_pointer_lines(commands: object, limit: int) -> list[str]:
    """Return expansion command lines for hook output."""

    if not isinstance(commands, list):
        return []
    return [f"Expand: {command}" for command in commands[:limit]]


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

    if not isinstance(facts, list) or not facts:
        return ["- No failed checks found in the selected verifier manifest."]
    lines: list[str] = []
    for fact in facts:
        if not isinstance(fact, dict):
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

    if not isinstance(context, dict):
        return ["- No supporting context selected."]
    return [
        str(context.get("summary", "")),
        "",
        f"- Selected logs: `{context.get('log_count', 0)}`",
        f"- Selected file outlines: `{context.get('file_outline_count', 0)}`",
    ]


def ratchet_lines(state: object) -> list[str]:
    """Return ratchet state lines."""

    if not isinstance(state, dict) or not state.get("available"):
        reason = state.get("reason", "unknown") if isinstance(state, dict) else "unknown"
        return [f"- Ratchet state unavailable: {reason}"]
    lines = [
        f"- Baseline: `{state.get('baseline_path')}`",
        f"- Counts: `{json.dumps(state.get('counts', {}), sort_keys=True)}`",
    ]
    stale = state.get("stale_reasons", [])
    if stale:
        lines.append("- Stale reasons:")
        lines.extend(f"  - {reason}" for reason in stale)
    return lines


def top_target_lines(targets: object) -> list[str]:
    """Return top ratchet target lines."""

    if not isinstance(targets, list) or not targets:
        return ["- No ratchet targets selected."]
    lines: list[str] = []
    for target in targets:
        if not isinstance(target, dict):
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

    if not isinstance(items, list) or not items:
        return [f"- {empty_message}"]
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
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

    if not isinstance(counts, dict):
        return []
    return [f"- {key}: `{value}`" for key, value in sorted(counts.items())]


def command_lines(commands: object) -> list[str]:
    """Return expansion command lines."""

    return [f"- `{command}`" for command in commands] if isinstance(commands, list) else []


def bullet_lines(values: object) -> list[str]:
    """Return bullet lines for string-like values."""

    return [f"- {value}" for value in values] if isinstance(values, list) else []


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
