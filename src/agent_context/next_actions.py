"""Rank surgical context expansion commands."""

from __future__ import annotations

from agent_context.structured_values import json_array, json_objects


def next_action_commands(facts: object, commands: object) -> list[str]:
    """Return surgical expansion commands before broader fallbacks."""

    ranked: list[str] = []
    for fact in json_objects(facts):
        ranked.extend(fact_expansion_commands(fact))
    command_values = json_array(commands)
    if command_values is not None:
        ranked.extend(str(command) for command in command_values)
    return list(dict.fromkeys(ranked))


def fact_expansion_commands(fact: dict[str, object]) -> list[str]:
    """Return expansion commands implied by one exact repair fact."""

    path = fact.get("path")
    line = fact.get("line")
    check = fact.get("check")
    if path:
        if isinstance(line, int):
            return [f"python -m agent_maintainer context file {path} --around {line} --context 30"]
        return [f"python -m agent_maintainer context file {path} --outline"]
    if check:
        return [
            f"python -m agent_maintainer context failures --check {check} --limit 3",
            f"python -m agent_maintainer context log {check} --tail 80",
        ]
    return []
