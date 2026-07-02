"""Compatibility shim for log repair-fact parsers."""

from agent_repair_facts.parsers import logs

CHANGE_BUDGET_BLOCK_RE = logs.CHANGE_BUDGET_BLOCK_RE
FILE_LENGTH_RE = logs.FILE_LENGTH_RE
change_budget_fact = logs.change_budget_fact
change_budget_facts = logs.change_budget_facts
file_length_facts = logs.file_length_facts
log_matches = logs.log_matches
