"""Compatibility shim for context compression backends."""

from __future__ import annotations

from agent_context.compression import backends as _backends

BACKEND_EXTRACTIVE = _backends.BACKEND_EXTRACTIVE
BACKEND_NONE = _backends.BACKEND_NONE
BACKEND_TRUNCATE = _backends.BACKEND_TRUNCATE
FALLBACK_WARNING = _backends.FALLBACK_WARNING
append_warning = _backends.append_warning
backend_function = _backends.backend_function
budget_remaining = _backends.budget_remaining
compress = _backends.compress
extractive_compress = _backends.extractive_compress
filler_lines = _backends.filler_lines
forbidden_warnings = _backends.forbidden_warnings
has_forbidden_term = _backends.has_forbidden_term
headroom_compress = _backends.headroom_compress
none_compress = _backends.none_compress
preserve_lines = _backends.preserve_lines
preserve_terms_present = _backends.preserve_terms_present
result_for = _backends.result_for
separator_chars = _backends.separator_chars
split_lines = _backends.split_lines
target_warnings = _backends.target_warnings
truncate_compress = _backends.truncate_compress
