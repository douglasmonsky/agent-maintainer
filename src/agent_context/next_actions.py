"""Rank surgical context expansion commands."""

from __future__ import annotations


def next_action_commands(facts: object, commands: object) -> list[str]:
    """Return surgical expansion commands before broader fallbacks."""

    ranked: list[str] = []
    if isinstance(facts, list):
        for fact in facts:
            if isinstance(fact, dict):
                ranked.extend(fact_expansion_commands(fact))
    if isinstance(commands, list):
        ranked.extend(str(command) for command in commands)
    return list(dict.fromkeys(ranked))


def fact_expansion_commands(fact: dict[object, object]) -> list[str]:
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
