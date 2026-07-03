"""Compatibility shim for context-pack rendering helpers."""

from __future__ import annotations

from agent_context import pack_rendering as _pack_rendering

HOOK_COMMAND_LIMIT = _pack_rendering.HOOK_COMMAND_LIMIT
HOOK_FACT_LIMIT = _pack_rendering.HOOK_FACT_LIMIT
add_section = _pack_rendering.add_section
budget_suffix = _pack_rendering.budget_suffix
bullet_lines = _pack_rendering.bullet_lines
command_lines = _pack_rendering.command_lines
command_pointer_lines = _pack_rendering.command_pointer_lines
enforce_pack_budget = _pack_rendering.enforce_pack_budget
exact_fact_lines = _pack_rendering.exact_fact_lines
fact_location = _pack_rendering.fact_location
fact_pointer_lines = _pack_rendering.fact_pointer_lines
fact_summary = _pack_rendering.fact_summary
next_action_line = _pack_rendering.next_action_line
omitted_count_lines = _pack_rendering.omitted_count_lines
ratchet_lines = _pack_rendering.ratchet_lines
render_pack_json = _pack_rendering.render_pack_json
render_pack_markdown = _pack_rendering.render_pack_markdown
render_pack_pointer = _pack_rendering.render_pack_pointer
supporting_context_lines = _pack_rendering.supporting_context_lines
supporting_item_lines = _pack_rendering.supporting_item_lines
top_target_lines = _pack_rendering.top_target_lines
