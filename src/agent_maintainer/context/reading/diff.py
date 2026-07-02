"""Compatibility shim for diff context readers."""

from agent_context.reading import diff

DEFAULT_DIFF_HUNKS = diff.DEFAULT_DIFF_HUNKS
DiffResult = diff.DiffResult
bound = diff.bound
import_only_candidates = diff.import_only_candidates
largest_change_lines = diff.largest_change_lines
limit_hunks = diff.limit_hunks
lines_to_text = diff.lines_to_text
patch_is_import_only = diff.patch_is_import_only
rename_candidates = diff.rename_candidates
render_diff = diff.render_diff
render_diff_summary = diff.render_diff_summary
render_name_only = diff.render_name_only
render_patch = diff.render_patch
