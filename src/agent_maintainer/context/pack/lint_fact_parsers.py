"""Compatibility shim for lint repair-fact parsers."""

from agent_repair_facts.parsers import lint

bandit_fact = lint.bandit_fact
bandit_facts = lint.bandit_facts
pyright_fact = lint.pyright_fact
pyright_facts = lint.pyright_facts
range_start = lint.range_start
ruff_fact = lint.ruff_fact
ruff_facts = lint.ruff_facts
