"""Compatibility shim for Git diff readers."""

from agent_context.reading import diff_git

DEFAULT_DIFF_CONTEXT_LINES = diff_git.DEFAULT_DIFF_CONTEXT_LINES
DEFAULT_DIFF_PATH_LIMIT = diff_git.DEFAULT_DIFF_PATH_LIMIT
DiffRequest = diff_git.DiffRequest
FileChange = diff_git.FileChange
changed_paths = diff_git.changed_paths
diff_args = diff_git.diff_args
file_changes = diff_git.file_changes
git_diff = diff_git.git_diff
name_status_lines = diff_git.name_status_lines
parse_count = diff_git.parse_count
parse_numstat_line = diff_git.parse_numstat_line
run_git = diff_git.run_git
