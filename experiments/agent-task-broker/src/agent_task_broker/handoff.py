"""Compact task handoff capsules for broker subagents."""

from __future__ import annotations

import json

RESULT_SCHEMA = {
    "statuses": {
        "done": "requires summary, verification, optional changed_files",
        "blocked": "requires needs",
        "escalate": "requires reason",
        "abandoned": "requires reason",
    },
    "changed_files": "repo-relative paths only",
}
DEFAULT_GIVE_UP_RULES = (
    "Use blocked when another fact, credential, dependency, or decision is needed.",
    "Use escalate when a stronger model or human decision is needed.",
    "Use abandoned when the task is no longer useful or safe to continue.",
)


def handoff_payload(task: dict[str, object]) -> dict[str, object]:
    """Return JSON-serializable handoff capsule."""
    return {
        "schema_version": 1,
        "task_id": task["id"],
        "goal": task["title"],
        "body": task.get("body", ""),
        "allowed_paths": string_list(task.get("allowed_paths")),
        "do_not_edit_paths": string_list(task.get("do_not_edit_paths")),
        "constraints": string_list(task.get("constraints")),
        "evidence": string_list(task.get("evidence")),
        "acceptance_commands": string_list(task.get("acceptance_commands")),
        "give_up_rules": list(DEFAULT_GIVE_UP_RULES),
        "result_schema": RESULT_SCHEMA,
    }


def render_handoff(task: dict[str, object], *, output_format: str) -> str:
    """Render handoff capsule as Markdown or JSON."""
    payload = handoff_payload(task)
    if output_format == "json":
        return json.dumps(payload, indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_handoff_markdown(payload)
    raise ValueError(f"unknown handoff format: {output_format}")


def render_handoff_markdown(payload: dict[str, object]) -> str:
    """Render handoff capsule Markdown."""
    lines = [
        f"# Task Handoff: {payload['task_id']}",
        "",
        f"Goal: {payload['goal']}",
        "",
        section("Allowed paths", payload["allowed_paths"]),
        section("Do not edit", payload["do_not_edit_paths"]),
        section("Constraints", payload["constraints"]),
        section("Evidence", payload["evidence"]),
        section("Acceptance commands", payload["acceptance_commands"]),
        section("Give-up rules", payload["give_up_rules"]),
        "## Result schema",
        "Return one status: `done`, `blocked`, `escalate`, or `abandoned`.",
        "`done` requires verification. `blocked` requires needs. "
        "`escalate` and `abandoned` require reason.",
    ]
    return "\n".join(lines).rstrip()


def section(title: str, values: object) -> str:
    """Render one Markdown list section."""
    items = string_list(values)
    if not items:
        items = ["<none>"]
    return "\n".join([f"## {title}", *[f"- {item}" for item in items], ""])


def string_list(values: object) -> list[str]:
    """Return string values from arbitrary JSON field."""
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]
